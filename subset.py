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

def loadinfoat(file, location):
    tell = file.tell()
    file.seek(location)
    uuid = fromint(file.read(4))
    puuid = fromint(file.read(4))
    commandlen = fromint(file.read(4))
    command = file.read(commandlen).split('\0')[:-1]
    cwdlen = fromint(file.read(4))
    cwd = file.read(cwdlen)
    file.seek(tell)
    return (uuid, puuid, command, cwd)

def match_configure(title, command):
    if title == 'sh' and len(command) > 1:
        if command[1].endswith('configure'):
            return True
        if command[1].endswith('autoconf'):
            return True
    return False

def readinfo(ROOT, LOGPATH, EXTRAROOTS):
    info = {}
    parents = {}
    i = 0

    # index = {}
    # with open(os.path.join(LOGPATH, 'info_index'), 'rb') as file:
    #     fsize = getfilesize(file)
    #     while file.tell() < fsize:
    #         uuid = fromint(file.read(4))
    #         location = fromint(file.read(4))
    #         index[uuid] = location

    with open(os.path.join(LOGPATH, 'info'), 'rb') as file:
        fsize = getfilesize(file)
        while file.tell() < fsize:
            uuid = fromint(file.read(4))
            puuid = fromint(file.read(4))
            commandlen = fromint(file.read(4))
            command = file.read(commandlen).split('\0')[:-1]
            cwdlen = fromint(file.read(4))
            cwd = file.read(cwdlen)

            title = os.path.basename(command[0])

            if puuid in parents:
                parents[uuid] = parents[puuid]
            elif title in ('gcc', 'g++', 'cp', 'install', 'mv', 'gfortran', 'ar', 'perl', 'bbstable', 'bison', 'flex', 'm4', 'debugedit', 'ranlib', 'strip', 'chmod') or match_configure(title, command):
                for ro in [ROOT] + EXTRAROOTS:
                    command = [part.replace(ro, os.path.relpath(ROOT, cwd)) for part in command] # strip absolute paths
                cwd = os.path.relpath(cwd, ROOT)
                info[uuid] = {'command' : command,
                              'cwd' : cwd,
                              'd' : set(),
                              'r' : set(),
                              'w' : set()}
                parents[uuid] = uuid
                # if 'conftest.c' in command:
                #     print command
                #     while puuid in index:
                #         (uuid, puuid, command, cwd) = loadinfoat(file, index[puuid])
                #         print ' ', command
            elif title in ['fork', 'sed', 'rm', 'pwd', 'date', 'ln', 'echo', 'gmake', 'make', 'mkdir', 'grep', 'ls', 'awk', 'cat', 'egrep', 'file', 'find', 'objdump', 'sh']:
                pass
            else:
                print 'unmatched:', command
            if i % 500 == 0:
                scratch('read info', file.tell() / float(fsize))
            i += 1

    with open(os.path.join(LOGPATH, 'access_log'), 'rb') as file:
        fsize = getfilesize(file)
        while file.tell() < fsize:
            uuid = fromint(file.read(4))
            rw = file.read(1)
            size = fromint(file.read(4))
            path = file.read(size)
            if uuid in parents:
                proc = info[parents[uuid]]
                if rw == 'r' and path in proc['w']:
                    # if we write first and only read it later in the same process
                    # it's probably just an output
                    continue
                elif rw == 'd' and path in proc['w']:
                    # if we later _delete_ it, then it was just a temp file
                    proc['w'].remove(path)
                else:
                    proc[rw].add(path)

    for uuid in list(info.keys()):
        if not info[uuid]['w']:
            del info[uuid]

    return info

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'Usage: {0} <root> <logpath> [extra-roots]'.format(sys.argv[0])
        exit(1)

    ROOT = os.path.abspath(sys.argv[1]).rstrip('/')
    LOGPATH = sys.argv[2]
    pprint(readinfo(ROOT, LOGPATH, sys.argv[3:]))
