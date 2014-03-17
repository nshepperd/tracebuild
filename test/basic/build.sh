#!/bin/bash

gcc -c -o one.o one.c
gcc -o one one.o
(cd dir && gcc -c -o two.o two.c)
(cd dir && gcc -o two two.o)
