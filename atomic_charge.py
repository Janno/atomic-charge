#!/usr/bin/python

import bencode

from hashlib import sha1
import socket
import struct

import os.path
import math
import random


from itertools import izip_longest

def grouper(n, iterable, padvalue=None):
    "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
    return izip_longest(*[iter(iterable)]*n, fillvalue=padvalue)


def makeId(prefix='-AC-'):
    result = prefix
    for x in xrange(8):
        result += '%2X' % random.choice(xrange(255))
    return result


class Charger(object):
    def __init__(self, torrentFile, location, remoteAddr, remotePort, hashCheck=True):
        self.torrent = Torrent(torrentFile)
        files = []
        sizesDict = {}
        if self.torrent.isSingleFile():
            # if location is a file, it must 
            # be the actual file to be used
            # if it's not, it must be a directory
            # containing the file to be used
            if not os.path.isfile(location):
                if not os.path.isdir(location):
                    print 'Critical: You must either specify a file or a directory which contains the target file'
                    exit()
                location = os.path.join(location, self.torrent.meta['info']['name'])
                if not os.path.isfile(location):
                    print 'Critical: The directory you specified does not contain the target file %s'
                    exit()

            if self.torrent.meta['info']['name'] != os.path.split(location)[1]:
                print 'Warning: provided file name differs from file name in torrent'
            files = [location]
            sizesDict[location] = self.torrent.meta['info']['length']
        else:
            # location must be a directory
            # assumption: the directory that usually contains all
            # the torrent's files IS the given directory.
            # this allows for renamed top-level directories
            assert os.path.isdir(location)
            files = []
            for fileInfo in self.torrent.meta['info']['files']:
                files.append(os.path.join(location, *fileInfo['path']))
                sizesDict[files[-1]] = fileInfo['length']

        self.fileManager = FileManager(files)
        if self.fileManager.checkFileSizes(sizesDict):
            print 'Warning: not all file sizes match those in the torrent'

        if hashCheck:
            self.setLocalBitField()
        else:
            self.localBitField = BitField(self.torrent.numPieces, complete=True)

        self.remoteBitField = BitField(self.torrent.numPieces, complete=False)

        self.socket = socket.socket()
        #self.socket.settimeout(1)
        self.socket.setblocking(1)
        self.addr = (remoteAddr, remotePort)
        self.id = makeId() 

    def connect(self):
        self.socket.connect(self.addr)

    def send(self, data):
        self.socket.sendall(data)

    def recv(self, length):
        data = ""
        counter = 0
        while counter < length:
            tmp = self.socket.recv(length-counter)
            data += tmp
            counter += len(tmp)
        return data

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
        pieceLen = self.torrent.pieceLength
        pos = pieceLen * piece + offset
        data = self.fileManager.read(pos, length)
        msg = struct.pack('>II', piece, offset) + data
        print 'Debug: sendPiece %s %s %s' % (piece, offset, length)
        self.sendMsg(7,msg)

    def sendHandshake(self):
        """Initializes communication with the peer"""
        print 'Debug: sending handshake'
        infohash = self.torrent.getInfoHash() 
        self.send(chr(19) + 'BitTorrent protocol' + chr(0)*8 + infohash + self.id)

    def setLocalBitField(self):
        pieces = []
        for n in xrange(self.torrent.numPieces):
            pieceData = self.fileManager.read(
                    n * self.torrent.pieceLength, 
                    min(self.torrent.pieceLength,
                        self.torrent.length - n*(self.torrent.pieceLength)
                        )
                    )
            if sha1(pieceData).digest() == self.torrent.hashes[n]:
                pieces.append(n)
        self.localBitField = BitField(self.torrent.numPieces, pieces=pieces, complete=False)
        
    def setRemoteBitField(self, string):
        pieces = []
        for i, char in enumerate(string):
            ordi = ord(char)
            pieces.extend(map(lambda x: x+n, filter(lambda x: ordi & 1<<x, [x for x in xrange(8)])))
        self.remoteBitField = BitField(self, pieces=pieces, complete=False)


    def sendBitField(self):
        """Message ID 5, MUST be sent immediately after the handshake"""
        self.sendMsg(5, str(self.localBitField))

    def receiveHandshake(self):
        data = self.recv(68)
        print 'Debug: received handshake:\n%s' % data.encode('hex')
        # TODO sanity check

    def unChoke(self):
        """Message ID 1"""
        self.sendMsg(1)

    def receiveMsg(self):
        lenEnc = self.recv(4)
        if len(lenEnc) != 4:
            print 'Debug: could not read packet length. %s' % len(lenEnc)
            raise socket.error()
        else:
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
                break
            if msgId == 6:
                # Request
                piece, offset, length = struct.unpack('>III', msg)
                self.sendPiece(piece, offset, length)
            if msgId == 3:
                # Uninterested
                print 'Debug: peer not interested, exiting'
                break
            if msgId == 5:
                # BitField
                self.setRemoteBitField(msg)
            if msgId == 4:
                # Have
                piece, = struct.unpack('>I', msg)
                self.remoteBitField.enable(piece)
                print 'Debug:', self.remoteBitField

    def begin(self):
        self.connect()
        self.sendHandshake()
        self.receiveHandshake()
        self.sendBitField()
        self.unChoke()
        self.receiveLoop()





class BitField(object):
    def __init__(self, size, complete=False, pieces=[]):
        """Initializes the bit field. If complete==False,
        every integer < size in pieces is treated as
        a piece that should be toggled on in the bit
        field. If complete==True, every piece contained
        in pieces is disabled."""
        self.size = size
        self.bitString = [1 if complete else 0]*size

        for piece in pieces:
            self.bitString[piece] ^= 1

    def enable(self, piece):
        self.bitString[piece] = 1

    def disable(self, piece):
        self.bitString[piece] = 0

    def __str__(self):
        result = ''
        for bits in grouper(8, self.bitString, 0):
            result += chr(int(''.join(map(str, bits)), 2))
        return result

    def __repr__(self):
        return repr(self.bitString)

class Torrent(object):
    def __init__(self, torrentFile):
        self.torrentFile = torrentFile
        assert os.path.exists(self.torrentFile) and \
               os.path.isfile(self.torrentFile)
        f = file(self.torrentFile, 'rb')
        self.meta = bencode.bdecode(f.read())
        self.hashes = map(''.join, list(grouper(20, self.meta['info']['pieces'], '0')))
        self.numPieces = len(self.meta['info']['pieces'])/20
        self.pieceLength = self.meta['info']['piece length']

        if self.isSingleFile():
            self.length = self.meta['info']['length']
        else:
            self.length = sum(map(lambda x: x['length'], self.meta['info']['files']))

        f.close()

    def isSingleFile(self):
        return 'length' in self.meta['info'].keys()

    def genFullBitField(self):
        """Each bit represents one piece in the torrent. The high bit in the first byte is piece 0. We set them all to indicate having 100%.
        Bitfield MUST be send after the handshake.
        """
        # meta['pieces'] contains a sha1-sum for each piece. 
        # thus, pieces_amount = len()/20
        pieces = self.numPieces
        num = int(math.ceil(pieces / 8.0))
        result = list('\xFF'*num)
        if pieces % 8:
            result[-1] = chr(ord(result[-1]) ^ (2**(8 - (pieces % 8))) - 1)
        return ''.join(result)

    def getInfoHash(self):
        return sha1(bencode.bencode(self.meta['info'])).digest()


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


    def checkFileSizes(self, sizesDict):
        result = []
        for fname, s1 in sizesDict.iteritems():
            s2 = self.fileSizes[fname]
            if s1 != s2:
                result.append(fname)
        return result

        
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
        for fname in self.fileNames:
            size = self.fileSizes[fname]
            if pos < (akku + size):
                return (fname, pos-akku, akku + size - pos)
            akku += size
    
    def read(self, pos, length):
        if (pos+length > sum(self.fileSizes.itervalues())):
            raise IndexError("pos+length is larger than combined size of all files")
        data = ""
        totalBytesRead = 0
        while totalBytesRead < length:
            fname, offset, bytesLeft = self.abs2rel(pos + totalBytesRead)
            handle = self.getHandle(fname)
            bytesToRead = min(length-totalBytesRead, bytesLeft)
            handle.seek(offset)
            data += handle.read(bytesToRead)
            totalBytesRead += bytesToRead
        return data


        
def main():
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


if __name__ == '__main__':
    main()
