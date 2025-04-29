# CORHPEX

COmpiler, Runtime and Hardware Parameter EXplorer (CORHPEX), is a framework to explore performance optimization spaces for any application.

## Apache License Version 2.0

This is a work in progress code to be eventually merged within the main version of CORHPEX which can be accessed at:
https://gitlab.inria.fr/corhpex/corhpex

Copyright 2025, developed by IFPEN and Inria within the context of their Joint Laboratory.

## Requirements

You need a python3.11+ environnement with the following modules :
- tomli
- numpy
- pyeasyga
- bayesian-optimization
- ply
- smt

We also need likwid to access time and performance counters and the user needs the appropriate permissions to the MSR. For more informations on how to setup likwid please see the official documentation.

## Exploration configuration

The exploration of the parameter space is handled by an explorer.
It relies on a TOML configuration file that describes the benchmarks and applications to execute as well as the parameter space.

At the top of the configuration file you can specify the number of metarepetion, the statistic function to use to aggregate data and optionally the name of the directory where the measures will be stored. For now only the mean and the median (med) are available. When data are aggregated one file will be generated per function and per measure.

``` toml
meta_rep = 11
stat_fn = ["med"]
#timing_dir = "output-dir-path"
```

### Benchmarks and applications

A benchmark is declared as follow :
``` toml
[[benchmarks]]
name = "My benchmark"
id = "my-b"
root_dir = "my-bench"
compile_cmd = "..."
```

The compile command should end in the same directory it started (the root directory of the benchmark).

After the benchmark is declared, we can declare all the applications it contains like this :

``` toml
[[benchmarks.apps]]
name = "App1"
id = "app1"
root_dir = "app1"
exec_cmd = "app1 <exec_flags> <variants>"
variants = ["..."]
variant_names = ["rand"]
```

The root directory is the directory where the executatble is located.
The execution command can contain 2 placeholders :
- `<exec_flags>` will be replaced by the execution flags of the exploration space
- `<variants>` will be replaced by each variants listed for the application. It can be used to run the benchmark with different inputs for example. The multiple variants must be named and will be considered as different execution not as a different configurations.
For now, having variants is mendatory even if there is only one, even if it is empty (and has no name).

You need to declare all the applications of a benchmark before delaring the next benchmark (proceed in the exact same way)

### Exploration space

After the benchmarks you can describe the exploration space. For now only execution flags that take a value can be explored :
``` toml
[exploration-space]
```

This first line indicates the start of the description of the exploration space.

Then we declare each execution flag with a block like this :
``` toml
[[exploration-space.execflags]]
name = "--flag"
values = ["val1", "val2"]
```

During the exploration each flag will take each possible value listed.

For compiler flags :
``` toml
[[exploration-space.compileflags]]
name = "-O3"
```

In both cases, flags without values will be toggled on or off.

For environment variables :
``` toml
[[exploration-space.envvars]]
name = "OMP_NUM_THREADS"
id = "th"
values = [1, 2]
```

The id is used as a short hand to name the configuration.

For commands that change the environment :
``` toml
[[exploration-space.envcmd]]
name = "sudo /usr/sbin/wrmsr -a 0x1A4 "
id = "prefetch"
values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
reset = 0
```
The name is the command, the id is required (to be used in the configurations'names) and an additional reset value must be specified.
At the end of the exploration the command will use the reset value which should result in a friendly environment fo the next user.

### Measures

You can add the mesure of perfcounters with likwid as follow :

``` toml
[measure]
[measure.perfcounters]
method = "likwid"
groups = ["ENERGY"]
use_api = true

[[measure.perfcounters.metrics]]
name = "Energy"
id = "ener"
section = "TABLE,Region Compute,Group 1 Metric"
groups = ["ENERGY"]
fields = ["Energy PKG [J]"]
cols = [1]
```

First, you declare the perfcounters to retrieve, here we use likwid (only method supported), we specify the group of counters to mesure and if we should use the likwid api (to monitor only a part of the code with markers, the binary must be compiled with likwid).

Then, you specify the metrics you are interested in, give each of them a name, an id (for short hand), the section of the likwid CSV file where the result is located, the group of the metric (the group must be measured so it must appear in the group list above.), the field of the metric and the column of the value in the CSV file.

### Space exploration pruning

You can manually prune the exploration space by providing a pruning function to the explorer constructor as a second argument.

``` python
explorer = ExhaustiveExplorer(config_file_path, custom_pruning_func)
explorer.run()
```


## Exploration strategies

### Bayesian Optimization exploration

Bayesian Optimization is a technique to find the maximum of a black-box function. It is often used to tune hyperparameters of machine learning algorithms.

It works by selecting the best next point to explore in the black-box function using an acquisition function. Depending on the acquisition function and its parameters, the search for the maximum can be aggressive (exploitation) or more exploratory (exploration). Thus, this exploration stategy is suitable for both maximizing the black-box function and exploring its behaviour on the space. Under the hood, a surrogate model is trained and the acquisition function determins the next point that will reduce the uncertainty and thus improve the accuracy of the surrogate model.

For example, the acquisition function can choose the next query point as the one which has the highest **probability of improvement** over the current maximum of the black-box function. For this **PI** acquisition a high value for the `xi` parameter (e.g. 0.3, 3) favors exploration while a low value (e.g. 0.075) favors exploitation. The **expected improvement** (**EI**) acquisition function is similar but takes into account how much improvement will result.  The `xi` parameter follows the same dynamics.

This exploration strategy can be parametrized in the configuration file:

``` toml
[algo_params]
init_points=10                      # number of random points to start with
n_iter=10                           # number of iterations (i.e. number of points on top of the random one at the start)
alpha=0.0001                        # tune the gaussian process regressor, use higher values for decrete parameters
aquisition_func.kind = "ei"         # or "ucb" or 'poi'
aquisition_func.xi = 3              # or kappa for ucb
target = "rdtsc"                    # target metric to optimize
target_stat = "med"                 # statistic of the metric to optimize
seed_value = 0                      # seed value for anything random in the algorithm
```


## Adding an exploration strategy

You can add an exploration strategy or algorithm by making a new class that inherits from `BaseExplorer`.

Here is a template for new empty explorer :

``` python
from BaseExplorer import BaseExplorer

class AwsomeExplorer(BaseExplorer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # Run the exploration
    def run(self):
        pass
```

You can implement the exploration in the `run` function and add any auxilary function you need to the class.
An explorer can access the following member variables:
- `config` which contains a `Configuration` object with all the informations about the space and the benchmarks and applications
- `_custom_env` a copy of the environnement the explorer was started id
- `entry_points` a dictionnary of 2 entry points ("pre-bench" and "pre-exec") that contains the list of sub-spaces explored ("explo") and the hook functions to apply the parameters of thoses spaces ("hook").
- `prune` the pruning function

