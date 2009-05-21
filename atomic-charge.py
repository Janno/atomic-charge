#!/usr/bin/python 
import bencode
from hashlib import sha1
from socket import socket

def gen_handshake(meta):
        infohash = sha1(bencode.bencode(meta['info'])).digest()
        return chr(19) + 'BitTorrent protocol' + chr(0)*8 + infohash

if __name__ == '__main__':
        from sys import argv
        #assert len(argv) == 4
        print argv
        
        f = file(argv[1], 'rb')
        meta = bencode.bdecode(f.read())
        f.close()
        
        sock = socket()
        sock.connect((argv[3], int(argv[4])))
        print "connected" 
        
        numpieces = len(meta['info']['pieces']) / 20

        
        
