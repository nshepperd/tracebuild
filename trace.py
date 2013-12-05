#!/usr/bin/python2
import sys, os
import tempfile

if len(sys.argv) < 4:
    print 'Usage: {0} <root> <log-file> <command ...>'.format(sys.argv[0])
    exit(1)

cwd = os.path.abspath(os.getcwd())
root = os.path.abspath(sys.argv[1]).rstrip('/')
logfile = os.path.abspath(sys.argv[2]).rstrip('/').replace(root, root + '.tmp')
command = sys.argv[3:]

# We should be running inside the "root"
assert cwd.startswith(root)
subtree = os.path.relpath(cwd, root)

TMPDIR = tempfile.mkdtemp()
MYDIR = os.path.realpath(os.path.dirname(sys.argv[0]))

# Set up environment
COMMANDS = ['cp', 'mv', 'install', 'gcc', 'g++', 'gfortran', 'flex', 'lex', 'yacc', 'bison']
for cmd in COMMANDS:
    os.symlink(os.path.join(MYDIR, 'command.py'),
               os.path.join(TMPDIR, cmd))
os.environ['TRACE_LOG_LOCATION'] = logfile
os.environ['FUSE_ROOT'] = root + '.tmp'
os.environ['PATH'] = TMPDIR + ':' + os.environ['PATH']

# Mount a read/write-tracking filesystem
os.chdir('/')
os.rename(root, root + '.tmp')
fsmount = os.path.join(MYDIR, 'fs')
mount_dir = root
os.mkdir(mount_dir)
os.spawnv(os.P_WAIT, fsmount, [fsmount, mount_dir])
os.chdir(cwd)

os.spawnvp(os.P_WAIT, command[0], command)

os.chdir('/')
os.spawnvp(os.P_WAIT, 'fusermount', ['fusermount', '-u', mount_dir])
os.rmdir(mount_dir)
os.rename(root + '.tmp', root)

for cmd in COMMANDS:
    os.unlink(os.path.join(TMPDIR, cmd))
os.rmdir(TMPDIR)
