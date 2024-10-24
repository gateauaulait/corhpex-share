#include <cstring>
#include <functional>
#include <getopt.h>
#include <iostream>
#include <map>
#include <stddef.h>
#include <vector>

#include "types.h"

#include "Benchmark.h"

// =====================================================

// Vector length in bytes
#if defined(__AVX2__)
#define VLEN 32
#elif defined(__SSE2__)
#define VLEN 16
#endif

#ifndef VLEN
#define VLEN 8
#endif

// =====================================================

std::map<const ConfigId, BenchmarkBase *> benchMapCreator() {
  std::map<const ConfigId, BenchmarkBase *> benchs;

  benchs.insert(std::pair<ConfigId, BenchmarkBase *>(
      ConfigId(FPType::Float, FPType::Float), new Benchmark<float, float>()));
  benchs.insert(std::pair<ConfigId, BenchmarkBase *>(
      ConfigId(FPType::Float, FPType::Double), new Benchmark<float, double>()));
  benchs.insert(std::pair<ConfigId, BenchmarkBase *>(
      ConfigId(FPType::Double, FPType::Double),
      new Benchmark<double, double>()));

  return benchs;
}

// =====================================================

std::map<const ConfigId, BenchmarkBase *> const Benchs = benchMapCreator();
int main(int argc, char *argv[]) {
  static struct option long_options[] = {{"fpstore", required_argument, 0, 's'},
                                         {"fpcomp", required_argument, 0, 'c'},
                                         {"kernel", required_argument, 0, 'l'},
                                         {"iter", required_argument, 0, 'i'},
                                         {"size", required_argument, 0, 'p'},
                                         {"help", no_argument, 0, 'h'},
                                         {"verbose", no_argument, 0, 0},
                                         {0, 0, 0, 0}};

  int c;
  int option_index = 0;
  ConfigId config = {FPType::Float, FPType::Float};
  long unsigned int problemSize = 10000000;
  int n = 10;

  while ((c = getopt_long(argc, argv, "scldiph", long_options,
                          &option_index)) != -1) {
    switch (c) {
    case 's': {
      if (strcmp(optarg, "float") == 0) {
      } else if (strcmp(optarg, "double") == 0) {
        std::get<0>(config) = FPType::Double;
      } else {
        std::cerr << "Type must be 'float' or 'double' default is float"
                  << std::endl;
        return 1;
      }
      break;
    }
    case 'c': {
      if (strcmp(optarg, "float") == 0) {
      } else if (strcmp(optarg, "double") == 0) {
        std::get<1>(config) = FPType::Double;
      } else {
        std::cerr << "Type must be 'float' or 'double' default is float"
                  << std::endl;
        return 1;
      }
      break;
    }
    case 'i': {
      n = std::stoi(optarg);
      break;
    }
    case 'p': {
      problemSize = std::stoi(optarg);
      break;
    }
    case 'h': {
      std::cout << "USAGE : bench [options] input_dir_path" << std::endl;
      std::cout << "Options:" << std::endl;
      std::cout << "--fpcomp=<precision>    precision of the computation "
                   "'float' or 'double' (default is 'float')"
                << std::endl;
      std::cout << "--fpstore=<precision>   precision of the stored values "
                   "'float' or 'double' (default is 'float')"
                << std::endl;
      std::cout
          << "--iter=<n>              execute <n> iterations(default is 10)"
          << std::endl;
      std::cout
          << "--size=<n>              problem size is <n>(default is 10000000)"
          << std::endl;
      break;
    }
    default: {
    }
    }
  }

  // Input directory is not an optarg argument and it is mendatory
  // Any argument after the input directory path will be ignored
  std::string input_dir;
  if (optind >= argc) {
    std::cerr << "Missing input directory path" << std::endl;
    return 1;
  }

  input_dir = argv[optind++];

  BenchmarkBase *b = Benchs.at(config);
  b->setIter(n);
  b->setProblemSize(problemSize);
  b->eval(input_dir);

  return 0;
}
