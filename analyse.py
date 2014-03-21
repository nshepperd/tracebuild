#!/usr/bin/python2
import sys, os
from collections import namedtuple
from pprint import pprint
import pstree

def shell_escape(string):
    return "'" + string.replace("'", "'\\''") + "'"

def get_action(op):
    if op['command'][0] == 'mv':
        op['command'][0] = 'cp'
    if all([files[fid].final == files[fid].original for fid in op['r'] + op['w']]):
        if op['cwd'] == '.':
            return ' '.join(op['command'])
        else:
            return '(cd {cwd} && {command})'.format(cwd=op['cwd'], command=' '.join(map(shell_escape, op['command'])))
    else:
        iread = ' '.join(files[fid].original + ' ' + files[fid].final for fid in op['r'])
        iwrite = ' '.join(files[fid].original + ' ' + files[fid].final for fid in op['w'])
        return './isolate {0} -- {1} -- {2} {3}'.format(iread, iwrite, op['cwd'], ' '.join(map(shell_escape, op['command'])))


def write_makefile(fname):
    entries = []
    all_outputs = []
    for uuid in sorted(info.keys()):
        op = info[uuid]
        read = sorted([files[fid].final for fid in op['r']])
        write = sorted([files[fid].final for fid in op['w']])
        all_outputs.extend(write)
        entries.append('{write}: {read}\n\t{action}'.format(
            read=' '.join(read),
            write=' '.join(write),
            action=get_action(op)))

    with open(fname, 'w') as file:
        file.write('all: {0}\n\n'.format(' '.join(all_outputs)))
        file.write('clean:\n\trm -f {0}\n\n'.format(' '.join(all_outputs)))
        for item in entries:
            file.write(item + '\n\n')

def write_tupfile(fname):
    entries = []

    for uuid in sorted(info.keys()):
        # Sort by id, so we get the topological sort required for tup.
        op = info[uuid]
        read = sorted([files[fid].final for fid in op['r']])
        write = sorted([files[fid].final for fid in op['w']])
        entries.append(': {read} |> {action} |> {write}'.format(
            read=' '.join(read),
            write=' '.join(write),
            action=get_action(op)))

    with open(fname, 'w') as file:
        for item in entries:
            file.write(item + '\n\n')

if __name__ == '__main__':
    make = 'tup'
    filter = False
    if '--tup' in sys.argv:
        make = 'tup'
        del sys.argv[sys.argv.index('--tup')]
    if '--make' in sys.argv:
        make = 'make'
        del sys.argv[sys.argv.index('--make')]
    if '--filter' in sys.argv:
        filter = True
        del sys.argv[sys.argv.index('--filter')]

    if len(sys.argv) < 4:
        print 'Usage: {0} [--tup|--make] [--filter] <root> <log-file> <output-file>'.format(sys.argv[0])
        exit(1)

    ROOT = sys.argv[1]
    ROOT = os.path.abspath(ROOT).rstrip('/')
    LOGPATH = sys.argv[2]
    output = sys.argv[3]

    info = pstree.getinfo(ROOT, LOGPATH)

    sources = set()
    File = namedtuple('File', ['original', 'final', 'id', 'v'])
    files = {} # id -> File(...)
    nameid = {} # current filename -> id

    for uuid in sorted(info.keys()):
        op = info[uuid]
        read = []
        for fname in op['r'].union(op['d']):
            if fname in nameid:
                # created file, id ifiles[fname]
                read.append(nameid[fname])
            else:
                sources.add(fname)
                fid = max([0] + files.keys()) + 1
                files[fid] = File(fname, fname, fid, 1)
                nameid[fname] = fid
                read.append(fid)
        write = []
        for fname in op['w']:
            if fname in sources:
                del info[uuid]
                print 'warning: operation {0} writes to source file {1}'.format(op.command, fname)
                break
            elif fname in nameid:
                # already created, we're overwriting!
                orig = nameid[fname]
                files[orig] = File(files[orig].original, '{0}-{1}'.format(files[orig].original, files[orig].v), orig, files[orig].v)
                fid = max([0] + files.keys()) + 1
                files[fid] = File(fname, fname, fid, files[orig].v + 1)
                nameid[fname] = fid
                write.append(fid)
            else:
                # new output file
                fid = max([0] + files.keys()) + 1
                files[fid] = File(fname, fname, fid, 1)
                nameid[fname] = fid
                write.append(fid)
        else:
            info[uuid]['r'] = read
            info[uuid]['w'] = write
            del info[uuid]['d']

    if filter:
        # Only keep commands whose inputs are regular files, or will be created by another command which we keep
        outputs = set()
        for uuid in sorted(info.keys()):
            op = info[uuid]
            for fid in op['r']:
                if not (fid in outputs or os.path.exists(os.path.join(ROOT, files[fid].original))):
                    print 'dropping command with missing inputs:', op['command']
                    print ' ', files[fid]
                    del info[uuid]
                    break
                else:
                    outputs.update(set(op['w']))

    assert make in ('make', 'tup')
    if make == 'make':
        write_makefile(output)
    else:
        write_tupfile(output)
