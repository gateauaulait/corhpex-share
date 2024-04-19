import tomli
import os
import numpy as np
import re
from functools import reduce
import operator
import itertools
from option import Option, Some, Nothing
from space_iterators import MultiSpaceExplorer, BenchAppIter
from utils import exec_cmd
import glob
import pandas as pd

stat_fn = dict()
stat_fn["med"] = np.median
stat_fn["mean"] = np.mean

class Configuration:
    def __init__(self, config_file, force=False, res_dir=None):
        with open(config_file, "rb") as f:
            config = tomli.load(f)
            self.benchmarks = config["benchmarks"]
            self.meta_rep = config["meta_rep"]
            self.res_stats = config["stat_fn"]
            self.space = config["exploration-space"]
            # directory to hold measurement
            self.res_dir = config.get("res_dir", "res_dir/")
            if res_dir != None:
                self.res_dir = res_dir
            self.force = force
            print(self.res_dir)

            # set up what is mesured and how
            self.measure = dict()
            if config.get("measure"):
                # Always assume time in mesured in-app and printed on stdout
                self.measure["time"] = {"method": "in-app", "output": "stdout"}
                if config["measure"].get("perfcounters"):
                    self.measure["perfcounters"] = Option.of(config["measure"]["perfcounters"])
                else:
                    self.measure["perfcounters"] = Option.empty()
            else:
                # If the mesure section is absent assume only time is mesured
                # in-app and printed on stdout
                self.measure["time"] = {"method": "in-app", "output": "stdout"}
                self.measure["perfcounters"] = Option.empty()

        # ensures all subspaces are declared
        self.space.setdefault("compileflags", dict())
        self.space.setdefault("execflags", dict())
        self.space.setdefault("envvars", dict())
        self.space.setdefault("envcmd", dict())

    # TODO rename into get_id
    # Returns an id string for the configuration
    # param config: the configuration to use, a dictionary of dictionaries
    # param ba: useless (only here for consistency)
    def get_conf(self, config, ba=None):
        id_str = ""
        pattern = re.compile('[\W_]+')
        for sub, desc in config.items():
            for i,(k,v) in enumerate(desc.items()):
                if self.space[sub][i]["values"] == [True, False]:
                    if v:
                        id_str = id_str + "_" + pattern.sub('', k)
                elif "id" in self.space[sub][i]:
                    id_str = id_str + "_" + self.space[sub][i]["id"] + str(v)
                else:
                    id_str = id_str + "_" + pattern.sub('', str(v))

        return id_str.lstrip("_")


class Explorer:

    # Initialize the exploration by reading the configuration file
    # param config_file: the path the configuration file
    # param prune: a pruning function that returns True if the configuration should be pruned and False other wise
    def __init__(self, config_file, prune=None, force=False, res_dir=None):
        # with open(config_file, "rb") as f:
        #     config = tomli.load(f)
        #     self.benchmarks = config["benchmarks"]
        #     self.meta_rep = config["meta_rep"]
        #     self.res_stats = config["stat_fn"]
        #     self.space = config["exploration-space"]
        #     # directory to hold measurement
        #     self.res_dir = config.get("res_dir", "res_dir/")
        #     if res_dir != None:
        #         self.res_dir = res_dir
        #     self.force = force
        #     print(self.res_dir)

        #     # set up what is mesured and how
        #     self.measure = dict()
        #     if config.get("measure"):
        #         # Always assume time in mesured in-app and printed on stdout
        #         self.measure["time"] = {"method": "in-app", "output": "stdout"}
        #         if config["measure"].get("perfcounters"):
        #             self.measure["perfcounters"] = Option.of(config["measure"]["perfcounters"])
        #         else:
        #             self.measure["perfcounters"] = Option.empty()
        #     else:
        #         # If the mesure section is absent assume only time is mesured
        #         # in-app and printed on stdout
        #         self.measure["time"] = {"method": "in-app", "output": "stdout"}
        #         self.measure["perfcounters"] = Option.empty()

        self.config = Configuration(config_file)

        self.__custom_env = os.environ.copy()

        # # ensures all subspaces are declared
        # self.space.setdefault("compileflags", dict())
        # self.space.setdefault("execflags", dict())
        # self.space.setdefault("envvars", dict())
        # self.space.setdefault("envcmd", dict())

        self.entry_points = {
            "pre_bench": {
                "explo": ["compileflags", "envvars"],
                "hook": [self.__compile, self.__set_envvars],
            },
            "pre_exec": {
                "explo": ["execflags", "envcmd"],
                "hook": [lambda *args: None, self.__exec_envcmd],
            }
        }

        # the pruning function does nothing by default
        # it is the user's responsability to provide a pruning function
        if prune == None:
            self.prune = lambda c : False
        else:
            self.prune = prune

        # Build the thread-binding generator if needed
        exec_cmd("cd thread-binding-generator; make; cd -")

        # set time_dir variant_names for all applications in all benchmarks
        self.__root_exec_dir = os.getcwd()
        for b in self.config.benchmarks:
            for a in b["apps"]:
                a["time_dir"] =  self.__root_exec_dir + "/" + self.config.res_dir + "/" + b["id"] + "/" + a["id"];
                exec_cmd("mkdir -p " + b["root_dir"] + "/" + a["root_dir"])
                exec_cmd("mkdir -p " + a["time_dir"])
                if a.get("variant_names") == None:
                    a["variant_names"] = ["default"]


    # Create the list of HWthreads to use given
    # @param nb_threads: the number of OMP threads
    # @param physical: true if physical indices should be used false otherwise (logical indices)
    # @return string of comma separated PU index
    def __get_pinning(self, nb_threads, physical=False):
        pkg_f = self.__custom_env.get("SPX_PKG_FIRST", 1)
        die_f = self.__custom_env.get("SPX_DIE_FIRST", 1)
        l3_f = self.__custom_env.get("SPX_L3_FIRST", 1)
        smt_f = self.__custom_env.get("SPX_SMT_FIRST", 1)

        p = "-p " if (physical) else ""

        l = exec_cmd(self.__root_exec_dir + "/thread-binding-generator/bindings-gen " + p + str(pkg_f) + " " + str(die_f) + " " + str(l3_f) + " " + str(smt_f))

        l = l.split(" ")
        s = ""
        for i in range(nb_threads):
            s += l[i] + ","
        return s.rstrip(",")


    # Instrument a command to measure metrics
    # @param cmd: the command to instrument
    # @param config: the current configuration
    # @param i: the id of the execution
    def __instrument_cmd(self, cmd, config, i):
        # get thread binding policy
        nb_threads = int(self.__custom_env.get("OMP_NUM_THREADS", 1))
        bindings = self.__get_pinning(nb_threads, True)

        # execution to mesure time
        instr_cmd = cmd
        if self.config.measure["time"]["output"] == "stdout":
            suffix = " >> times"
            instr_cmd += suffix
        prefix = "GOMP_CPU_AFFINITY="
        instr_cmd = prefix + bindings + " " + instr_cmd
        exec_cmd(instr_cmd, self.__custom_env)

        # execution to measure perf counters
        if self.config.measure["perfcounters"].is_some():
            bindings = self.__get_pinning(nb_threads)
            perfcounters = self.config.measure["perfcounters"].unwrap()
            # For now we onlysupport likwid
            # This is NOT extensible
            # Use a compact (everything first) thread binding policy by default
            # if the number of threads is not set use one thread by default
            prefix = "likwid-perfctr -C " + bindings
            if perfcounters["use_api"]:
                prefix += " -m"

            for g in perfcounters["groups"]:
                group = " -o likwid_" + g + "_" + str(i) + ".csv -g " + g + " "
                instr_cmd = prefix + group + cmd
                exec_cmd(instr_cmd, self.__custom_env)

    # Cleanup measure files
    def __handle_measures(self, a, v, id_str):
        # Same as above this is not extensible
        # Move the times file to the correct location with an appropiate name that reflects the configuration
        filename = "times_" + a["id"] + "_" + a["variant_names"][v] + "_" + id_str
        exec_cmd("mv times " + a["time_dir"] + "/" + filename)

        # Move the likwid files to the correct location with an appropiate name that reflects the configuration
        if self.config.measure["perfcounters"].is_some():
            perfcounters = self.config.measure["perfcounters"].unwrap()
            for i in range(self.config.meta_rep):
                for g in perfcounters["groups"]:
                    filename = "likwid_" + g + "_" + str(i) + "_" + a["id"] + "_" + a["variant_names"][v] + "_" + id_str + ".csv"
                    exec_cmd("mv likwid_" + g + "_" + str(i) + ".csv " + a["time_dir"] + "/" + filename)

    # Evaluate the application for each input variant
    # @param config: the configuration to use, a dictionary of dictionaries
    # @param ba: the benchmark info and application to execute
    def __evaluate(self, config, ba):
        a = ba["a"]

        # Build the id string
        id_str = self.config.get_conf(config)

        # dump the config id
        with open(self.__root_exec_dir + "/" + self.config.res_dir + "/configs.txt", 'a+') as f:
            f.write(id_str + "\n")

        # Build the flag string
        flags_str = ""
        for k,v in config["execflags"].items():
            flags_str = flags_str + k + "=" + v + " "

        # Build the command
        cmd_base = "./" + a["exec_cmd"]
        # Replace the exec_flags placeholder with the flag string
        cmd_base = cmd_base.replace("<exec_flags>", flags_str)
        # For each variant replace the variant placeholder with the variant string
        for i,v in enumerate(a["variants"]):
            # Skip the execution if the results are already present and force is off
            if not self.config.force and os.path.exists(a["time_dir"] + "/times_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str):
                continue

            # Execute the variant for the number of meta_rep and dump the output in the file times
            cmd = cmd_base.replace("<variants>", v)
            for k in range(self.config.meta_rep):
                self.__instrument_cmd(cmd, config, k)
            # Move mesure to their correct location
            self.__handle_measures(a, i, id_str)

    # Returns an id string for the configuration
    # param config: the configuration to use, a dictionary of dictionaries
    # param ba: useless (only here for consistency)
    # def __get_conf(self, config, ba=None):
    #     id_str = ""
    #     pattern = re.compile('[\W_]+')
    #     for sub, desc in config.items():
    #         for i,(k,v) in enumerate(desc.items()):
    #             if self.config.space[sub][i]["values"] == [True, False]:
    #                 if v:
    #                     id_str = id_str + "_" + pattern.sub('', k)
    #             elif "id" in self.config.space[sub][i]:
    #                 id_str = id_str + "_" + self.config.space[sub][i]["id"] + str(v)
    #             else:
    #                 id_str = id_str + "_" + pattern.sub('', str(v))

    #     return id_str.lstrip("_")

    # Compile the benchmark
    # param config: the configuration to use, a dictionary of dictionaries
    # param changes: an array of bool telling which compile flags have changed since last compilation
    def __compile(self, config, changes):
        if not reduce(operator.or_, changes, False) and config["compileflags"]:
            return
        saved_cwd = []
        # Build the flag string
        flags_str = ""
        for k,v in config["compileflags"].items():
            if v:
                flags_str = flags_str + k + " "

        for b in self.config.benchmarks:
            saved_cwd.append(os.getcwd())
            # Move to root directory of the benchmark
            os.chdir(b["root_dir"])
            # compile if there is a global compile command for the benchmark
            if "compile_cmd" in b:
                # Replace the compile_flags placeholder with the flag string
                cmd = b["compile_cmd"].replace("<compile_flags>", flags_str)
                exec_cmd(cmd, self.__custom_env)
            for a in b["apps"]:
                saved_cwd.append(os.getcwd())
                # Go to the application's directory (if there is one)
                os.chdir(a["root_dir"])
                # compile if there is a compile command for the application
                if "compile_cmd" in a:
                    cmd = a["compile_cmd"].replace("<compile_flags>", flags_str)
                    exec_cmd(cmd, self.__custom_env)

                # Go back to the benchmark directory for the next app
                os.chdir(saved_cwd.pop())

            # Go back to the user's current working directory for the next benchmark
            os.chdir(saved_cwd.pop())

    def __set_envvars(self, config, changes):
        for i,(k,v) in enumerate(config["envvars"].items()):
            if changes[i]:
                self.__custom_env |= {k: str(v)}

    def __exec_envcmd(self, config, changes):
        for i,(k,v) in enumerate(config["envcmd"].items()):
            if changes[i]:
                exec_cmd(k + " " + str(v), self.__custom_env)

    def __reset_envcmd(self):
        for cmd in self.config.space["envcmd"]:
            exec_cmd(cmd["name"] + " " + str(cmd["reset"]), self.__custom_env)

    # Explore the optimization space
    # param action_func: the action to execute for each config an each app
    # param bench_iter: a function that returns an iterator
    # param apply_config: functions to apply the configuration are executed only if it is true
    def __explore(self, action_func, bench_iter, apply_config=True):
        results = {}
        # Explore a subspace before iterating over the benchmarks and applications
        mse_pre_bench = MultiSpaceExplorer(self.config.space, self.entry_points["pre_bench"]["explo"])
        for config_pre_bench, changes_pre_bench in mse_pre_bench:
            if self.prune(config_pre_bench, "pre_bench"):
                continue
            if apply_config:
                for i,h in enumerate(self.entry_points["pre_bench"]["hook"]):
                    h(config_pre_bench, changes_pre_bench[i])

            # Iterate over benchmarks and applications OR execute once (depends on the iterator returned)
            for ba in bench_iter():
                # If execute once then ba is None
                # Add keys to results appropriately
                if ba != None:
                    results.setdefault(ba["b"]["id"]+"_"+ba["a"]["id"], [])
                else:
                    results.setdefault("ba", [])

                # Explore a subspace before executing the application
                mse_pre_exec = MultiSpaceExplorer(self.config.space, self.entry_points["pre_exec"]["explo"], config_pre_bench)
                for config, changes in mse_pre_exec:
                    if self.prune(config_pre_bench, "pre_exec"):
                        continue
                    if apply_config:
                        for i,h in enumerate(self.entry_points["pre_exec"]["hook"]):
                            h(config_pre_bench, changes[i])

                    r = action_func(config, ba)
                    if r != None:
                        if ba != None:
                            results[ba["b"]["id"]+"_"+ba["a"]["id"]] += [r]
                        else:
                            results["ba"] += [r]

        # Clean up environment
        if apply_config:
            self.__reset_envcmd()

        return results

    # Run the space exploration for all applications
    def run(self):
        self.__explore(self.__evaluate, lambda : BenchAppIter(self.config.benchmarks))

    def __get_times_from_file(self, filename):
        values = []
        with open(filename, "rb") as f:
            for l in f:
                values.append(float(l.rstrip()))
        return values

    # Evaluate the application for each input variant
    # param config: the configuration to use, a dictionary of dictionaries
    # param ba: the benchmark info and application to execute
    def __get_time_data(self, config, ba):
        a = ba["a"]
        id_str = self.config.get_conf(config)

        filename_base = "times_" + a["id"] + "_"

        res = []
        for i,v in enumerate(a["variants"]):
            filename = filename_base + a["variant_names"][i] + "_" + id_str
            res.append([])
            for k,fn_id in enumerate(self.config.res_stats):
                values = self.__get_times_from_file(a["time_dir"] + "/" + filename)
                res[i].append(stat_fn[fn_id](values))
        return res

    # Return the value of the desired field in a given file
    def __get_counter_from_file(self, filename, section, field, col):
        value = 0
        pattern_section = re.compile("(" + section +").*")
        in_section = False
        with open(filename, "r") as f:
            for l in f:
                if in_section:
                    fields = l.split(",")
                    if field == fields[0]:
                        value = float(fields[col])
                        break;
                else:
                    if pattern_section.search(l):
                        in_section = True

        return value


    # Return the statistics for a paire of application and configuration
    def __get_likwid_data(self, config, ba):
        a = ba["a"]
        id_str = self.config.get_conf(config)
        perfcounters = self.config.measure["perfcounters"].unwrap()

        res = dict()
        for m in perfcounters["metrics"]:
            res_tmp = []
            for i,v in enumerate(a["variants"]):
                filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str
                values = []
                res_tmp.append([])
                for k in range(self.config.meta_rep):
                    filename = "likwid_" + m["groups"][0] + "_" + str(k) + filename_var + ".csv"
                    values.append(self.__get_counter_from_file(a["time_dir"] + "/" + filename, m["section"], m["fields"][0], m["cols"][0]))
                for f,fn_id in enumerate(self.config.res_stats):
                    res_tmp[i].append(stat_fn[fn_id](values))
            res[m["id"]] = res_tmp

        return res




    # Write data to CSV
    # param mesure_id: the identifier of the metric
    # param res: the dict of results to write in CSV
    # param headers: column headers to write at the top of the file
    def __write_to_csv(self, measure_id, res, headers):
        # Write to CSV files
        for k,fn_id in enumerate(self.config.res_stats):
            res_id = 0
            outputFile = open(self.config.res_dir +'/' + measure_id + '_' + fn_id +'.csv', "w")
            # Write headers
            outputFile.write("apps")
            for h in headers:
                outputFile.write(";" + h)
            outputFile.write("\n")

            # Write data by app and variants
            for b in self.config.benchmarks:
                for i,a in enumerate(b["apps"]):
                    nb_variants = len(a["variants"])
                    for v in range(nb_variants):
                        outputFile.write(b["id"] + "_" + a["id"] + "_" +a["variant_names"][v])
                        for e in res[b["id"] + "_" + a["id"]]:
                            outputFile.write(";{:.3f}".format(e[v][k]))
                        outputFile.write("\n")
                    res_id += 1
            outputFile.close()

    def __get_likwid_data_(self, config_id, b, a, perfcounters):
        res = dict()
        for m in perfcounters["metrics"]:
            res_tmp = []
            for i,v in enumerate(a["variants"]):
                filename_var = "_" + a["id"] + "_" + a["variant_names"][i] + "_" + config_id
                values = []
                res_tmp.append([])
                for k in range(self.config.meta_rep):
                    filepath = a["time_dir"] + "/" + "likwid_" + m["groups"][0] + "_" + str(k) + filename_var + ".csv"
                    if os.path.exists(filepath):
                        values.append(self.__get_counter_from_file(filepath, m["section"], m["fields"][0], m["cols"][0]))
                    if values == []:
                        valuse = [np.nan]
                for f,fn_id in enumerate(self.config.res_stats):
                    res_tmp[i].append(stat_fn[fn_id](values))
            res[m["id"]] = res_tmp

        return res

    # Aggregate data in CSV files
    def data_agreggation(self):
        # Get headers (config string identifier)
        headers = self.__explore(self.config.get_conf, lambda: [None], False)["ba"]
        headers_ = []
        with open(self.config.res_dir + "configs.txt") as f:
            lines = [line.rstrip('\n') for line in f]
            headers_ = list(set(lines))

        print(headers_)
        print(self.config.measure["perfcounters"].unwrap())

        nb_configs = len(headers)

        if self.config.measure["perfcounters"].is_some():
            perfcounters = self.config.measure["perfcounters"].unwrap()
            prefix = ""
            if perfcounters["method"] == "likwid":
                for b in self.config.benchmarks:
                    for a in b["apps"]:
                        for c in headers_:
                            print(self.__get_likwid_data_(c, b, a, perfcounters))



        # Get time data
        times = self.__explore(self.__get_time_data, lambda: BenchAppIter(self.config.benchmarks), False)
        self.__write_to_csv("time", times, headers)
        # Get counters data
        counters = dict()
        if self.config.measure["perfcounters"].is_some():
            perfcounters = self.config.measure["perfcounters"].unwrap()
            # Get counters statistics over meta-rep
            counters = self.__explore(self.__get_likwid_data, lambda: BenchAppIter(self.config.benchmarks), False)
            # Reorganize the dictionary
            counters = {k:{k1:[i1[k2] for i1 in l for k2 in i1 if k1 == k2] for i in l for k1 in i} for k,l in counters.items()}
            counters = {k2:{k3: counters[k3][k4] for k3 in counters for k4 in counters[k3] if k2 == k4} for k in counters for k2 in counters[k]}
            # Dump metrics to CSV
            for m in perfcounters["metrics"]:
                self.__write_to_csv(m["id"], counters[m["id"]], headers)
