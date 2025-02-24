CC=clang
CXX=clang++
FLAGS_OPENMP?=-fopenmp
CFLAGS+=-std=gnu99 -g 

all: libinit.so

initialization.o: initialization.c initialization.h
	$(CC) $(CFLAGS) $(OPENMP_INCLUDE) $(FLAGS_OPENMP)  $< -fPIC -c -o $@

energy.o: energy.c energy.h
	$(CC) $(CFLAGS) $(OPENMP_INCLUDE) $(FLAGS_OPENMP) $< -fPIC -c -o $@ 

libinit.so: initialization.o energy.o
	$(CC) $(CFLAGS) $(OPENMP_INCLUDE) $(FLAGS_OPENMP)  $^ -shared -o $@

clean:
	$(RM) libinit.so *~ *.o