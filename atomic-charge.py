#!/usr/bin/python 
import bencode
from hashlib import sha1

def gen_handshake(meta):
        infohash = sha1(bencode.bencode(meta['info'])).digest()
        return chr(19) + 'BitTorrent protocol' + chr(0)*8 + infohash

if __name__ == '__main__':
        from sys import argv
        #assert len(argv) == 4

        
        f = file(argv[1], 'rb')
        meta = bencode.bdecode(f.read())
        f.close()

        numpieces = len(meta['pieces']) / 20

        
        
