from .BaseAggregator import BaseAggregator
import re
import numpy as np
import os
import sys
import logging
logger = logging.getLogger("corhpex." + __name__)

stat_fn = dict()
stat_fn["med"] = np.median
stat_fn["mean"] = np.mean

class SimpleAggregator(BaseAggregator):
    """
    Aggregator to combine multiple aggregators

    Attributes:
        config (Configuration): the exploration configuration
        _store (dict of ()): Dictionnary to store metrics already read, inner aggregators should use the same
        aggregators: a list of aggregators
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    ### To update to support more advanced values
    def read_score(self, file_name):
        with open(file_name) as file_in:
            r = []
            for line in file_in:
                r.append(float(line.split(";")[1]))
        return sum(r)

    # key function to collect simple values 
    def get_app_config_metric_stat(self, b, a, config):
        """
        todo: to improve & comment
        """
        id_str = self.config.get_conf(config)
        assert (len (a["variants"]) == 1)
        assert self.config.meta_rep == 1
        res = []              
        filename_var_exec_time = a["time_dir"] + "/" + "profile_simple" + "_" + a["id"] + "_" + a["variant_names"][0] + "_" + id_str + ".csv"
        filename_var_energy = a["time_dir"] + "/" + "profile_simple_energy" + "_" + a["id"] + "_" + a["variant_names"][0] + "_" + id_str + ".csv"
        value = {}
        value["goal"] = []
        value["goal"].append(self.read_score(filename_var_exec_time))
        value["goal"].append(self.read_score(filename_var_energy))
        # quick fix to work with the other aggregators
        # value["goal"].append(self.read_score(filename_var_exec_time))        
        res.append(value)
        return res

    def get_app_config_metric(self, b, a, config):
        return self.get_app_config_metric_stat(b, a, config)     

    def app_config_was_evaluated(self, b, a, config):
        """
        wip
        """
        return False

    def write_stats_to_csv(self, metric_id):
        """
        Write the statistics of a metric to a CSV file

        Args:
            metric_id (str): the identifier of the metric
        """
        for k,fn_id in enumerate(self.config.res_stats):
            res_id = 0
            with open(self.config.res_dir +'/' + metric_id + '_' + fn_id +'.csv', "w") as outputFile:

                storage = dict()
                headers = []
                for e,v in self._store.items():
                    if e[0] in storage:
                        storage[e[0]].append(stat_fn[fn_id](v[metric_id]))
                    else:
                        storage[e[0]] = []
                    if e[1] not in headers:
                        headers.append(e[1])

                # Write headers
                outputFile.write("apps")
                for h in headers:
                    outputFile.write("," + h)
                outputFile.write("\n")

                # Write values
                for a,v in storage.items():
                    outputFile.write(a)
                    for e in v:
                        outputFile.write(",{:.3f}".format(e))

    def get_metrics_ids(self):
        """
        Return:
            A list of strings that are metric ids
        """
        return [ m["id"] for m in self.config.metrics["simple"]]
