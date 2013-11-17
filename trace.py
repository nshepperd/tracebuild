#!/usr/bin/python2
import sys, os
import tempfile

root = os.path.realpath(sys.argv[1])
logfile = os.path.realpath(sys.argv[2])
command = sys.argv[3:]

TMPDIR = tempfile.mkdtemp()
MYDIR = os.path.realpath(os.path.dirname(sys.argv[0]))

# Set up environment
COMMANDS = ['cp', 'mv', 'install', 'gcc', 'g++']
for cmd in COMMANDS:
    os.symlink(os.path.join(MYDIR, 'command.py'),
               os.path.join(TMPDIR, cmd))

os.environ['TRACE_LOG_LOCATION'] = os.path.realpath(logfile)
os.environ['PATH'] = TMPDIR + ':' + os.environ['PATH']

os.spawnvp(os.P_WAIT, command[0], command)

for cmd in COMMANDS:
    os.unlink(os.path.join(TMPDIR, cmd))
os.rmdir(TMPDIR)
