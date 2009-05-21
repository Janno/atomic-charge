#!/usr/bin/python 
import bencode
from hashlib import sha1
from socket import socket
from string import printable
import struct
import math
import random

def gen_handshake(meta):
        infohash = sha1(bencode.bencode(meta['info'])).digest()
        return chr(19) + 'BitTorrent protocol' + chr(0)*8 + infohash

def gen_bitfield(meta):
        num = len(meta['info']['pieces']) / 20 // 8
##        result = ""
##        for x in reversed(xrange(int(math.ceil(math.log(num,2))))):
##                result = result + chr(num / (2**x))
##                num = num % (2**x)
##        return result
        return '\xFF'*num

def gen_message(msgid, msg):
        return struct.pack('>iis', len(msg)+1, msgid ,msg)
        

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
        sock.sendall(gen_handshake(meta))
        print "handshake sent"
        resp = sock.recv(100)
        if resp:
                print "got a response"
                if ord(resp[0]) == 19:
                        print 'peer-id:', resp[48:]
                        
                else:
                        print "gibberish, exiting!"
                        exit()
        id = ''.join(random.choice(printable) for x in xrange(12))
        sock.sendall(gen_handshake(meta)+'AC-'+id)
        sock.sendall(gen_message(5, gen_bitfield(meta)))
        print gen_bitfield(meta)
        print "bitfield sent"
        while True:
                resp = sock.recv(512)
                if resp: print resp
                
                



        



