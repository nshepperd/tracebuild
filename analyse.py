#!/usr/bin/python2
import sys, os
from collections import namedtuple

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

root = sys.argv[1]
root = os.path.realpath(root)
logfile = sys.argv[2]
to = sys.argv[3]

pid_to_id = {}

Operation = namedtuple('Operation', ['read', 'write', 'cwd', 'command', 'id'])
operations = {}

with open(logfile, 'r') as file:
    id = 0
    for line in file:
        line = eval(line)
        if line[1] in ('read', 'write'):
            # Add an entry to their inputs/outputs.
            # Note, the command itself should always be listed before any inputs and outputs.
            (pid, op, fname) = line
            # If not, discard it
            if pid not in pid_to_id:
                # print 'Discarding irrelevant action', pid
                continue
            cid = pid_to_id[pid]
            assert op in ('read', 'write')
            if op == 'read':
                operations[cid].read.add(fname.lstrip('/'))
            else:
                operations[cid].write.add(fname.lstrip('/'))
        else:
            id += 1 # id: topological sort order
            # Create a new command
            (pid, cwd, command) = line
            # print 'create:', pid
            # Paths in the recorded command line may be of the form /root/...
            # We need to clean this up so the build can be relocated.
            rel_root = os.path.relpath(root, cwd)                             # cwd -> root
            cwd = os.path.relpath(cwd, root)
            # Strip out all absolute paths (/root/.mnt/root) from commands
            command = [x.replace(root, rel_root) for x in command]
            operations[id] = Operation(set(), set(), cwd, command, id)
            pid_to_id[pid] = id

sources = set()

File = namedtuple('File', ['original', 'final', 'id', 'v'])
files = {} # id -> File(...)
ifiles = {} # current filename -> id

for id in sorted(operations.keys()):
    op = operations[id]
    read = []
    for fname in op.read:
        if fname in ifiles:
            # created file, id ifiles[fname]
            read.append(ifiles[fname])
        else:
            sources.add(fname)
            fid = max([0] + files.keys()) + 1
            files[fid] = File(fname, fname, fid, 1)
            ifiles[fname] = fid
            read.append(fid)
    write = []
    for fname in op.write:
        if fname in sources:
            del operations[id]
            print 'warning: operation {0} writes to source file {1}'.format(op.command, fname)
            break
        elif fname in ifiles:
            # already created, we're overwriting!
            orig = ifiles[fname]
            files[orig] = File(files[orig].original, '{}-{}'.format(files[orig].original, files[orig].v), orig, files[orig].v)
            fid = max([0] + files.keys()) + 1
            files[fid] = File(fname, fname, fid, files[orig].v + 1)
            ifiles[fname] = fid
            write.append(fid)
        else:
            fid = max([0] + files.keys()) + 1
            files[fid] = File(fname, fname, fid, 1)
            ifiles[fname] = fid
            write.append(fid)
    else:
        operations[id] = Operation(read, write, op.cwd, op.command, op.id)

if filter:
    # Only keep commands whose inputs are regular files, or will be created by another command which we keep
    outputs = set()
    for id in sorted(operations.keys()):
        for fid in operations[id].read:
            if not (fid in outputs or os.path.exists(os.path.join(root, files[fid].original))):
                print 'dropping command with missing inputs:', operations[id].command
                del operations[id]
                break
        else:
            outputs.update(set(operations[id].write))

# for id in sorted(operations.keys()):
#     print operations[id]

# for fid in sorted(files.keys()):
#     print files[fid]

def shell_escape(string):
    return "'" + string.replace("'", "'\\''") + "'"

def get_action(op):
    if all([files[fid].final == files[fid].original for fid in op.read + op.write]):
        if op.cwd == '.':
            return ' '.join(op.command)
        else:
            return '(cd {cwd} && {command})'.format(cwd=op.cwd, command=' '.join(op.command))
    else:
        iread = ' '.join(files[fid].original + ' ' + files[fid].final for fid in op.read)
        iwrite = ' '.join(files[fid].original + ' ' + files[fid].final for fid in op.write)
        return './isolate {} -- {} -- {} {}'.format(iread, iwrite, op.cwd, ' '.join(op.command))

def write_makefile(fname):
    entries = []
    all_outputs = []
    for oid in sorted(operations.keys()):
        op = operations[oid]
        # if 'Tpo' in ' '.join(op.command):
        #     continue
        if op.write:
            read = sorted([files[fid].final for fid in op.read])
            write = sorted([files[fid].final for fid in op.write])
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

    for oid in sorted(operations.keys()):
        # Sort by id, so we get the topological sort required for tup.
        op = operations[oid]
        if op.write:
            read = sorted([files[fid].final for fid in op.read])
            write = sorted([files[fid].final for fid in op.write])
            entries.append(': {read} |> {action} |> {write}'.format(
                read=' '.join(read),
                write=' '.join(write),
                action=get_action(op)))

    with open(fname, 'w') as file:
        for item in entries:
            file.write(item + '\n\n')

assert make in ('make', 'tup')
if make == 'make':
    write_makefile(to)
else:
    write_tupfile(to)
