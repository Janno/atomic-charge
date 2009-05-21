#!/usr/bin/python 
import bencode
from hashlib import sha1
from socket import socket

def gen_handshake(meta):
        infohash = sha1(bencode.bencode(meta['info'])).digest()
        return chr(19) + 'BitTorrent protocol' + chr(0)*8 + infohash

if __name__ == '__main__':
        from sys import argv
        print argv
        # expects torrent file, src file/dir, remote ip, remote host
        assert len(argv) == 5
        
        f = file(argv[1], 'rb')
        meta = bencode.bdecode(f.read())
        f.close()
        
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
                        print "gibberish!"

        singlefile = ('md5sum' in meta['info'])
        numpieces = len(meta['info']['pieces']) / 20

        
        
