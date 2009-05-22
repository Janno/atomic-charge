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
        pieces = len(meta['info']['pieces']) / 20
        num = int(math.ceil(pieces / 8.0))
        result = list('\xFF'*num)
        if pieces % 8:
                #print 'result:', result
                result[-1] = chr(ord(result[-1]) ^ (2**(8 - (pieces % 8))) - 1)
                #print 'result:', result
        
        return ''.join(result)

def gen_message(msgid, msg = ''):
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

        #sock.sendall(gen_handshake(meta)+id)
        #raw_input()
        #print map(ord, sock.recv(100))
        #send(sock, gen_message(5, gen_bitfield(meta)))
        #print "bitfield sent"
        #raw_input()
        #send(sock, gen_message(0))
        #print "keep alive sent"
        while True:
                resp = sock.recv(512)
                if resp:
                        printhex(resp, '<- ')
                        if resp[4] == chr(5):
                                print "got bitfield"
                                send(sock, gen_message(2))
                                print "interested sent"
                
                
                



        



