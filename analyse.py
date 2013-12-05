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
            if pid not in operations:
                # print 'Discarding irrelevant action', pid
                continue
            if op == 'read':
                # print 'read:', pid, os.path.relpath(fname, root)
                # operations[pid].read.add(os.path.relpath(fname, root))
                operations[pid].read.add(fname.lstrip('/'))
            else:
                assert op == 'write'
                # print 'write:', pid, os.path.relpath(fname, root)
                operations[pid].write.add(fname.lstrip('/'))
        else:
            id += 1
            # Create a new command
            (pid, cwd, command) = line
            # print 'create:', pid
            # Paths in the recorded command line may be of the form /root/...
            # We need to clean this up so the build can be relocated.
            rel_root = os.path.relpath(root, cwd)                             # cwd -> root 
            cwd = os.path.relpath(cwd, root)
            # Strip out all absolute paths (/root/.mnt/root) from commands
            command = [x.replace(root, rel_root) for x in command]
            operations[pid] = Operation(set(), set(), cwd, command, id)

if filter:
    outputs = set()
    for pid in sorted(operations.keys(), key=lambda z: operations[z].id):
        for fname in operations[pid].read:
            if not (fname in outputs or os.path.exists(os.path.join(root, fname.lstrip('/')))):
                print 'dropping command with missing inputs:', operations[pid].command
                del operations[pid]
                break
        else:
            outputs.update(operations[pid].write)


to_delete = set()
owned = {}
for pid in sorted(operations.keys(), key=lambda z: operations[z].id):
    for fname in operations[pid].write:
        if fname not in owned:
            owned[fname] = pid
        elif owned[fname] != pid:
            print 'conflict!'
            print ' ', operations[owned[fname]].cwd, ' '.join(operations[owned[fname]].command)
            print ' ', operations[pid].cwd, ' '.join(operations[pid].command)
            to_delete.add(pid)
            owned[fname] = pid
for pid in to_delete:
    del operations[pid]

if filter:
    outputs = set()
    for pid in sorted(operations.keys(), key=lambda z: operations[z].id):
        for fname in operations[pid].read:
            if not (fname in outputs or os.path.exists(os.path.join(root, fname.lstrip('/')))):
                print 'dropping command with missing inputs:', operations[pid].command
                del operations[pid]
                break
        else:
            outputs.update(operations[pid].write)

def write_makefile(fname):
    entries = []
    all_outputs = []
    for op in operations.values():
        if 'Tpo' in ' '.join(op.command):
            continue
        if op.write:
            read = sorted(op.read)
            write = sorted(op.write)
            all_outputs.extend(write)
            entries.append('{write}: {read}\n\t(cd {cwd} && {command})'.format(
                read=' '.join(read),
                write=' '.join(write),
                cwd=op.cwd,
                command=' '.join(op.command)))

    with open(fname, 'w') as file:
        file.write('all: {0}\n\n'.format(' '.join(all_outputs)))
        file.write('clean:\n\trm -f {0}\n\n'.format(' '.join(all_outputs)))
        for item in sorted(entries):
            file.write(item + '\n\n')

def write_tupfile(fname):
    entries = []

    for op in sorted(operations.values(), key=lambda z: z.id):
        # Sort by pid, so we get the topological sort required for tup.
        if 'Tpo' in ' '.join(op.command):
            continue
        if op.write:
            read = sorted(op.read)
            write = sorted(op.write)
            entries.append(': {read} |> (cd {cwd} && {command}) |> {write}'.format(
                read=' '.join(read),
                write=' '.join(write),
                cwd=op.cwd,
                command=' '.join(op.command)))

    with open(fname, 'w') as file:
        for item in entries:
            file.write(item + '\n\n')

if make == 'make':
    write_makefile(to)
else:
    assert make == 'tup'
    write_tupfile(to)
