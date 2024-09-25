import re
import numpy as np
import os
from abc import ABC, abstractmethod

stat_fn = dict()
stat_fn["med"] = np.median
stat_fn["mean"] = np.mean


class BaseAggregator(ABC):
    """
    Base class for Aggregators

    All aggregators should inherit this class.

    Attributes:
        config (Configuration): The exploration configuration
        _store (dict[(app_id, config_id), dict[metric_id, list[values]]]): Dictionnary to store metrics already read
    """

    def __init__(self, configuration):
        """
        Args:
            config_file (str): The configuration file path
        """
        self.config = configuration

        # store all values we attempt to aggregate
        # keys: (app_id, config_id)
        # value: a dict where keys are metric id and values are a list of metrics
        self._store = dict()

    def _entry_id(self, b, a, c):
        return (b + "_" + a, c)

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def app_config_was_evaluated(self, b, a, config):
        """
        Return True only if the configuration was evaluated

        Args:
            b (dict): the benchmark description
            a (dict): the application description
            config (dict): the configuration (design) to execute
        """
        pass

    @abstractmethod
    def write_stats_to_csv(self, metric_id):
        """
        Write the statistics of a metric to a CSV file

        Args:
            metric_id (str): the identifier of the metric
        """
        pass

    @abstractmethod
    def get_metrics_ids(self):
        """
        Return:
            A list of strings that are metric ids
        """
        pass
