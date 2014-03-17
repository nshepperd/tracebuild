#!/usr/bin/python2
import sys, os, shutil
import tempfile

i = 1
read = []
while i < len(sys.argv):
    if sys.argv[i] == '--':
        i += 1
        break
    else:
        read.append((sys.argv[i], sys.argv[i+1]))
        i += 2

write = []
while i < len(sys.argv):
    if sys.argv[i] == '--':
        i += 1
        break
    else:
        write.append((sys.argv[i], sys.argv[i+1]))
        i += 2

cwd = sys.argv[i]
command = sys.argv[i+1:]

# (read, write, cwd, command) = eval(sys.argv[1])

ROOT = os.path.abspath(os.getcwd())
TMPDIR = tempfile.mkdtemp()

for (original, final) in read:
    path = os.path.join(TMPDIR, original)
    dirpath = os.path.dirname(path)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    # symlink input files
    os.symlink(os.path.join(ROOT, final), path)

for (original, final) in write:
    path = os.path.join(TMPDIR, original)
    dirpath = os.path.dirname(path)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)

dirpath = os.path.join(TMPDIR, cwd)
if not os.path.exists(dirpath):
    os.makedirs(dirpath)

try:
    os.chdir(os.path.join(TMPDIR, cwd))
    ret = os.spawnvp(os.P_WAIT, command[0], command)

    for (original, final) in write:
        src = os.path.join(TMPDIR, original)
        dst = os.path.join(ROOT, final)
        shutil.copy(src, dst)

    exit(ret)
finally:
    os.chdir(ROOT)
    shutil.rmtree(TMPDIR)
