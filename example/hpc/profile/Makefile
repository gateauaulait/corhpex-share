CC=clang
CXX=clang++
FLAGS_OPENMP?=-fopenmp
CFLAGS+=-std=gnu99 -g -llikwid

all: libinit.so

libinit.so: initialization.c initialization.h
	$(CC) $(CFLAGS) $(OPENMP_INCLUDE) $(FLAGS_OPENMP)  $< -shared -fPIC -o $@

clean:
	$(RM) libinit.so *~