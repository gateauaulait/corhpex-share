# Example
# target: dependencies
	# command 1
	# command 2
          # .
          # .
          # .
	# command n

# link objects(binaries) together
a.out:	main.o
	$(CCC) $(MODE) -lstdc++ -lm	main.o \
			-lm -fopenmp -o srad

# compile main function file into object (binary)
main.o: 	main.c \
				define.c \
				graphics.c
	$(CCC) $(MODE)	main.c \
			-c -fopenmp

# delete all object files
clean:
	rm -f *.o srad *.ll
