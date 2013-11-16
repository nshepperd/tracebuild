import sys, os

logfile = sys.argv[1]
root = sys.argv[2]
root = os.path.realpath(root)

def interpret(pid, cwd, command):
    print pid, cwd, ' '.join(command).replace(root, os.path.relpath(root, cwd))
    for line in open('{}.strace.{}'.format(logfile, pid), 'r'):
        if line.split(' ', 1)[1].startswith('open'):
            print line.strip()
    # if command[0] == 'cp':
    #     files = []
    #     opts = []
    #     for arg in command[1:]:
    #         if arg[0] == '-':
    #             opts.append(arg)
    #         else:
    #             files.append(arg)
    #     # interpret paths
    #     files = [os.path.join(cwd, fname) for fname in files]
    #     target = files.pop()
    #     if os.path.basename(target) == 'conftest.dir':
    #         # autotools shit
    #         return
    #     # get target directory
    #     tdir = os.path.dirname(target)
    #     # relativise wrt target location
    #     files = [os.path.relpath(fname, tdir) for fname in files]
    #     target = os.path.relpath(target, tdir)
    #     # relativise tdir wrt root
    #     tdir = os.path.relpath(tdir, root)
    #     print '[{}] cp {} {} {}'.format(tdir, opts, files, target)
    # elif command[0] == 'g++':
    #     output = []
    #     inputs = []
        

with open(logfile, 'r') as file:
    for line in file:
        (pid, cwd, command) = eval(line)
        interpret(pid, cwd, command)
