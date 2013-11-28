#!/usr/bin/python2
import sys, os
from collections import namedtuple

if len(sys.argv) < 4:
    print 'Usage: {} <log-file> <root> <output-file>'.format(sys.argv[0])
    exit(1)

logfile = sys.argv[1]
root = sys.argv[2]
root = os.path.realpath(root)        
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
                operations[pid].read.add(os.path.relpath(fname, root))
            else:
                assert op == 'write'
                # print 'write:', pid, os.path.relpath(fname, root)
                operations[pid].write.add(os.path.relpath(fname, root))
        else:
            id += 1
            # Create a new command
            (pid, cwd, command) = line
            # print 'create:', pid
            # Paths in the recorded command line are always of the form /root/.mnt/root/...
            # We need to clean this up so the build can be relocated.
            sub_root = os.path.join(os.path.join(root, '.mnt'), root.lstrip('/')) # /root/.mnt/root
            rel_root = os.path.relpath(sub_root, cwd)                             # cwd -> root 
            cwd = cwd.replace(sub_root, '').lstrip('/') or '.'                    # root -> cwd
            # Strip out all absolute paths (/root/.mnt/root) from commands
            command = [x.replace(sub_root, rel_root) for x in command]
            operations[pid] = Operation(set(), set(), cwd, command, id)

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
        file.write('all: {}\n\n'.format(' '.join(all_outputs)))
        file.write('clean:\n\trm -f {}\n\n'.format(' '.join(all_outputs)))
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

# write_makefile(to)
write_tupfile(to)
