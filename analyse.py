#!/usr/bin/python2
import sys, os

if len(sys.argv) < 4:
    print 'Usage: {} <log-file> <root> <output-file>'.format(sys.argv[0])
    exit(1)

logfile = sys.argv[1]
root = sys.argv[2]
root = os.path.realpath(root)        
to = sys.argv[3]

pids = set()

writes = {}
reads = {}
commands = {}
cdirs = {}

with open(logfile, 'r') as file:
    for line in file:
        line = eval(line)
        if line[1] in ('read', 'write'):
            (pid, op, fname) = line
            if pid not in writes:
                writes[pid] = set()
            if pid not in reads:
                reads[pid] = set()
            if op == 'read':
                reads[pid].add(os.path.relpath(fname, root))
            else:
                assert op == 'write'
                writes[pid].add(os.path.relpath(fname, root))
        else:
            (pid, cwd, command) = line
            # strip bullshit from the paths
            sub_root = os.path.join(os.path.join(root, '.mnt'), root.lstrip('/'))
            rel_root = os.path.relpath(sub_root, cwd)
            cwd = cwd.replace(sub_root, '').lstrip('/')
            command = [x.replace(sub_root, rel_root) for x in command]
            pids.add(pid)
            cdirs[pid] = cwd
            commands[pid] = command

entries = []

for pid in pids:
    if len(writes[pid]):
        rd = sorted(reads[pid])
        wr = sorted(writes[pid])
        writedir = os.path.dirname(wr[0]) or '.'
        if cdirs[pid] == '':
            cdirs[pid] = '.'
        entries.append('{}: {}\n\t(cd {} && {})'.format(' '.join(wr), ' '.join(rd), cdirs[pid], ' '.join(commands[pid])))

        # entries.append(': {rd} |> (cd {cwd} && {cmd}) |> {wr}'.format(rd=' '.join(rd),
        #                                                               wr=' '.join(wr),
        #                                                               cwd=cdirs[pid],
        #                                                               cmd=' '.join(commands[pid])))

def concat(gen):
    res = []
    for item in gen:
        res.extend(item)
    return res

with open(to, 'w') as file:
    file.write('all: {}\n\n'.format(' '.join(concat(writes.values()))))
    file.write('clean:\n\trm -f {}\n\n'.format(' '.join(concat(writes.values()))))
    for item in sorted(entries):
        file.write(item + '\n\n')
