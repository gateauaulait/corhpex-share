# C compiler
CC = $(CCC) $(MODE)
ICC = icc
CC_FLAGS = -g -fopenmp
OFFLOAD_CC_FLAGS = -offload-option,mic,compiler,"-no-opt-prefetch"

all: needle #needle_offload

needle.o: needle.cpp
	$(CC) $(CC_FLAGS) needle.cpp -c -o needle.o 

needle: needle.o
	$(CC) $(CC_FLAGS) -lstdc++ -lm needle.o -o needle 

needle_offload:
	$(ICC) $(CC_FLAGS) $(OFFLOAD_CC_FLAGS) -DOMP_OFFLOAD needle.cpp -o needle_offload

clean:
	rm -f needle needle_offload *.o *.ll
