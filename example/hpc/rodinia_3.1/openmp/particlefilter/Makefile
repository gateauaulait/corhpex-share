#makefile

all: openmp

ex_particle_OPENMP_seq.o: ex_particle_OPENMP_seq.c
	$(CCC) $(MODE)  -fopenmp ex_particle_OPENMP_seq.c -c -o ex_particle_OPENMP_seq.o 

openmp: ex_particle_OPENMP_seq.o
	$(CCC) $(MODE)  -ffast-math -fopenmp ex_particle_OPENMP_seq.o -o particle_filter -lm 

icc_openmp: ex_particle_OPENMP_seq.c
	icc -O3 -fast -openmp ex_particle_OPENMP_seq.c -o particle_filter


clean:
	rm -f particle_filter *.o *.ll
