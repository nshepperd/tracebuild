#!/usr/bin/python2
import sys, os
import tempfile

COMMANDS = ['cp', 'mv', 'install', 'gcc', 'g++']

TMPDIR = tempfile.mkdtemp()
MYDIR = os.path.realpath(os.path.dirname(sys.argv[0]))

for cmd in COMMANDS:
    os.symlink(os.path.join(MYDIR, 'command.py'),
               os.path.join(TMPDIR, cmd))

os.environ['TRACE_LOG_LOCATION'] = os.path.join(MYDIR, 'log')
os.environ['PATH'] = TMPDIR + ':' + os.environ['PATH']

root = os.path.realpath(sys.argv[1])
command = sys.argv[2:]
os.spawnvp(os.P_WAIT, command[0], command)

for cmd in COMMANDS:
    os.unlink(os.path.join(TMPDIR, cmd))
os.rmdir(TMPDIR)
