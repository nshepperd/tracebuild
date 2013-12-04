all: one dir/two
clean:
	rm *.o dir/*.o one dir/two

one.o: one.c
	gcc -c -o one.o one.c
one: one.o
	gcc -o one one.o

dir/two.o: dir/two.c
	(cd dir && gcc -c -o two.o two.c)
dir/two: dir/two.o
	(cd dir && gcc -o two two.o)
