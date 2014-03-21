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

def scratch(line):
    sys.stdout.write(str(line).ljust(80) + '\r')
    sys.stdout.flush()

def readaccess():
    access = []
    with open(os.path.join(LOGPATH, 'access_log'), 'rb') as file:
        fsize = getfilesize(file)
        while file.tell() < fsize:
            uuid = fromint(file.read(4))
            rw = file.read(1)
            size = fromint(file.read(4))
            path = file.read(size)
            access.append((uuid, rw, path))
    return access

def readinfo():
    info = {}
    with open(os.path.join(LOGPATH, 'info'), 'rb') as file:
        fsize = getfilesize(file)
        while file.tell() < fsize:
            uuid = fromint(file.read(4))
            puuid = fromint(file.read(4))
            cmdlen = fromint(file.read(4))
            cmd = file.read(cmdlen).split('\0')[:-1]
            cwdlen = fromint(file.read(4))
            cwd = file.read(cwdlen)
            info[uuid] = {'parent' : puuid,
                          'command' : cmd,
                          'cwd' : os.path.relpath(cwd, ROOT),
                          'desc' : set(),
                          'children' : set(),
                          'd' : set(),
                          'r' : set(),
                          'w' : set()}


    for uuid in info.keys():
        parent = info[uuid]['parent']
        if parent in info:
            info[parent]['children'].add(uuid)
        while parent in info:
            info[parent]['desc'].add(uuid)
            parent = info[parent]['parent']

    return info

def applyaccess(info, access):
    for (uuid, rw, path) in access:
        if rw == 'r' and path in info[uuid]['w']:
            # if we write first and only read it later in the same process
            # it's probably just an output
            continue
        while uuid in info:
            info[uuid][rw].add(path)
            uuid = info[uuid]['parent']

    for uuid in info.keys():
        for fname in set.intersection(info[uuid]['d'], info[uuid]['w']):
            # if we create then delete a temp file, ignore it
            info[uuid]['d'].discard(fname)
            info[uuid]['w'].discard(fname)

def kill_parents(info, uuid):
    parent = info[uuid]['parent']
    while parent in info:
        node = info[parent]
        del info[parent]
        parent = node['parent']

def kill_descendants(info, uuid):
    for child in info[uuid]['desc']:
        if child in info:
            del info[child]

def filtertree(info):
    # for uuid in list(info.keys()):
    #     if uuid not in info:
    #         continue
    #     if info[uuid]['command'][0] in ['gcc', 'clang']:
    #         # kill_parents(info, uuid)
    #         kill_descendants(info, uuid)
    #     elif info[uuid]['command'][0] in ['fork']:
    #         del info[uuid]

    for uuid in list(info.keys()):
        if not info[uuid]['w']:
            del info[uuid]
        elif info[uuid]['command'][0] == 'fork' and not info[uuid]['children']:
            del info[uuid]

    for uuid in info.keys():
        info[uuid]['desc'] = {c for c in info[uuid]['desc'] if c in info}
        info[uuid]['children'] = {c for c in info[uuid]['children'] if c in info}

def descend(info, uuid=1):
    if uuid == 191:
        print 'here'
    if not info[uuid]['children']:
        return
    elif info[uuid]['command'][0] in ['gcc', 'clang', 'g++']:
        kill_descendants(info, uuid)
    else:
        # info[uuid]['command'][0] == 'fork':
        ch = info[uuid]['children']
        del info[uuid]
        for c in ch:
            descend(info, c)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'Usage: {0} <root> <logpath>'.format(sys.argv[0])
        exit(1)

    ROOT = os.path.abspath(sys.argv[1]).rstrip('/')
    LOGPATH = sys.argv[2]
    access = readaccess()
    info = readinfo()
    applyaccess(info, access)
    filtertree(info)
    descend(info)
    pprint(info)