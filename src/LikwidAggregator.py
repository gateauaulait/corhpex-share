from Configuration import Configuration
import re
import numpy as np
import os

stat_fn = dict()
stat_fn["med"] = np.median
stat_fn["mean"] = np.mean


class LikwidAggregator:

    def __init__(self, config_file):
        self.config = Configuration(config_file)

        # store all values we attempt to aggregate
        # keys: (app_id, config_id)
        # value: a dict where keys are metric id and values are a list of metrics
        self.__store = dict()

    def __entry_id(self, b, a, c):
        return (b + "_" + a, c)

    # Return the value of the desired field in a given file
    def _get_counter_from_file(self, filename, section, field, col):
        value = 0
        pattern_section = re.compile("(" + section +").*")
        with open(filename, "r") as f:
            for i,fld in enumerate(field):
                in_section = False
                for l in f:
                    if in_section:
                        fields = l.split(",")
                        if fld == fields[0]:
                            value += float(fields[col[i]])
                            break;
                    else:
                        if pattern_section.search(l):
                            in_section = True

        return value

    # Return the statistics for a pair of application and configuration
    def get_app_config_metric_stat(self, b, a, config):
        id_str = self.config.get_conf(config)
        perfcounters = self.config.measure["perfcounters"].unwrap()

        res = []
        for i,v in enumerate(a["variants"]):
            filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str
            entry_id = self.__entry_id(b["id"], a["id"] + "_" + a["variant_names"][i], id_str)
            res_tmp = dict()

            # If the application-variant-config metrics where never stored do it
            if entry_id not in self.__store:
                self.store_app_config_metric(b, a, config)

            # Get the statistics for each metric
            for m in perfcounters["metrics"]:
                values = self.__store[entry_id][m["id"]]
                res_tmp[m["id"]] = [stat_fn[fn_id](values) for fn_id in self.config.res_stats]

            res.append(res_tmp)

        return res

    def get_app_config_metric(self, b, a, config):
        id_str = self.config.get_conf(config)
        perfcounters = self.config.measure["perfcounters"].unwrap()

        res = []
        for i,v in enumerate(a["variants"]):
            filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str
            entry_id = self.__entry_id(b["id"], a["id"] + "_" + a["variant_names"][i], id_str)
            res_tmp = dict()

            # If the application-variant-config metrics where never stored do it
            if entry_id not in self.__store:
                self.store_app_config_metric(b, a, config)

            # Get the statistics for each metric
            for m in perfcounters["metrics"]:
                values = self.__store[entry_id][m["id"]]
                res_tmp[m["id"]] = values

            res.append(res_tmp)

        return res

    def store_app_config_metric(self, b, a, config):
        id_str = self.config.get_conf(config)
        perfcounters = self.config.measure["perfcounters"].unwrap()

        res = []
        for i,v in enumerate(a["variants"]):
            filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str
            entry_id = self.__entry_id(b["id"], a["id"] + "_" + a["variant_names"][i], id_str)
            res_tmp = dict()

            self.__store[entry_id] = dict()
            for m in perfcounters["metrics"]:
                values = []
                res_tmp[m["id"]] = []
                for k in range(self.config.meta_rep):
                    filename = "likwid_" + m["groups"][0] + "_" + str(k) + filename_var + ".csv"
                    values.append(self._get_counter_from_file(a["time_dir"] + "/" + filename, m["section"], m["fields"], m["cols"]))

                self.__store[entry_id][m["id"]] = values

    def app_config_was_evaluated(self, b, a, config):
        id_str = self.config.get_conf(config)
        perfcounters = self.config.measure["perfcounters"].unwrap()

        for i,v in enumerate(a["variants"]):
            filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str
            entry_id = self.__entry_id(b["id"], a["id"] + "_" + a["variant_names"][i], id_str)

            # If the application-variant-config metrics where never stored do it
            for m in perfcounters["metrics"]:
                if entry_id not in self.__store:
                    for k in range(self.config.meta_rep):
                        filename = "likwid_" + m["groups"][0] + "_" + str(k) + filename_var + ".csv"
                        if not os.path.isfile(a["time_dir"] + "/" + filename):
                            return False

        return True


    # Write data to CSV
    # param metric_id: the identifier of the metric
    # param res: the dict of results to write in CSV
    # param headers: column headers to write at the top of the file
    def write_stats_to_csv(self, metric_id):
        # Write to CSV files
        for k,fn_id in enumerate(self.config.res_stats):
            res_id = 0
            outputFile = open(self.config.res_dir +'/' + metric_id + '_' + fn_id +'.csv', "w")

            storage = dict()
            headers = []
            for e,v in self.__store.items():
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

            for a,v in storage.items():
                outputFile.write(a)
                for e in v:
                    outputFile.write(",{:.3f}".format(e))

            outputFile.close()
