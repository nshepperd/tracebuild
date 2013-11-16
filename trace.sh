#!/usr/bin/bash

COMMANDS="cp mv install gcc g++ ld"

TMPDIR=$(realpath $(mktemp -d))
MYDIR=$(realpath $(/bin/dirname $0))

for cmd in $COMMANDS ; do
    ln -s ${MYDIR}/command.py ${TMPDIR}/${cmd}
done

export TRACE_LOG_LOCATION=$(realpath ${MYDIR}/log)

echo "$@"
(PATH=${TMPDIR}:${PATH} "$@")

for cmd in $COMMANDS ; do
    rm ${TMPDIR}/${cmd}
done
rmdir $TMPDIR
