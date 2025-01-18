# C compiler
CC = $(CCC) $(MODE)
ICC = icc
CC_FLAGS = -g -fopenmp 
LD= -lstdc++ -lm
OFFLOAD_CC_FLAGS = -offload-option,mic,compiler,"-no-opt-prefetch"

all: hotspot #hotspot_offload 


hotspot: hotspot_openmp.cpp Makefile 
	$(CC) $(CC_FLAGS) hotspot_openmp.cpp -c -o hotspot_openmp.o 
	$(CC) $(CC_FLAGS) $(LD) hotspot_openmp.o -o hotspot 

hotspot_offload: hotspot_openmp.o Makefile
	$(ICC) $(CC_FLAGS) $(OFFLOAD_CC_FLAGS) -DOMP_OFFLOAD hotspot_openmp.o -o hotspot_offload

clean:
	rm -f hotspot hotspot_offload *.o *.ll
