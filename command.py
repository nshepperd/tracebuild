#!/usr/bin/python2
import sys, os

op = os.path.basename(sys.argv[0])
mypath = os.path.abspath(os.path.dirname(sys.argv[0]))
PATH = os.getenv('PATH').split(':')

# Delete ourselves from the PATH
if mypath in PATH:
    del PATH[PATH.index(mypath)]
os.environ['PATH'] = ':'.join(PATH)

# Log a command entry
LOGFILE = os.getenv('TRACE_LOG_LOCATION')
with open(LOGFILE, 'a') as file:
    file.write(repr((os.getpid(), os.getcwd(), [op] + sys.argv[1:])) + '\n')

# Create a process group for this command
os.setpgid(0, 0)

# Execute
command = list(sys.argv)
command[0] = op
os.execvp(op, command)

# STRACE_FILE = '{}.strace.{}'.format(LOGFILE, os.getpid())
# os.execvp('strace', ['strace', '-o', STRACE_FILE, '-f', '-e', 'open,chdir'] + command)

