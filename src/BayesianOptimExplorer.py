from .BaseExplorer import BaseExplorer
from .space_iterators import MultiSpaceExplorer, BenchAppIter
from .utils import exec_cmd
import os
import random
import subprocess
import numpy as np
from bayes_opt import BayesianOptimization
from bayes_opt import UtilityFunction
import sys
import smt.surrogate_models as smtsm
import pickle


class BayesianOptimExplorer(BaseExplorer):

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
        # name_parameters serves to construct a configuration from a vector
        self.size_parameters = []
        self.name_parameters = []
        
        # used by the GA to call the evaluation on a target ba
        self.bench = ""

        # Set default BO parameteres if none are provided in the config
        if self.config.algo_params == {}:
            self.config.algo_params = {
                "init_points": 10,
                "n_iter":100,
                "target": "rdtsc",
                "target_stat": "med",
                "seed_value": 0
            }


        # Default surrogate model id (corrected right before exploration)
        self.sm_id = "GPR_matern52"

        # Check the configuration to fail early
        if len(self.config.benchmarks) != 1 or len(self.config.benchmarks[0]["apps"]) != 1 or len(self.config.benchmarks[0]["apps"][0]["variants"]) != 1:
            sys.exit("The BO only supports executing a single application with a single variant.")


    def _get_score(self, ba, **flat_config):
        """
        Get the score (i.e. any group of counters) of a configuration applied to an app

        Args:
            ba (dict[str, dict]): The benchmark info and application
            flat_config (dict): The configuration to evaluate  in a flat format

        Returns:
            float: The score of the configuration
        """
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
        
        with open(self.config.res_dir +'/bo_explo_' + self.sm_id + "_" + measure_id + '_' + self.config.algo_params["target_stat"] +'.csv', 'a') as f:
            line = "BO " + str([round(v) for v in flat_config.values()]) + " " + id_str + " " + str(score) + " " + str(measures)
            f.write(line + '\n')
            print("measure:", line)

        return score

    def _flat2conf(self, flat_config):
        """
        Convert a flat configuration into a CORHPEX configuration

        This transformation is a bijection: there is a 1-1 association between vectors and CORHPEX configurations

        Args:
            flat_config (dict): The flat format configuration

        Returns:
            dict[str, dict]: The CORHPEX configuration associated to the vector
        """
        assert len(flat_config) == len(self.name_parameters)
        
        conf = {
            "compileflags": dict(),
            "execflags": dict(),
            "envvars": dict(),
            "envcmd": dict()
        }

        for key,value_idx in flat_config.items():
            subspace = key.split(self.sep)[0]
            dim = key.split(self.sep)[1]
            # subspace - execflags, compileflags, envvars, envcmd
            # dim - dimension: name of the parameter eg OMP_NUM_THREADS or SPX_HT

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
                self.name_parameters.append(name_param)

        print("BO", "space size:", self.size_parameters)
        print("BO", "space description:", self.name_parameters)
        assert(len(self.size_parameters) == len(self.name_parameters))

    def _explore_BO(self, ba):
        """
        Run the BO exploration for the given application

        Args:
            ba (dict[str, dict]): The benchmark info and the application
        """

        space = dict(zip(self.name_parameters, [(0, s-1) for s in self.size_parameters]))

        bo = BayesianOptimization(
            f=lambda **x: self._get_score(ba, **x),
            pbounds=space,
            verbose=0,
            random_state=self.config.algo_params["seed_value"],
        )

        params = self.config.algo_params

        # Change the gaussian process model for an SMT model if it is specified in the configuration
        # In any case update the model id to refect the model used and its parameters
        if "gp" in self.config.algo_params.keys():
            bo._gp = SMTAdapter(params["gp"]["model"], **params["gp"]["params"])
            self.sm_id = params["gp"]["model"]
            for k,v in params["gp"]["params"].items():
                p = str(v)
                p = p.strip("[]").replace(",", "")
                self.sm_id = self.sm_id + "_" + k + str(v)
        else:
            if "alpha" in params:
                bo.set_gp_params(alpha=params["alpha"])
                self.sm_id = self.sm_id + "_alpha" + str(params["alpha"])

        # Run the BO
        if "acquisition_func" in params:
            acquisition_function = UtilityFunction(**params["acquisition_func"])
            bo.maximize(init_points=params["init_points"], n_iter=params["n_iter"], acquisition_function=acquisition_function)
        else:
            bo.maximize(init_points=params["init_points"], n_iter=params["n_iter"])

        # If the save option is on save the model with pickle
        if self.config.algo_params.get("save", False):
            filename = ba["b"]["id"] + "_" + ba["a"]["id"] + "_" + self.sm_id + ".pkl"
            with open(filename, "wb") as f:
                pickle.dump(bo._gp, f)


    def _explore(self):
        """
        Run the BO
        """
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

        for ba in BenchAppIter(self.config.benchmarks):
            self._explore_BO(ba)

        # Dump statistics to CSV
        perfcounters = self.config.measure["perfcounters"].unwrap()
        for m in perfcounters["metrics"]:
            self.aggregator.write_stats_to_csv(m["id"])

        return
        
    def run(self, bo_params={}):
        """
        Run an exploration with given parameters if any

        Args:
            bo_params (optional dict[str, any]): parameter override to run the BO
        """
        if bo_params != {}:
            self.config.algo_params = bo_params
        self._explore()


class SMTAdapter():
    """
    Wrapper class for gaussian process surrogate models for the Surrogate Model Toolbox (SMT) to use in BayesianOptimization
    Mimics the scikitlearn interface

    Attributes:
        surrogate_model: the model object from SMT
        X_train_: features for training
        y_train_: labels for training
    """

    def __init__(self, model, **kwargs):
        """
        Initialize the wrapper by creating a model and setting default inner values

        Args:
            model: the name of the SMT model (cf. SMT docs)
            **kwargs: arguments for the SMT model creation (cf. SMT docs)
        """

        self.surrogate_model = None

        if model == "KRG":
            kwargs.setdefault("corr", "matern52")
            self.surrogate_model = smtsm.KRG(**kwargs)
        elif model == "KPLS":
            self.surrogate_model = smtsm.KPLS(**kwargs)
        elif model == "KPLSK":
            self.surrogate_model = smtsm.KPLSK(**kwargs)
        elif model == "GPX":
            self.surrogate_model = smtsm.GPX(**kwargs)
        elif model == "GEKPLS":
            self.surrogate_model = smtsm.GEKPLS(**kwargs)
        elif model == "MGP":
            self.surrogate_model = smtsm.MGP(**kwargs)
        elif model == "SGP":
            self.surrogate_model = smtsm.SGP(**kwargs)
        else:
            print("Unknown GP, use default Kriging with Matern 5/2")
            kwargs.setdefault("corr", "matern52")
            self.surrogate_model = smtsm.KRG(**kwargs)

        self.X_train_ = None
        self.y_train_ = None

    def fit(self, X,Y):
        """
        Fit (ie. train) the model with given features and labels

        Args:
            X: the features for the training
            Y: the labels for the training
        """

        self.surrogate_model.set_training_values(X, Y)
        self.X_train_ = self.surrogate_model.training_points[None][0][0]
        self.y_train_ = self.surrogate_model.training_points[None][0][1]
        self.surrogate_model.train()

    def predict(self, X, return_std=False):
        """
        Predict the label for a given set of features using the SMT model previously trained

        Args:
            X: the features to predict
            return_std (optional bool): whether the standard deviation should be returned

        Returns:
            The predicted label and if `return_std` was true the standard deviation (the 2 as a pair)
        """
        y = self.surrogate_model.predict_values(X)
        if return_std:
            if self.surrogate_model.supports["variances"]:
                dy = self.surrogate_model.predict_variances(X)
            else:
                dy = np.ones_like(y)
            return y, np.sqrt(dy)

        return y

    def set_params(self, **params):
        """
        Set the model parameters after the creationg of the wrapper

        Args:
            **params (dict): the parameters and their values
        """
        for (k,v) in params.items():
            self.surrogate_model.options[k] = v
