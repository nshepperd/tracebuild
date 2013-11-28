all: one two
clean:
	rm *.o one two

one.o: one.c
	gcc -c -o one.o one.c
one: one.o
	gcc -o one one.o

two.o: two.c
	gcc -c -o two.o two.c
two: two.o
	gcc -o two two.o
