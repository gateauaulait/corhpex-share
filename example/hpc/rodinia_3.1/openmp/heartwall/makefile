
ifdef OUTPUT
override OUTPUT = -DOUTPUT
endif

CXX=$(CCC) $(MODE) 
LD= -lstdc++ -lm

# link objects(binaries) together
heartwall: main.o ./AVI/avilib.o ./AVI/avimod.o
	$(CXX) main.o ./AVI/avilib.o ./AVI/avimod.o -lm -fopenmp -o heartwall

# compile main function file into object (binary)
main.o: main.c define.c kernel.c
	$(CXX) $(OUTPUT) main.c -I./AVI -c -fopenmp

./AVI/avilib.o ./AVI/avimod.o:
	cd AVI; make;

# delete all object files
clean:
	rm -f *.o AVI/*.o heartwall
