from .BaseAggregator import BaseAggregator
import re
import numpy as np
import os

stat_fn = dict()
stat_fn["med"] = np.median
stat_fn["mean"] = np.mean


class MetaAggregator(BaseAggregator):
    """
    Aggregator to combine multiple aggregators

    Attributes:
        config (Configuration): the exploration configuration
        _store (dict of ()): Dictionnary to store metrics already read, inner aggregators should use the same
        aggregators: a list of aggregators
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.aggregators = []

    def get_app_config_metric_stat(self, b, a, config):
        """
        Return the statistics for a pair of application and configuration

        Args:
            b (dict): the benchmark description
            a (dict): the application description
            config (dict): the configuration (design) to execute

        Returns:
            A list of dicts containing the lists of statistics labeled by metric.
            In the top level list, an item correspnds to a variant of the application.
            In the last level list, an item corresponds to a statistic ordered as in `stat_fn`
        """
        res = self.aggregators[0].get_app_config_metric_stat(b, a, config)
        for aggreg in self.aggregators[1:]:
            r = aggreg.get_app_config_metric_stat(b, a, config)
            for i in range(len(res)):
                res[i] = {**res[i], **r[i]}
        return res

    def get_app_config_metric(self, b, a, config):
        """
        Return the lists of metric metarepetitions for a pair of application and configuration

        Args:
            b (dict): the benchmark description
            a (dict): the application description
            config (dict): the configuration (design) to execute

        Returns:
            A list of one dict containing the target statistic wraped in a one item list for all
            the metrics collected labeled by metric
        """

        res = self.aggregators[0].get_app_config_metric(b, a, config)
        for aggreg in self.aggregators[1:]:
            r = aggreg.get_app_config_metric(b, a, config)
            for i in range(len(res)):
                res[i] = {**res[i], **r[i]}

        return res

    def app_config_was_evaluated(self, b, a, config):
        """
        Return True only if the configuration was evaluated

        Args:
            b (dict): the benchmark description
            a (dict): the application description
            config (dict): the configuration (design) to execute
        """

        evaluated = True
        for aggreg in self.aggregators:
            evaluated = evaluated & aggreg.app_config_was_evaluated(b, a, config)

        return evaluated

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

    def add(self, aggreg):
        aggreg._store = self._store
        self.aggregators.append(aggreg)

    def get_metrics_ids(self):
        """
        Return:
            A list of strings that are metric ids
        """
        ids = []
        for a in self.aggregators:
            ids = ids + a.get_metrics_ids()

        return ids
