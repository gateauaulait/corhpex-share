/*
 * Benchmark.h
 */

#ifndef BENCHMARK_H_
#define BENCHMARK_H_

#include "types.h"

// =====================================================

class BenchmarkBase {
protected:
  long unsigned int problemSize = 10000000;
  int n = 10;

public:
  virtual ~BenchmarkBase() = default;
  virtual int eval(std::string input_dir) = 0;
  void setIter(int iter) { n = iter; }
  void setProblemSize(int size) { problemSize = size; }
};

// =====================================================

template <typename FpStore, typename FpComp>
class Benchmark : public BenchmarkBase {
private:
  struct Cells {
    std::vector<FpStore> A;
    std::vector<FpStore> B;
    std::vector<FpStore> C;
    std::vector<std::vector<FpStore>> A_v;
    Cells(long unsigned int N) : A(N), B(N), C(N), A_v(N) {}
  };

public:
  ~Benchmark() = default;
  int eval(std::string input_dir);
};

// Do NOT remove theses comments
// They are used by an outside script to automatically add template class
// definition
/* __TEMPLATE_CLASS_START__ */
template class Benchmark<float, float>;
template class Benchmark<float, double>;
template class Benchmark<double, double>;

/* __TEMPLATE_CLASS_END__ */

#endif /* BENCHMARK_H_ */
