import sys, os

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
        # rd = [os.path.relpath(x, writedir) for x in rd]
        # wr = [os.path.relpath(x, writedir) for x in wr]
        entries.append('{}: {}\n\t(cd {} && {})'.format(' '.join(wr), ' '.join(rd), cdirs[pid], ' '.join(commands[pid])))
        # entries.append(( writedir, ': {} |> (cd {} && {}) |> {}'.format(' '.join(rd), os.path.relpath(cdirs[pid], writedir), ' '.join(commands[pid]), ' '.join(wr)) ))

def concat(gen):
    res = []
    for item in gen:
        res.extend(item)
    return res

with open('Makefile', 'w') as file:
    # file.write('all: {}\n\n'.format(' '.join(concat(writes.values()))))
    file.write('all: libCLHEP-2.0.3.2.so\n\n')
    file.write('clean:\n\trm -f {}\n\n'.format(' '.join(concat(writes.values()))))
    for item in sorted(entries):
        file.write(item + '\n\n')

# for (cwd, cmd) in sorted(entries):
#     target_dir = os.path.join(to, cwd)
#     # if not os.path.exists(target_dir):
#     #     os.makedirs(target_dir)
#     # with open(os.path.join(target_dir, 'Tupfile'), 'a') as file:
#     #     file.write(cmd + '\n')
#     print target_dir, cmd
