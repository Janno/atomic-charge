#!/usr/bin/python

from hashlib import sha1
import socket
from string import printable
import struct
import math
import random
import bencode
import os

def makeId(prefix='-AC-'):
    result = prefix
    for x in xrange(8):
        result += '%2X' % random.choice(xrange(255))
    return result


class Charger(object):
    def __init__(self, torrentFile, location, remoteAddr, remotePort):
        self.torrent = Torrent(torrentFile)
        if self.torrent.isSingleFile():
            # location must be an existing file
            assert os.path.isfile(location)
            if self.torrent.meta['info']['name'] != os.path.split(location)[1]:
                print 'Warning: provided file name differs from file name in torrent'
            self.fileManager = FileManager([location])
        else:
            # location must a directory
            # assumption: the directory that usually contains all
            # the torrent's files IS the given directory.
            # this allows for renamed top-level directories
            assert os.path.isdir(location)
            files = []
            sizes = []
            for fileInfo in self.torrent.meta['info']['files']:
                files.append(os.path.join(location, fileInfo['path']))
                sizes.append(fileInfo['length'])
            self.fileManager = FileManager(files)
            if not self.fileManager.checkFileSizes(sizes):
                print 'Warning: not all file sizes match those in the torrent'

        self.socket = socket.socket()
        self.socket.settimeout(2)
        self.addr = (remoteAddr, remotePort)
        self.id = makeId() 

    def connect(self):
        self.socket.connect(self.addr)

    def send(self, data):
        self.socket.sendall(data)

    def recv(self, length):
        return self.socket.recv(length)

    def sendMsg(self, msgId, msg=""):
        packet = ""
        if msgId == 0:
            # keep-alive, length must be zero
            assert not msg
            packet = struct.pack('>I', 0)
        else:
            packet = struct.pack('>IB', len(msg) + 1, msgId) + msg
        print 'Debug: sending message with ID %s' % msgId
        self.send(packet)

    def sendPiece(self, piece, offset, length):
        """Message ID 7"""
        pieceLen = self.torrent.meta['info']['piece length']
        pos = pieceLen * piece + offset
        data = self.fileManager.read(pos, length)
        msg = struct.pack('>II', piece, offset) + data
        self.sendMsg(7,msg)

    def sendHandshake(self):
        """Initializes communication with the peer"""
        print 'Debug: sending handshake'
        infohash = sha1(bencode.bencode(self.torrent.meta['info'])).digest()
        self.send(chr(19) + 'BitTorrent protocol' + chr(0)*8 + infohash + self.id)

    def sendBitField(self):
        """Message ID 5, MUST be sent immediately after the handshake"""
        self.sendMsg(5, self.torrent.genFullBitField())

    def receiveHandshake(self):
        data = self.recv(68)
        print 'Debug: received handshake:\n%s' % data
        # TODO sanity check

    def unChoke(self):
        """Message ID 1"""
        self.sendMsg(1)

    def receiveMsg(self):
        lenEnc = self.recv(4)
        length = struct.unpack('>I', lenEnc)[0]
        if length > 0:
            data = self.recv(length)
            msgId, msg = struct.unpack('>B', data[0])[0], data[1:]
            print 'Debug: received message with ID %s' % msgId
            return (msgId, msg)
        else:
            # keep-alive, no data
            print 'Debug: received keep-alive'
            return ('0', '')

    def receiveLoop(self):
        while True:
            try:
                msgId, msg = self.receiveMsg()
            except:
                import traceback
                traceback.print_exc()
                continue
            if msgId == 6:
                piece, offset, length = struct.unpack('>III', msg)
                self.sendPiece(piece, offset, length)


    def begin(self):
        self.connect()
        self.sendHandshake()
        self.sendBitField()
        self.receiveHandshake()
        self.unChoke()
        self.receiveLoop()


         

class Torrent(object):
    def __init__(self, torrentFile):
        self.torrentFile = torrentFile
        assert os.path.exists(self.torrentFile) and \
               os.path.isfile(self.torrentFile)
        f = file(self.torrentFile, 'rb')
        self.meta = bencode.bdecode(f.read())
        f.close()

    def isSingleFile(self):
        return 'length' in self.meta['info'].keys()

    def genFullBitField(self):
        """Each bit represents one piece in the torrent. The high bit in the first byte is piece 0. We set them all to indicate having 100%.
        Bitfield MUST be send after the handshake.
        """
        # meta['pieces'] contains a sha1-sum for each piece. 
        # thus, pieces_amount = len()/20
        pieces = len(self.meta['info']['pieces']) / 20
        num = int(math.ceil(pieces / 8.0))
        result = list('\xFF'*num)
        if pieces % 8:
            result[-1] = chr(ord(result[-1]) ^ (2**(8 - (pieces % 8))) - 1)
        return ''.join(result)


class FileManager(object):
    """Manages all file access for both single-file
    and multi-file torrents."""
    def __init__(self, files, sizes=None):
        self.fileNames = files

        for fname in self.fileNames:
            if not os.path.exists(fname):
                raise IOError("file not found: %s" % fname)

        self.fileSizes = dict([(fname, os.path.getsize(fname)) for fname in self.fileNames])
        self.handles = dict([(fname, None) for fname in self.fileNames])


    def checkFileSizes(self, sizes):
        """Order matters!!!"""
        for s1,s2 in zip(sizes, self.fileSizes.itervalues()):
            if s1 != s2:
                return false
        return true

        
    def openFile(self, fname):
        assert fname in self.fileNames
        self.handles[fname] = file(fname, 'rb')
    
    def getHandle(self, fname):
        if not self.handles[fname]:
            self.openFile(fname)
        return self.handles[fname]
        
    def abs2rel(self, pos):
        """Returns the name of the file which corresponds to
        the given, absolute position. Additionally, abs2rel
        returns the corresponding offset and the number of 
        bytes after pos in that file."""
        if (pos > sum(self.fileSizes.itervalues())):
            raise IndexError("pos is larger than combined size of all files")
        akku = 0
        for fname, size in self.fileSizes.iteritems():
            if pos < (akku + size):
                return (fname, pos-akku, akku + size - pos)
            akku += size
    
    def read(self, pos, length):
        if (pos+length > sum(self.fileSizes.itervalues())):
            raise IndexError("pos is larger than combined size of all files")
        data = ""
        totalBytesRead = 0
        while totalBytesRead < length:
            fname, offset, bytesLeft = self.abs2rel(pos + totalBytesRead)
            bytesToRead = min(length, bytesLeft)
            data += self.getHandle(fname).read(bytesToRead)
            totalBytesRead += bytesToRead
        return data


        

if __name__ == '__main__':
    from sys import argv
    if len(argv) != 5:
        print 'Could not parse parameters.'
        print 'Parameters: <torrent file> <file location> <remote address> <remote port>'
        exit()
    
    torrent = argv[1]
    location = argv[2]
    addr = argv[3]
    port = int(argv[4])

    con = Charger(torrent, location, addr, port)
    con.begin()

