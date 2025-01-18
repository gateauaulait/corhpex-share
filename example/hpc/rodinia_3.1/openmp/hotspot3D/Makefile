CC = $(CCC) $(MODE)
CCFLAGS = -g -fopenmp
OUTPUT = *.out

3D:
	$(CC) -c -o 3D.o $(CCFLAGS) 3D.c  
	$(CC) -o 3D $(CCFLAGS) 3D.o -lm 

clean:
	rm -f 3D *.o $(OUTPUT)
