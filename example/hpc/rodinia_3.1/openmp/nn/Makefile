LOCAL_CC = gcc -g -Wall
CC = $(CCC) $(MODE)
CFLAGS = -lm -fopenmp -Wall


all : nn

clean :
	rm -rf *.o nn

nn.o : nn_openmp.c
	$(CC) -o $@ -c $< $(LDFLAGS) $(CFLAGS) 

nn : nn_openmp.o
	$(CC) -o $@ $< $(LDFLAGS) $(CFLAGS) 

hurricane_gen : hurricane_gen.c
	$(LOCAL_CC) -o $@ $< -lm

