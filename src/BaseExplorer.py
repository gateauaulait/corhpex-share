import os
import numpy as np
import re
from functools import reduce
import operator
import itertools
from .space_iterators import MultiSpaceExplorer, BenchAppIter
from .utils import exec_cmd
import glob
import pandas as pd
from abc import ABC, abstractmethod

stat_fn = dict()
stat_fn["med"] = np.median
stat_fn["mean"] = np.mean


class BaseExplorer(ABC):

    def __init__(self, aggregator, configuration, prune=None):
        """
        Initialize the exploration by reading the configuration file

        Args:
            configuration (Configuration): the path the configuration file
            prune (fn): a pruning function that returns True if the configuration should be pruned and False other wise
        """

        self.config = configuration
        self.aggregator = aggregator

        self._custom_env = os.environ.copy()


        self.entry_points = {
            "pre_bench": {
                "explo": ["compileflags", "envvars"],
                "hook": [self._compile, self._set_envvars],
            },
            "pre_exec": {
                "explo": ["execflags", "envcmd"],
                "hook": [lambda *args: None, self._exec_envcmd],
            }
        }

        # the pruning function does nothing by default
        # it is the user's responsability to provide a pruning function
        if prune == None:
            self.prune = lambda c : False
        else:
            self.prune = prune

        # set time_dir variant_names for all applications in all benchmarks
        self._root_exec_dir = os.getcwd()
        for b in self.config.benchmarks:
            for a in b["apps"]:
                a["time_dir"] = self.config.res_dir + "/" + b["id"] + "/" + a["id"];
                exec_cmd("mkdir -p " + b["root_dir"] + "/" + a["root_dir"])
                exec_cmd("mkdir -p " + a["time_dir"])
                if a.get("variant_names") == None:
                    a["variant_names"] = ["default"]


    def _get_pinning(self, nb_threads, physical=False):
        """
        Create the list of HWthreads to use given

        Args:
            nb_threads (int): The number of OMP threads
            physical (bool): True if physical indices should be used false otherwise (logical indices)

        Returns:
            str: A comma separated list of PU index
        """
        pkg_f = self._custom_env.get("SPX_PKG_FIRST", 1)
        die_f = self._custom_env.get("SPX_DIE_FIRST", 1)
        l3_f = self._custom_env.get("SPX_L3_FIRST", 1)
        smt_f = self._custom_env.get("SPX_SMT_FIRST", 1)

        p = "-p " if (physical) else ""

        dir_path = os.path.dirname(__file__)
        l = exec_cmd(dir_path + "/../thread-binding-generator/bindings-gen " + p + str(pkg_f) + " " + str(die_f) + " " + str(l3_f) + " " + str(smt_f))
        print(nb_threads)
        print(l)

        l = l.split(" ")
        s = ""
        for i in range(nb_threads):
            s += l[i] + ","
        return s.rstrip(",")


    def _instrument_cmd(self, cmd, config):
        """
        Instrument a command and execute it to measure metrics

        Args:
            cmd (str): The command to instrument
            config (dict): The current configuration
            i (int): The id of the execution
        """

        # get thread binding policy
        nb_threads = int(self._custom_env.get("OMP_NUM_THREADS", 1))

        # execution to measure perf counters
        if self.config.measure["perfcounters"].is_some():
            bindings = self._get_pinning(nb_threads)
            perfcounters = self.config.measure["perfcounters"].unwrap()
            # For now we onlysupport likwid
            # This is NOT extensible
            # Use a compact (everything first) thread binding policy by default
            # if the number of threads is not set use one thread by default
            prefix = "likwid-perfctr -C " + bindings
            if perfcounters["use_api"]:
                prefix += " -m"

            for i in range(self.config.meta_rep):
                for g in perfcounters["groups"]:
                    group = " -M " + str(perfcounters["mode"]) + " -o likwid_" + g + "_" + str(i) + ".csv -g " + g + " "
                    instr_cmd = prefix + group + cmd
                    exec_cmd(instr_cmd, self._custom_env)

    # Cleanup measure files
    def _handle_measures(self, a, v, id_str):
        """
        Cleanup measure files

        Args:
            a (dict): The application
            v (int): The index of the variant
            id_str (str): The configuration identifier string
        """
        # Move the likwid files to the correct location with an appropiate name that reflects the configuration
        if self.config.measure["perfcounters"].is_some():
            perfcounters = self.config.measure["perfcounters"].unwrap()
            for i in range(self.config.meta_rep):
                for g in perfcounters["groups"]:
                    filename = "likwid_" + g + "_" + str(i) + "_" + a["id"] + "_" + a["variant_names"][v] + "_" + id_str + ".csv"
                    exec_cmd("mv likwid_" + g + "_" + str(i) + ".csv " + a["time_dir"] + "/" + filename)

    def _evaluate(self, config, ba):
        """
        Evaluate the application for each input variant

        Args:
            config (dict[str, dict]): The configuration to use
            ba (dict[str, dict]): The benchmark info and application to execute
        """

        a = ba["a"]

        # Build the id string
        id_str = self.config.get_conf(config)

        # dump the config id
        with open(self.config.res_dir + "/configs.txt", 'a+') as f:
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
            if not self.config.force and os.path.exists(a["time_dir"] + "/likwid_" + a["id"] + "_" + a["variant_names"][i] + "_" + id_str):
                continue

            # Execute the variant for the number of meta_rep and dump the output in the file times
            cmd = cmd_base.replace("<variants>", v)
            self._instrument_cmd(cmd, config)
            # Move mesure to their correct location
            self._handle_measures(a, i, id_str)

    def _compile(self, config, changes):
        """
        Compile the benchmark

        Args:
            config (dict[str, dict]): The configuration to use
            changes list[bool]: Indicate which compile flags have changed since last compilation
        """

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
                exec_cmd(cmd, self._custom_env)
            for a in b["apps"]:
                saved_cwd.append(os.getcwd())
                # Go to the application's directory (if there is one)
                os.chdir(a["root_dir"])
                # compile if there is a compile command for the application
                if "compile_cmd" in a:
                    cmd = a["compile_cmd"].replace("<compile_flags>", flags_str)
                    exec_cmd(cmd, self._custom_env)

                # Go back to the benchmark directory for the next app
                print(saved_cwd[-1])
                os.chdir(saved_cwd.pop())

            # Go back to the user's current working directory for the next benchmark
            print(saved_cwd[-1])
            os.chdir(saved_cwd.pop())

    def _set_envvars(self, config, changes):
        """
        Set environnement variables

        Args:
            config (dict[str, dict]): The configuration to use
            changes list[bool]: Indicate which compile flags have changed since last compilation
        """
        for i,(k,v) in enumerate(config["envvars"].items()):
            if changes[i]:
                self._custom_env |= {k: str(v)}

    def _exec_envcmd(self, config, changes):
        """
        Set environnement parameters through commands

        Args:
            config (dict[str, dict]): The configuration to use
            changes list[bool]: Indicate which compile flags have changed since last compilation
        """
        for i,(k,v) in enumerate(config["envcmd"].items()):
            if changes[i]:
                exec_cmd(k + " " + str(v), self._custom_env)

    def _reset_envcmd(self):
        """
        Reset environnement parameters through commands
        """
        for cmd in self.config.space["envcmd"]:
            exec_cmd(cmd["name"] + " " + str(cmd["reset"]), self._custom_env)


    # Run the space exploration for all applications
    @abstractmethod
    def run(self):
        pass
