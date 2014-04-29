#!/usr/bin/python2
import sys, os
import struct
from pprint import pprint

def fromint(s):
    return struct.unpack('I', s)[0]

def getfilesize(file):
    cursor = file.tell()
    file.seek(0, 2)
    size = file.tell()
    file.seek(cursor, 0)
    return size

def scratch(*line):
    sys.stderr.write(' '.join(map(str,line)).ljust(80) + '\r')
    sys.stderr.flush()

def readinfo(fd, ROOT, LOGPATH):
    i = 0
    with open(os.path.join(LOGPATH, 'info'), 'rb') as file:
        fsize = getfilesize(file)
        while file.tell() < fsize:
            tell = file.tell()

            uuid = fromint(file.read(4))
            file.read(4) # puuid
            commandlen = fromint(file.read(4))
            file.read(commandlen) # command
            cwdlen = fromint(file.read(4))
            file.read(cwdlen) # cwd

            fd.write(struct.pack('II', uuid, tell))

            if i % 20000 == 0:
                scratch('read info', file.tell() / float(fsize))
            i += 1

def main(argv):
    if len(argv) < 3:
        print 'Usage: {0} <root> <logpath>'.format(argv[0])
        exit(1)

    ROOT = os.path.abspath(argv[1]).rstrip('/')
    LOGPATH = argv[2]
    TARGET = os.path.join(LOGPATH, 'info_index')
    with open(TARGET, 'wb') as output:
        readinfo(output, ROOT, LOGPATH)

if __name__ == '__main__':
    main(sys.argv)
