#!/usr/bin/python2
import sys, os
import struct
import argparse
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

def replaceall(s, repl, new):
    for r in repl:
        s = s.replace(r, new)
    return s

def readinfo(roots, logpath):
    info = {}
    parents = {}
    killed = set()
    i = 0

    # index = {}
    # with open(os.path.join(LOGPATH, 'info_index'), 'rb') as file:
    #     fsize = getfilesize(file)
    #     while file.tell() < fsize:
    #         uuid = fromint(file.read(4))
    #         location = fromint(file.read(4))
    #         index[uuid] = location

    with open(os.path.join(logpath, 'info'), 'rb') as file:
        fsize = getfilesize(file)
        while file.tell() < fsize:
            uuid = fromint(file.read(4))
            puuid = fromint(file.read(4))
            commandlen = fromint(file.read(4))
            command = file.read(commandlen).split('\0')[:-1]
            cwdlen = fromint(file.read(4))
            cwd = file.read(cwdlen)

            title = os.path.basename(command[0])

            cwd = replaceall(cwd, roots, '') or '/'

            if puuid in parents:
                parents[uuid] = parents[puuid]
            elif puuid in killed:
                killed.add(uuid)
            elif title in ('gcc', 'g++', 'cp', 'install', 'mv', 'gfortran', 'ar', 'perl', 'bbstable', 'bison', 'flex', 'm4', 'ranlib', 'strip', 'chmod'):
                command = [replaceall(part, roots, os.path.relpath('/', cwd)) for part in command] # strip absolute paths
                cwd = os.path.relpath(cwd, '/')
                info[uuid] = {'command' : command,
                              'cwd' : cwd,
                              'd' : set(),
                              'r' : set(),
                              'w' : set()}
                parents[uuid] = uuid
            elif match_configure(title, command):
                killed.add(uuid)
            elif title in ['fork', 'sed', 'rm', 'pwd', 'date', 'ln', 'echo', 'gmake', 'make', 'mkdir', 'grep', 'ls', 'awk', 'cat', 'egrep', 'file', 'find', 'objdump', 'sh', 'debugedit', 'uname', 'mktemp', 'sort', 'cut', 'diff']:
                pass
            else:
                print 'unmatched:', command
            if i % 500 == 0:
                scratch('read info', file.tell() / float(fsize))
            i += 1

    with open(os.path.join(logpath, 'access_log'), 'rb') as file:
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

    version = {}

    for uuid in sorted(info.keys()):
        proc = info[uuid]
        read = proc['r'].union(proc['d'])
        for fname in read:
            if fname not in version:
                version[fname] = 0
        proc['r'] = [(fname, version[fname]) for fname in read]
        del proc['d']
        for fname in proc['w']:
            version[fname] = 1 + version.get(fname, 0)
        proc['w'] = [(fname, version[fname]) for fname in proc['w']]
        print proc

    have = set(version.items())

    # for uuid in sorted(info.keys()):
    #     proc = info[uuid]
    #     inputs = []
    #     for (fname, v) in proc['r']:
    #         if v == version[fname]:
    #             inputs.append((fname, fname))
    #         else:
    #             inputs.append((fname, fname + ',' + v))
    #     for (fname, v) in proc['w']:
    #         if v == version[fname]:
    #             inputs.append((fname, fname))
    #         else:
    #             inputs.append((fname, fname + ',' + v))


    return info

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Find relevant build steps in log files.")
    parser.add_argument('--root', action='append', help="Roots of the build.", required=True)
    parser.add_argument('--mount', help="Somewhere the completed build can be found.")
    parser.add_argument('logpath', help="Path to the logs directory.")
    args = parser.parse_args()

    ROOTS = [os.path.abspath(path).rstrip('/') for path in args.root]
    info = readinfo(ROOTS, args.logpath)
    # pprint(info)
