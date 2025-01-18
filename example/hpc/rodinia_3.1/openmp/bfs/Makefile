# C compiler
CC = $(CCC) $(MODE)
ICC = icc
CC_FLAGS = -g -fopenmp  

all: bfs #bfs_offload

bfs.o: bfs.cpp 
	$(CC) $(CC_FLAGS) bfs.cpp -c -o bfs.o 

bfs: bfs.o
	$(CC) $(CC_FLAGS) bfs.o -o bfs -lstdc++ -lm

bfs_offload: bfs.cpp
	$(CC) $(CC_FLAGS) -DOMP_OFFLOAD bfs.cpp -o bfs_offload

clean:
	rm -f bfs bfs_offload result.txt *.o
