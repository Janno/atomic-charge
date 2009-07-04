#!/usr/bin/python
# fast fertig. jo!

from hashlib import sha1
import socket
from string import printable
import struct
import math
import random
import bencode
import os

class Torrent(object):
    def __init__(self, torrentFile):
        self.torrentFile = torrentFile
        assert os.path.exists(self.torrentFile) and \
               os.path.isfile(self.torrentFile)
        f = file(self.torrentFile)
        self.meta = bencode.bdecode(f.read())
        f.close()
        
    def __getitem__(self, key):
        return self.meta[key]
    
    
    
    
class FileManager(object):
    def __init__(self, files):
        self.fileNames = files
        self.files = [(fname, os.path.getsize(fname)) for fname in files]
        self.handles = dict([(fname, None) for (fname, _) in self.files])
        
        
    def openFile(self, fname):
        assert fname in self.fileNames()
        self.handles[key] = file(key, 'rb')
    
    def getHandle(self, fname):
        if not self.handles[key]:
            self.openFile(key)
        return self.handles[key]
        
    def getHandleByPos(self, pos):
        handle, relpos = self.abs2rel(key)
        handle.seek(relpos)
        return handle
    
    def abs2rel(self, pos):
        akku = 0
        for fname, size in self.files:
            if pos < (akku + size):
                return (self[fname], pos-akku)
            akku += size
        return (None, -1)
    
    def getPiece(self, pos, length):
        while length > 0:
            ## WIP
    
    def __getitem__(self, key):        
        if key in self.fileNames.keys()
            self.getHandle(key)
        elif isinstance(key, int):
            self.getHandleByPos(key)



    