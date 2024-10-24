# Examples

This directory contains examples of usage of the CORHPEX framework.

## Structure

We encourage users use this stucture when performing experiments with CORHPEX.

The `configs` directory contains all the configuration files for DSE examples.
The `corhpex` directory is a symlink to the parent directory to enable using the library as `corhpex` in python scripts. In an external repository, this would be a submodule until CORHPEX is released as a python library.
The `main.py` is a minimal working script to launch a DSE experiment with CORHPEX. We encourage users to start with this file.
The source code of benchmarks and applications is kept in dedicated directories such as `cp`.

## CP

The CP experiment aims to optimize the number of threads and the thread binding policy for the Capillary Pressure computation kernel on a Zen 1 (Naples) architecture with 2 CPUs and 16 cores per CPUs.

On a system with `likwid` and all the python dependencies installed, you can launch the experiment with:

``` sh
./main.py -f configs/cp.toml
```

This will produce a `exp-cp` directory with csv files for each pair of metric and statistic such as `rdtsc_med.csv`.

The plotting script relies on `pandas` and `seaborn`. You can then produce a plot with:

``` sh
./cp-plot.py
```

