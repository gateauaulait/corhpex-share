PREFIX=${PARSECDIR}/pkgs/kernels/streamcluster/inst/${PARSECPLAT}

#TARGET_C = sc_cpu

TARGET_O = sc_omp

ifdef version
  ifeq "$(version)" "parallel"
    CXXFLAGS :=	$(CXXFLAGS) -DENABLE_THREADS -pthread
  endif
endif

all: cpu omp

cpu:
	$(CXX) $(CXXFLAGS) $(LDFLAGS) streamcluster_original.cpp -o $(TARGET_C) $(LIBS) -DENABLE_THREADS -pthread

omp:
	$(CCC) -c $(MODE) -fopenmp -o streamcluster_omp.o streamcluster_omp.cpp 
	$(CCC) $(MODE) -O3 -fopenmp -o $(TARGET_O) streamcluster_omp.o -lstdc++ -lm 


clean:
	rm -f *.o *~ *.txt sc_cpu sc_omp
	
