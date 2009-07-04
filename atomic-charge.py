#!/usr/bin/python 

from hashlib import sha1
import socket
from string import printable
import struct
import math
import random
import bencode
import os

def parse(sock):
    """
    returns (yieldwise): (id, msg) # :D
    """    
    while True:
        #assert len(msg) >= 4
        try:
            temp = sock.recv(4) # read 4 bytes to know the length of the packet
        except socket.timeout:
            continue
        
        if not temp:
            continue
        msglen = int(struct.unpack('>I', temp)[0]) # "..PWP messages are encoded as a 4-byte big-endian number"
        if msglen == 0:
            # keep-alive, len 0
            yield (0, '')
        else:
            msg = sock.recv(msglen) # read msgid and msg
            assert len(msg) == msglen
            msgid, msg = struct.unpack('>B', msg[0])[0], msg[1:]
            yield (msgid, msg)


def gen_handshake(meta):
    """
    unsigned first-byte value is the length of the string with the protocol name. len('BitTorrent protocol') == 19.
    following 8 reserved bytes and infohash of .torrent-file. len(handshake) == 68byte
    the handshake MUST be sent after a TCP connection has been established
    """
    infohash = sha1(bencode.bencode(meta['info'])).digest()
    return chr(19) + 'BitTorrent protocol' + chr(0)*8 + infohash

def gen_bitfield(meta):
    #XXX needs documentation
    # freddy added some text. sufficient?!
    """
    each bit represents a piece. (high bit in the first byte is piece 0). we set them all to indicate having 100%
    bitfield MUST be send after the handshake.
    """
    pieces = len(meta['info']['pieces']) / 20 # "pieces" contains a sha1-sum for each piece. thus, pieces_amount = len()/20
    num = int(math.ceil(pieces / 8.0))
    result = list('\xFF'*num)
    if pieces % 8:
        #print 'result:', result
        result[-1] = chr(ord(result[-1]) ^ (2**(8 - (pieces % 8))) - 1)
        #print 'result:', result
    
    return ''.join(result)

def gen_message(msgid, msg = ''):
    if msgid == 0:
        # keep-alive, message length = 0
        return '\x00' * 4
    else:
        return struct.pack('>IB', len(msg)+1, msgid) + msg
    
def send(s, msg, silent=False):
    s.sendall(msg)
    if not silent: printhex(msg, '-> ')
    
def printhex(msg, prefix=''):
    def gen_printhex(msg):
        return ' '.join(["%2X" % ord(char) for char in msg])
    print prefix + gen_printhex(msg)

def abs2rel(index, offset):
    pass

def sendpiece(meta,sock,piece,offset,length):
    print "got request", piece, offset, length
    print piece, offset, length
    if singlefile:
        f = file(argv[2], 'rb')
        print "offset: %s" % (piece*meta['info']['piece length']+offset)
        f.seek(piece*meta['info']['piece length']+offset)
        content = f.read(length)
        print "content length: %s" % len(content)
        send(sock, gen_message(7, struct.pack('>II', piece, offset)+content), True)
        print "sent piece"
        f.close()


if __name__ == '__main__':
    from sys import argv
    print argv
    # expects torrent file, src file/dir, remote ip, remote host
    assert len(argv) == 5
    
    f = file(argv[1], 'rb')
    meta = bencode.bdecode(f.read())
    f.close()

    print meta['info'].keys()
    singlefile = ('length' in meta['info'].keys())
    print ("single-file" if singlefile else "multi-file") + " torrent"
    if singlefile:
       files = [argv[2]]
    else:
       files = [os.path.join(argv[2], '/'.join(file['path'])) for file in meta['info']['files']]
       print "files: ", files
    
    
    sock = socket.socket()
    sock.connect((argv[3], int(argv[4])))
    sock.settimeout(2)
    print "connected"
    id = '-AC-'+''.join('%2X' % random.choice(xrange(255)) for x in xrange(8)) #AC is our client-"ID", of course..

    print 'id: ', id
    send(sock, gen_handshake(meta)+id + gen_message(5, gen_bitfield(meta)))
    print "handshake sent + bitfield sent"
    resp = sock.recv(68)
    if resp:
        print "got a response"
        if ord(resp[0]) == 19:
            print 'peer-id:', resp[48:]
            printhex(resp, '<- ')
            
        else:
            print "gibberish, exiting!"
            exit()

    pwp_dict = {0:'Choke',1:'Unchoke',
                2:'Interested',3:'Uninterested',
                4:'Have',5:'Bitfield',6:'Request',
                7:'Piece',8:'Cancel'}

    for (msgid, msg) in parse(sock):
        printhex(msg, '<- %s: (%s) ' % (str(msgid), pwp_dict[msgid]))
        #send(sock, gen_message(0)) # Keep-alive
        #print "keep alive sent"
        if msgid == 4:  
            msg_int = sum(256**i * ord(c) for i, c in enumerate(reversed(msg)))
            peerbitfield |= 1<<msg_int # update bitfield #FIXME somehow it's not always \xFF*pieces when finished
            print 'bitfield updated' #FIXME make a beauty string of it...
        if msgid == 5:
            msg_int = sum(256**i * ord(c) for i, c in enumerate(reversed(msg)))
            peerbitfield = msg_int
            send(sock, gen_message(1))
            print "unchoke sent"
        if msgid == 6:
            piece, offset, length = struct.unpack('>III', msg)
            sendpiece(meta,sock,piece,offset,length)
        if msgid == 3:
            print "received not interested"
            print "exiting"
            exit()

                
                
        
        



    


