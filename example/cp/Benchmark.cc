#include <fstream>
#include <iostream>
#include <sstream>
#include <stddef.h>
#include <time.h>
#include <vector>

#include "Benchmark.h"
#include <CapillaryPressureLaw.h>

// =====================================================

#ifdef LIKWID_PERFMON
#include <likwid-marker.h>
#else
#define LIKWID_MARKER_INIT
#define LIKWID_MARKER_THREADINIT
#define LIKWID_MARKER_SWITCH
#define LIKWID_MARKER_REGISTER(regionTag)
#define LIKWID_MARKER_START(regionTag)
#define LIKWID_MARKER_STOP(regionTag)
#define LIKWID_MARKER_CLOSE
#define LIKWID_MARKER_GET(regionTag, nevents, events, time, count)
#endif

// =====================================================

template <typename FpStore, typename FpComp>
int Benchmark<FpStore, FpComp>::eval(std::string input_dir) {

  auto cells = Cells(problemSize);

  std::vector<FpStore> A(problemSize);
  std::vector<FpStore> B(problemSize);
  std::vector<FpStore> C(problemSize);

  std::cout << "Loading data ...";
  // Fill the data structure with values from file
  std::stringstream filename;
  filename << input_dir << "/A.txt";
  std::ifstream file(filename.str());
  if (!file.is_open()) {
    std::cerr << "file " << filename.str() << " does not exist" << std::endl;
  }

  for (std::size_t i = 0; i < problemSize; i++) {
    file >> A[i];
  }
  std::cout << " DONE" << std::endl;

  // Create and parametrize kernel
  CapillaryPressureLaw<FpStore, FpComp> kernel;

  LIKWID_MARKER_INIT;
  LIKWID_MARKER_THREADINIT;
  LIKWID_MARKER_REGISTER("Compute");

  std::cout << "Execute Capillary Pressure kernel ...";
  std::flush(std::cout);

  // Execute kernel and record execution time
  struct timespec begin, end;
  LIKWID_MARKER_START("Compute");
#pragma omp parallel
  {
    for (std::size_t k = 0; k < n; k++) {
#pragma omp for simd
      for (std::size_t i = 0; i < problemSize; i++) {
        kernel.eval((FpComp)A[i], B[i], C[i]);
      }
    }
  }
  LIKWID_MARKER_STOP("Compute");

  LIKWID_MARKER_CLOSE;

  std::cout << " DONE" << std::endl;

  return 0;
}
