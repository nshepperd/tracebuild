import sys
import struct

def fromint(s):
    return struct.unpack('I', s)[0]

def getfilesize(file):
    cursor = file.tell()
    file.seek(0, 2)
    size = file.tell()
    file.seek(cursor, 0)
    return size

fname = sys.argv[1]
with open(fname) as file:
    size = getfilesize(file)
    while file.tell() < size:
        uuid = fromint(file.read(4))
        puuid = fromint(file.read(4))
        cmdlen = fromint(file.read(4))
        cmd = ' '.join(file.read(cmdlen).split('\0')[:-1])
        cwdlen = fromint(file.read(4))
        cwd = file.read(cwdlen)
        print uuid, puuid, cmd, cwd
