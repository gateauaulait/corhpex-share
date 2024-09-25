from .BaseAggregator import BaseAggregator
import re
import numpy as np
import os

stat_fn = dict()
stat_fn["med"] = np.median
stat_fn["mean"] = np.mean


class LikwidAggregator(BaseAggregator):
    """
    Aggregator for Likwid data in CSV format

    Attributes:
        config (Configuration): the exploration configuration
        _store (dict of ()): Dictionnary to store metrics already read
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_counter_from_file(self, filename, section, field, col):
        """
        Return the value of the desired field in a given file

        If several fields and columns are specifed, they are summed

        Attributes:
            filename (str): the name of the file
            section (str): the section of file to target

        Returns:
            float: The value for the desired app with a configuration
        """
        value = 0
        pattern_section = re.compile("(" + section +").*")
        with open(filename, "r") as f:
            in_section = False
            # for each line of the file
            for l in f:
                # if we are in the section
                if in_section:
                    # split the columns
                    fields = l.split(",")
                    # for each field
                    for i,fld in enumerate(field):
                        if fields[0] == "TABLE":
                            in_section= False
                        # if the first column is the current field
                        if fld == fields[0]:
                            # add the value of the field and move on to the next field
                            if fields[col[i]].isprintable():
                                value += float(fields[col[i]])
                else:
                    if pattern_section.search(l):
                        in_section = True

        return value

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
        id_str = self.config.get_conf(config)
        perfcounters = self.config.measure["perfcounters"].unwrap()

        res = []
        for i,v in enumerate(a["variants"]):
            filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str
            entry_id = self._entry_id(b["id"], a["id"] + "_" + a["variant_names"][i], id_str)
            res_tmp = dict()

            # If the application-variant-config metrics where never stored do it
            if entry_id not in self._store:
                self.__store_app_config_metric(b, a, config)

            # Get the statistics for each metric
            for m in perfcounters["metrics"]:
                values = self._store[entry_id][m["id"]]
                res_tmp[m["id"]] = [stat_fn[fn_id](values) for fn_id in self.config.res_stats]

            res.append(res_tmp)

        return res

    def get_app_config_metric(self, b, a, config):
        """
        Return the lists of metric metarepetitions for a pair of application and configuration

        Args:
            b (dict): the benchmark description
            a (dict): the application description
            config (dict): the configuration (design) to execute
        """
        id_str = self.config.get_conf(config)
        perfcounters = self.config.measure["perfcounters"].unwrap()

        res = []
        for i,v in enumerate(a["variants"]):
            filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str
            entry_id = self._entry_id(b["id"], a["id"] + "_" + a["variant_names"][i], id_str)
            res_tmp = dict()

            # If the application-variant-config metrics where never stored do it
            if entry_id not in self._store:
                self.__store_app_config_metric(b, a, config)

            # Get the values for each metric
            for m in perfcounters["metrics"]:
                res_tmp[m["id"]] = self._store[entry_id][m["id"]]

            res.append(res_tmp)

        return res

    def __store_app_config_metric(self, b, a, config):
        """
        Read metrics values and store them in _store

        Args:
            b (dict): the benchmark description
            a (dict): the application description
            config (dict): the configuration (design) to execute
        """
        id_str = self.config.get_conf(config)
        perfcounters = self.config.measure["perfcounters"].unwrap()

        res = []
        for i,v in enumerate(a["variants"]):
            filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str
            entry_id = self._entry_id(b["id"], a["id"] + "_" + a["variant_names"][i], id_str)
            res_tmp = dict()

            self._store[entry_id] = dict()
            for m in perfcounters["metrics"]:
                values = []
                res_tmp[m["id"]] = []
                for k in range(self.config.meta_rep):
                    filename = "likwid_" + m["groups"][0] + "_" + str(k) + filename_var + ".csv"
                    values.append(self._get_counter_from_file(a["time_dir"] + "/" + filename, m["section"], m["fields"], m["cols"]))

                self._store[entry_id][m["id"]] = values

    def app_config_was_evaluated(self, b, a, config):
        """
        Return True only if the configuration was evaluated

        Args:
            b (dict): the benchmark description
            a (dict): the application description
            config (dict): the configuration (design) to execute
        """
        id_str = self.config.get_conf(config)
        perfcounters = self.config.measure["perfcounters"].unwrap()

        for i,v in enumerate(a["variants"]):
            filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str
            entry_id = self._entry_id(b["id"], a["id"] + "_" + a["variant_names"][i], id_str)

            # If the application-variant-config metrics where never stored do it
            for m in perfcounters["metrics"]:
                if entry_id not in self._store:
                    for k in range(self.config.meta_rep):
                        filename = "likwid_" + m["groups"][0] + "_" + str(k) + filename_var + ".csv"
                        if not os.path.isfile(a["time_dir"] + "/" + filename):
                            return False

        return True

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
