#!/usr/bin/python2
import sys, os
import tempfile

if len(sys.argv) < 4:
    print 'Usage: {} <root> <log-file> <command ...>'.format(sys.argv[0])
    exit(1)

cwd = os.path.abspath(os.getcwd())
root = os.path.abspath(sys.argv[1])
logfile = os.path.abspath(sys.argv[2])
command = sys.argv[3:]

# We should be running inside the "root"
assert cwd.startswith(root)
subtree = os.path.relpath(cwd, root)

TMPDIR = tempfile.mkdtemp()
MYDIR = os.path.realpath(os.path.dirname(sys.argv[0]))

# Set up environment
COMMANDS = ['cp', 'mv', 'install', 'gcc', 'g++', 'flex', 'lex', 'yacc', 'bison']
for cmd in COMMANDS:
    os.symlink(os.path.join(MYDIR, 'command.py'),
               os.path.join(TMPDIR, cmd))
os.environ['TRACE_LOG_LOCATION'] = logfile
os.environ['PATH'] = TMPDIR + ':' + os.environ['PATH']

# Mount a read/write-tracking filesystem
# !!! We're assuming that the build is relocatable here !!!
fsmount = os.path.join(MYDIR, 'fs')
mount_dir = os.path.join(root, '.mnt')
os.mkdir(mount_dir)
print 'Mounting our tracing fs at {}.'.format(mount_dir)
os.spawnv(os.P_WAIT, fsmount, [fsmount, mount_dir])
os.chdir(os.path.join(mount_dir, cwd.lstrip('/')))

os.spawnvp(os.P_WAIT, command[0], command)

os.chdir(cwd)
os.spawnvp(os.P_WAIT, 'fusermount', ['fusermount', '-u', mount_dir])
os.rmdir(mount_dir)

for cmd in COMMANDS:
    os.unlink(os.path.join(TMPDIR, cmd))
os.rmdir(TMPDIR)
