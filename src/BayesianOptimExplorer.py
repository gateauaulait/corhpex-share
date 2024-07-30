from BaseExplorer import BaseExplorer
from space_iterators import MultiSpaceExplorer, BenchAppIter
from LikwidAggregator import LikwidAggregator
import os
import random
from utils import exec_cmd
import subprocess
import numpy as np
from bayes_opt import BayesianOptimization
from bayes_opt import UtilityFunction
import sys


class BayesianOptimExplorer(BaseExplorer):

    def __init__(self, *args, **kwargs):
        # necessary to reset compiler settings
        self.dir_pre_bench_hook = ""
        
        # separator used to construct id for configurations
        # feel free to improve this part
        self.sep = "::"

        # The GA needs an aggregator to get the mesures on the fly
        self.aggregator = LikwidAggregator(args[0])

        # these arrays enable defining a configuration from a vector of configuration
        # size_parameters parameterizes the size of the search space
        # size_parameters is useful for GA or RL to create initial population or set possible mutations / state changes
        # name_parameters serves to construct a configuration from a vector
        self.size_parameters = []
        self.name_parameters = []
        
        # used by the GA to call the evaluation on a target ba
        self.bench = ""

        # See BaseExplorer.__init__()
        super().__init__(*args, **kwargs)

        # Set default BO parameteres if none are provided in the config
        if self.config.algo_params == {}:
            self.config.algo_params = {
                "init_points": 10,
                "n_iter":100,
                "target": "rdtsc",
                "target_stat": "med",
                "seed_value": 0
            }

        # Check the configuration to fail early
        if len(self.config.benchmarks) != 1 or len(self.config.benchmarks[0]["apps"]) != 1 or len(self.config.benchmarks[0]["apps"][0]["variants"]) != 1:
            sys.exit("The BO only supports executing a single application with a single variant.")


    # Get the score (i.e. any group of counters) of a configuration applied to an app
    # Note that ba is a dictionnary:
    # - the key "b" gives access to the benchmark info
    # - the key "a" gives access to the app info
    def _get_score(self, ba, **flat_config):
        b = ba["b"]
        a = ba["a"]

        # transforms a flat configuration into a configuration that can be parsed and executed
        config = self._flat2conf(flat_config)

        # prune invalid configurations
        # return a score of 0 for invalid configurations
        if self.prune(config, "pre_exec"):
            return 0

        if not self.aggregator.app_config_was_evaluated(b, a, config):
        
            # pre_exec directory when applying the second hook
            # buffered before executing the first hook
            os.chdir(self._root_exec_dir)

            # we also need an array of True of the size of
            # config["envvars"]
            # config["envcmd"]
            # to ensure that we systematically evaluate each point
            # envvars is used by pre_bench while envcmd is used by pre_exec
            envvars_array = [True for _ in range(len(config["envvars"]))]
            envcmd_array = [True for _ in range(len(config["envcmd"]))]
            for i,hook in enumerate(self.entry_points["pre_bench"]["hook"]):
                hook(config, envvars_array)

            os.chdir(b["root_dir"] + "/" + a["root_dir"])
            print("cd " + b["root_dir"] + "/" + a["root_dir"])
            for i,hook in enumerate(self.entry_points["pre_exec"]["hook"]):
                hook(config, envcmd_array)

            self._evaluate(config, ba)
            self._reset_envcmd()


        id_str = self.config.get_conf(config)

        # metric statistics for the score
        measures = self.aggregator.get_app_config_metric_stat(b, a, config)[0]
        measure_id = self.config.algo_params["target"]
        fn_id = self.config.res_stats.index(self.config.algo_params["target_stat"])

        # higher is better score
        score = float(measures[measure_id][fn_id])
        if score > 0:
            score = 1/score

        # full metrics for recording
        measures = self.aggregator.get_app_config_metric(b, a, config)[0]
        
        with open(self.config.res_dir +'/bo_explo_' + measure_id + '_' + self.config.algo_params["target_stat"] +'.csv', 'a') as f:
            line = "BO " + str([round(v) for v in flat_config.values()]) + " " + id_str + " " + str(score) + " " + str(measures)
            f.write(line + '\n')
            print("measure:", line)

        return score

    # take flat configuration and return a configuration with subspaces
    # configuration is a dict of dict
    def _flat2conf(self, flat_config):
        assert len(flat_config) == len(self.name_parameters)
        
        conf = {}
        for key,value_idx in flat_config.items():
            subspace = key.split(self.sep)[0]
            dim = key.split(self.sep)[1]
            # subspace - execflags, compileflags, envvars, envcmd
            # dim - dimension: name of the parameter eg OMP_NUM_THREADS or SPX_HT
            if subspace not in conf.keys():
                conf[subspace] = {}
            
            # get value using vector with k / val in search space
            # list containing dict. One of them contains val as value under the key name
            subspace_dims = self.config.space[subspace]
            
            for d in subspace_dims:
                if d["name"] == dim:
                    assert(dim not in conf[subspace].keys())
                    # 2 scenarios: either values as a key or not
                    # if yes, we just return the values id as index in i["value"]
                    if "values" in d.keys():
                        conf[subspace][dim] = d["values"][round(value_idx)]
                    # otherwise we change true fale depending on values id
                    else:
                        conf[subspace][dim] = bool(round(value_idx))
        return(conf)

    # calculate array space_size and associated space_desc
    # each dimension of space_size describes the size of the dimension of each parameter in the space
    # each dimension of space_desc describes the parameter the associated dimension of space_size
    def _parametrize_space(self):
        # self.config.space 
        # 4 dictionaries: execflags, compileflags, envvars, envcmd
        for k in self.config.space.keys():

            # each dict contains a list of parameters
            # each param is a dict
            for param in self.config.space[k]:
                # the size of the paramter
                size_param = 0
                
                # unique id composed of param nature + its name
                # please feel free to improve the id naming
                name_param = str(k) + self.sep + str(param["name"])
               
                # if values NOT in keys of param, we have 2 options: True or False                
                if "values" not in param.keys():
                    size_param = 2                
                # otherwise values size is the number of possible values of a given parameter
                else:
                    size_param = len(param["values"])
                                
                self.size_parameters.append(size_param)
                self.name_parameters.append(name_param)

        print("BO", "space size:", self.size_parameters)
        print("BO", "space description:", self.name_parameters)
        assert(len(self.size_parameters) == len(self.name_parameters))

    # Utility function to currify the _get_score function with a given ba
    def _get_app_score(self, ba):
        return lambda **x: self._get_score(ba, **x)

    def _explore_BO(self, ba):

        space = dict(zip(self.name_parameters, [(0, s-1) for s in self.size_parameters]))

        bo = BayesianOptimization(
            f=self._get_app_score(ba),
            pbounds=space,
            verbose=0,
            random_state=self.config.algo_params["seed_value"],
        )

        params = self.config.algo_params

        if "alpha" in params:
            bo.set_gp_params(alpha=params["alpha"])

        if "acquisition_func" in params:
            acquisition_function = UtilityFunction(**params["acquisition_func"])
            bo.maximize(init_points=params["init_points"], n_iter=params["n_iter"], acquisition_function=acquisition_function)
        else:
            bo.maximize(init_points=params["init_points"], n_iter=params["n_iter"])

 
    def _explore(self, action_func, bench_iter, apply_config=True):
        # Set to ensure consistent/deterministic executions
        seed_value = self.config.algo_params["seed_value"]
        os.environ['PYTHONHASHSEED']=str(seed_value)
        np.random.seed(seed_value)
        random.seed(seed_value)

        # pre_bench env directory to be used when applying compiler settings
        # Can this be replaced by self._root_exec_dir ? -it works but not sure if correct way
        self.dir_pre_bench_hook = os.getcwd()
        # self.dir_pre_bench_hook = self._root_exec_dir
        
        # enable to transform vectors to configurations
        self._parametrize_space()

        for ba in bench_iter():
            self._explore_BO(ba)

        # Dump statistics to CSV
        perfcounters = self.config.measure["perfcounters"].unwrap()
        for m in perfcounters["metrics"]:
            self.aggregator.write_stats_to_csv(m["id"])

        return
        
    # Test on dahu: python3.9 corhpex/main.py e corhpex/configs/xp-ga.toml
    # Run the exploration
    def run(self, bo_params={}):
        if bo_params != {}:
            self.config.algo_params = bo_params
        self._explore(self._evaluate, lambda : BenchAppIter(self.config.benchmarks))
