CC = $(CCC) $(MODE) -lstdc++ -lm
SRC = pathfinder.cpp
EXE = pathfinder
FLAGS = -fopenmp

all: release

release.o: $(SRC)
	$(CC) $(SRC) $(FLAGS) -c -o release.o

release: release.o
	$(CC) release.o $(FLAGS) -o $(EXE)

debug:
	$(CC) $(SRC) -g -Wall -o $(EXE)

clean:
	rm -f pathfinder *.o *.ll


