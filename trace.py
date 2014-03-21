#!/usr/bin/python2
import sys, os
import tempfile

if len(sys.argv) < 4:
    print 'Usage: {0} <root> <logpath> <command ...>'.format(sys.argv[0])
    exit(1)

cwd = os.path.abspath(os.getcwd())
root = os.path.abspath(sys.argv[1]).rstrip('/')
logpath = os.path.abspath(sys.argv[2]).rstrip('/')
os.mkdir(logpath)
logpath = logpath.replace(root, root + '.tmp')
command = sys.argv[3:]

# We should be running inside the "root"
assert cwd.startswith(root)
subtree = os.path.relpath(cwd, root)

MYDIR = os.path.realpath(os.path.dirname(sys.argv[0]))

# Set up environment
# COMMANDS = ['cp', 'mv', 'install', 'gcc', 'g++', 'gfortran', 'flex', 'lex', 'yacc', 'bison']
os.environ['LOGPATH'] = logpath
os.environ['FUSE_ROOT'] = root + '.tmp'


# Mount a read/write-tracking filesystem
os.chdir('/')
os.rename(root, root + '.tmp')
fsmount = os.path.join(MYDIR, 'fs')
mount_dir = root
os.mkdir(mount_dir)
os.spawnv(os.P_WAIT, fsmount, [fsmount, mount_dir])
os.chdir(cwd)

# create lockfile
with open(os.path.join(logpath, 'lock'), 'wb') as file:
    file.write('lock')

try:
    os.environ['LD_PRELOAD'] = os.path.join(MYDIR, 'libpid.so')
    os.spawnvp(os.P_WAIT, command[0], command)
finally:
    del os.environ['LD_PRELOAD']
    os.chdir('/')
    while os.spawnvp(os.P_WAIT, 'fusermount', ['fusermount', '-u', mount_dir]) != 0:
        pass
    os.rmdir(mount_dir)
    os.rename(root + '.tmp', root)
