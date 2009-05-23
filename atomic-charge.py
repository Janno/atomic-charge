#!/usr/bin/python 

from hashlib import sha1
from socket import socket
from string import printable
import struct
import math
import random
import bencode

def parse(msg):
    """
    returns (yieldwise): (id, msg) # :D
    """
    while msg:
        assert len(msg) >= 4
        msglen = struct.unpack('>I', msg[:4]) # "..PWP messages are encoded as a 4-byte big-endian number"
        if msglen == 0:
            # keep-alive, len 0
            yield (0, '')
            msg = msg[4:]
        else:
            msgid = msg[4]
            yield (msgid, msg[4:4+msglen])
            msg = msg[4+msglen:]

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
    
def send(s, msg):
    s.sendall(msg)
    printhex(msg, '-> ')
def printhex(msg, prefix=''):
    def gen_printhex(msg):
        return ' '.join(["%2X" % ord(char) for char in msg])
    print prefix + gen_printhex(msg)

if __name__ == '__main__':
    from sys import argv
    print argv
    # expects torrent file, src file/dir, remote ip, remote host
    assert len(argv) == 5
    
    f = file(argv[1], 'rb')
    meta = bencode.bdecode(f.read())
    f.close()
    
    singlefile = ('md5sum' in meta['info'])
    
    sock = socket()
    sock.connect((argv[3], int(argv[4])))
    print "connected"
    id = '-AC-'+''.join('%2X' % random.choice(xrange(255)) for x in xrange(8))

    print 'id: ', id
    send(sock, gen_handshake(meta)+id + gen_message(5, gen_bitfield(meta)))
    print "handshake sent + bitfield sent"
    raw_input()
    resp = sock.recv(68)
    if resp:
        print "got a response"
        if ord(resp[0]) == 19:
            print 'peer-id:', resp[48:]
            printhex(resp, '<- ')
            
        else:
            print "gibberish, exiting!"
            exit()

    while True:
        resp = sock.recv(512)
        if resp:
            printhex(resp, '<- ')
            send(sock, gen_message(0))
            print "keep alive sent"
            if len(resp) > 4 and resp[4] == chr(5):
                print "got bitfield"
        
        
        



    


