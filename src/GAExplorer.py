from .BaseExplorer import BaseExplorer
from .space_iterators import MultiSpaceExplorer, BenchAppIter
from .utils import exec_cmd
import os
import random
import subprocess
import numpy as np
from pyeasyga import pyeasyga
import sys


class GAExplorer(BaseExplorer):

    def __init__(self, *args, **kwargs):
        # See BaseExplorer.__init__()
        super().__init__(*args, **kwargs)

        # necessary to reset compiler settings
        self.dir_pre_bench_hook = ""
        
        # separator used to construct id for configurations
        # feel free to improve this part
        self.sep = "::"

        # these arrays enable defining a configuration from a vector of configuration
        # size_parameters parameterizes the size of the search space
        # size_parameters is useful for GA or RL to create initial population or set possible mutations / state changes
        # name_paramters serves to construct a configuration from a vector
        self.size_parameters = []
        self.name_paramters = []
        
        # used by the GA to call the evaluation on a target ba
        self.bench = ""

        # Set default GA parameteres if none are provided in the config
        if self.config.algo_params == {}:
            self.config.algo_params = {"pop":300, "gen": 45, "cross": 0.9, "mut":0.1, "target": "rdtsc"}

        # Check the configuration to fail early
        if len(self.config.benchmarks) != 1 or len(self.config.benchmarks[0]["apps"]) != 1 or len(self.config.benchmarks[0]["apps"][0]["variants"]) != 1:
            sys.exit("The GA only supports executing a single application with a single variant.")

    def _mutate(self, individual):
        """
        Mutate and individual by picking a random valid value for a random index

        Args:
            individual (list[int]): The individual to mutate
        """
        mutate_index = random.randrange(len(individual))
        individual[mutate_index] = random.randrange(self.size_parameters[mutate_index])

    def _get_score(self, ba, vector):
        """
        Get the score (i.e. any group of counters) of a configuration applied to an app

        Args:
            ba (dict[str, dict]): The benchmark info and application
            vector: The individual (i.e. configuration as an int list) to evaluate

        Returns:
            float: The score of the vector individual
        """
        b = ba["b"]
        a = ba["a"]

        # transforms a vector into a configuration that can be parsed and executed
        config = self._vec2conf(vector)

        # prune invalid configurations
        # return a score of 0 for invalid configurations
        if self.prune(config, "pre_exec"):
            print("Prunned configuration - this is unexpected")
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
        # uses the custom jpdc implementation
        measures = self.aggregator.get_app_config_metric_stat(b, a, config)[0]

        # since all values are the same, we should get consistent results even if we collect energy
        # higher is better score, thus normalization
        measure_id = self.config.algo_params["target"]
        fn_id = self.config.res_stats.index(self.config.algo_params["target_stat"])

        score = float(measures[measure_id][fn_id])
        if score > 0:
            score = 1/score

        # full metrics for recording
        measures = self.aggregator.get_app_config_metric(b, a, config)[0]

        with open(self.config.res_dir +'/ga_explo_' + measure_id + '_' + self.config.algo_params["target_stat"] +'.csv', 'a') as f:
            line = "GA: " + str(vector) + " " + id_str + " " + str(score) + " " + str(measures)
            f.write(line + '\n')
            print("measure:", line)

        return score

    def _vec2conf(self, vector):
        """
        Convert a individual (vector) into a CORHPEX configuration

        This transformation is a bijection: there is a 1-1 association between vectors and CORHPEX configurations

        Args:
            vector (list[int]): The individual vector

        Returns:
            dict[str, dict]: The CORHPEX configuration associated to the vector
        """
        assert len(vector) == len(self.name_paramters)
        
        conf = {
            "compileflags": dict(),
            "execflags": dict(),
            "envvars": dict(),
            "envcmd": dict()
        }
        for n,param_name in enumerate(self.name_paramters):
            k = param_name.split(self.sep)[0]
            val = param_name.split(self.sep)[1]
            # k - execflags, compileflags, envvars, envcmd
            # val - name of the parameter eg OMP_NUM_THREADS or SPX_HT            
            if k not in conf.keys():
                conf[k] = {}
            
            # get value using vector with k / val in search space
            # list containing dict. One of them contains val as value under the key name
            param_value = self.config.space[k]
            
            for i in param_value:
                if i["name"] == val:
                    assert(val not in conf[k].keys())                                     
                    # 2 scenarios: either values as a key or not
                    # if yes, we just return the values id as index in i["value"]
                    if "values" in i.keys():
                        conf[k][val] = i["values"][vector[n]]
                    # otherwise we change true fale depending on values id
                    else:
                        false_true = [True,False]
                        conf[k][val] = false_true[vector[n]]
        return(conf)

    def _parametrize_space(self):
        """
        Compute the arrays `space_size` and `space_desc`

        Each dimension of `space_size` describes the size of the dimension of each parameter in the space
        Each dimension of `space_desc` describes the parameter the associated dimension of `space_size`
        """
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
                self.name_paramters.append(name_param)

        print("GA:", "space size:", self.size_parameters)
        print("GA:", "space description:", self.name_paramters)
        assert(len(self.size_parameters) == len(self.name_paramters))

    def _generate_random_vectors(self):
        """
        Generate random vectors respecting the search space size

        Returns:
            list[int]: A random vector individual
        """
        r = []
        for n,v in enumerate(self.size_parameters):
            r.append(random.randint(0, v - 1))       
        
        return r

    def _create_individual(self, data):
        """
        Generate random individual

        Returns:
            list[int]: A random vector individual
        """
        return self._generate_random_vectors()

    def _explore(self):
        """
        Run the GA exploration
        """

        # Set to ensure consistent/deterministic executions
        seed_value = 0
        os.environ['PYTHONHASHSEED']=str(seed_value)
        np.random.seed(seed_value)
        random.seed(seed_value)

        # pre_bench env directory to be used when applying compiler settings
        self.dir_pre_bench_hook = os.getcwd()
        # self.dir_pre_bench_hook = self._root_exec_dir
        
        # enable to transform vectors to configurations
        self._parametrize_space()
        
        self._generate_random_vectors()

        for ba in BenchAppIter(self.config.benchmarks):
            self.bench = ba
            ga = pyeasyga.GeneticAlgorithm([],
                                   population_size=self.config.algo_params["pop"],
                                   generations=self.config.algo_params["gen"],
                                   crossover_probability=self.config.algo_params["cross"],
                                   mutation_probability=self.config.algo_params["mut"],
                                   #elitism=True,
                                   maximise_fitness=True)

            ga.create_individual = self._create_individual
            ga.fitness_function = lambda vector, data: self._get_score(self.bench, vector)
            ga.mutate_function = self._mutate
            ga.run()
            print (ga.best_individual())

        # Dump statistics to CSV
        perfcounters = self.config.metrics
        for m in self.aggregator.get_metrics_ids():
            self.aggregator.write_stats_to_csv(m)


    def run(self, ga_params={}):
        """
        Run an exploration with given parameters if any

        Args:
            ga_params (optional dict[str, any]): parameter override to run the GA
        """
        if ga_params != {}:
            self.config.algo_params = ga_params
        self._explore()
