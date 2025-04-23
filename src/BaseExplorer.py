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
import subprocess

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
                a["time_dir"] = self.config.res_dir + "/" + b["id"] + "/" + a["id"]
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
        print("number of threads",nb_threads)
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
        if "likwid" in self.config.metrics:
            bindings = self._get_pinning(nb_threads)
            perfcounters = self.config.metrics["likwid"]
            # For now we onlysupport likwid
            # This is NOT extensible
            # Use a compact (everything first) thread binding policy by default
            # if the number of threads is not set use one thread by default
            prefix = "likwid-perfctr -C " + bindings
            if perfcounters["options"]["use_api"]:
                prefix += " -m"

            for i in range(self.config.meta_rep):
                for g in perfcounters["options"]["groups"]:
                    group = " -M " + str(perfcounters["options"]["mode"]) + " -o likwid_" + g + "_" + str(i) + ".csv -g " + g + " "
                    instr_cmd = prefix + group + cmd
                    exec_cmd(instr_cmd, self._custom_env)

        ###
        # Please update without likwid
        # This is a quick fix to enable thread biding
        ###
        if "simple" in self.config.metrics:
            bindings = self._get_pinning(nb_threads)
            prefix = f"KMP_AFFINITY=scatter,granularity=fine,verbose " 
            if any(app["name"] == "streamcluster" for benchmark in self.config.benchmarks for app in benchmark["apps"]):
                cmd = "env OMP_TOOL_LIBRARIES=/home/uartdev/behnaz/corhpex-share-main_original/example/hpc/profile/libinit.so ./sc_omp 10 20 128 1000000 200000 5000 none output.txt"
                instr_cmd = "sudo " + prefix + cmd + " " + str(nb_threads)
                exec_cmd(instr_cmd, self._custom_env)

            elif any(app["name"] == "kmeans" for benchmark in self.config.benchmarks for app in benchmark["apps"]):
                cmd = "env OMP_TOOL_LIBRARIES=/home/uartdev/behnaz/corhpex-share-main_original/example/hpc/profile/libinit.so ./kmeans -n "
                cmd = cmd + str(nb_threads) + " " + "-i ../../../data/kmeans/kdd_cup"
                instr_cmd = "sudo " + prefix + cmd
                exec_cmd(instr_cmd, self._custom_env)

            else:
                instr_cmd = "sudo " + prefix + cmd
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
        if "likwid" in self.config.metrics:
            perfcounters = self.config.metrics["likwid"]
            for i in range(self.config.meta_rep):
                for g in perfcounters["options"]["groups"]:
                    filename = "likwid_" + g + "_" + str(i) + "_" + a["id"] + "_" + a["variant_names"][v] + "_" + id_str + ".csv"
                    exec_cmd("mv likwid_" + g + "_" + str(i) + ".csv " + a["time_dir"] + "/" + filename)

        # Move simple data files
        if "simple" in self.config.metrics:
            filename = "profile_simple" + "_" + a["id"] + "_" + a["variant_names"][v] + "_" + id_str + ".csv"
            exec_cmd("sudo mv profile_simple.csv " + a["time_dir"] + "/" + filename)

            filename = "profile_simple_energy" + "_" + a["id"] + "_" + a["variant_names"][v] + "_" + id_str + ".csv"
            exec_cmd("sudo mv profile_simple_energy.csv " + a["time_dir"] + "/" + filename)

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

    def change_certain_bits(self, start_bit, end_bit, new_value, current_reg_value):
        """ 
        Set the bits between start_bit and end_bit in 'value' to 'new_value'.

        Args:
            current_reg_value: The current value.
            start_bit: The starting bit position (inclusive).
            end_bit: The ending bit position (inclusive).
            new_value : The new value to set in the specified bit range.

        Returns:
            str: The modified value in hex as a string.
        """
        # current_reg_value = int(current_reg_value, 16)  
        # Create a mask for the bit range
        mask = ((1 << (end_bit - start_bit + 1)) - 1) << start_bit

        # Clear the bits in the range
        current_reg_value &= ~mask

        # Align the new value with the target bit range and set the bits
        current_reg_value |= (new_value << start_bit) & mask

        return current_reg_value


    def compute_register_value(self, prefetcher_name, status, current_reg_value, register_name):
        """
        Compute the new register value based on the prefetcher name, status, and current value.

        Args:
            prefetcher_name (str): Name of the prefetcher.
            status (str): Desired status (e.g., ON, OFF).
            current_reg_value (int): Current register value.
            register_name (str): Register name (e.g., 0x1A4, 0x1320).

        Returns:
            int: Updated register value.
        """
        MLC_STREAMER_BIT = 0
        L1_NLP_BIT = 2
        L1_IPP_BIT = 3
        L1_NPP_BIT = 4
        AMP_BIT = 5
        LLC_STREAMER_BIT = 43
        L2_NLP_BIT = 40

        if prefetcher_name == "MLC_LLC_STREAMER":
            if status == "000000":  #ON
                current_reg_value = current_reg_value & ~(1 << MLC_STREAMER_BIT)
            else:  # OFF
                current_reg_value = current_reg_value | (1 << MLC_STREAMER_BIT)
            
        elif prefetcher_name == "L1_NLP":
            if status == "000000":  #ON
                current_reg_value = current_reg_value & ~(1 << L1_NLP_BIT)
            else:  # OFF
                current_reg_value = current_reg_value | (1 << L1_NLP_BIT)
        
        elif prefetcher_name == "L1_IPP":
            if status == "000000":  #ON
                # print("status5: ", status)
                current_reg_value = current_reg_value & ~(1 << L1_IPP_BIT)
            else:  # OFF
                current_reg_value = current_reg_value | (1 << L1_IPP_BIT)
        
        elif prefetcher_name == "L1_NPP":
            if status == "000000":  #ON
                current_reg_value = current_reg_value & ~(1 << L1_NPP_BIT)
            else:  # OFF
                current_reg_value = current_reg_value | (1 << L1_NPP_BIT)
        
        elif prefetcher_name == "AMP":
            if status == "000000":  #ON
                current_reg_value = current_reg_value & ~(1 << AMP_BIT)
            else:  # OFF
                current_reg_value = current_reg_value | (1 << AMP_BIT)
        
        elif prefetcher_name == "LLC_STREAMER": 
            if status == "OFF":  #OFF
                if register_name == '0x1320':
                    current_reg_value = current_reg_value | (1 << LLC_STREAMER_BIT)
                else:
                    return current_reg_value
            else:
                if register_name == "0x1320":
                # ON-MD-XQ-DD-DDO
                    MD = int (status.split("-")[1])
                    XQ = int (status.split("-")[2])
                    current_reg_value = current_reg_value & ~(1 << LLC_STREAMER_BIT)
                    current_reg_value = self.change_certain_bits(37, 42, MD, current_reg_value)   # Set the max distance
                    current_reg_value = self.change_certain_bits(58, 62, XQ, current_reg_value)   # Set the XQ
                elif register_name == "0x1322":
                    DD = int (status.split("-")[3])
                    DDO = int (status.split("-")[4])
                    current_reg_value = self.change_certain_bits(14, 22, DD, current_reg_value)     #set the demand density
                    current_reg_value = self.change_certain_bits(23, 26, DDO, current_reg_value)    #set the demand density override

        elif prefetcher_name == "MLC_STREAMER":  
            if status == "OFF": #OFF
                if register_name == '0x1320':
                    current_reg_value = current_reg_value | (1 << MLC_STREAMER_BIT)
                else:
                    return current_reg_value
            else:
                if register_name == '0x1A4': #ON
                    current_reg_value = current_reg_value & ~(1 << MLC_STREAMER_BIT)
                elif register_name == "0x1320":
                # ON-MD-XQ-DD-DDO
                    MD = int (status.split("-")[1])
                    XQ = int (status.split("-")[2])
                    current_reg_value = self.change_certain_bits(20, 24, MD, current_reg_value)   # Set the max distance
                    current_reg_value = self.change_certain_bits(0, 4, XQ, current_reg_value)     # Set the XQ
    
                elif register_name == "0x1321":
                    DD = int (status.split("-")[3])
                    DDO = int (status.split("-")[4])
                    current_reg_value = self.change_certain_bits(21, 28, DD, current_reg_value)   #set the demand density
                    current_reg_value = self.change_certain_bits(29, 32, DDO, current_reg_value)  #set the demand density override
           
        elif prefetcher_name == "L2_NLP":
            # if status == "0x161122147800":  #ON
            if status == "OFF":
                current_reg_value = current_reg_value | (1 << L2_NLP_BIT)
            elif status == 'ON':  
                # print("status14: ", status)
                current_reg_value = current_reg_value & ~(1 << L2_NLP_BIT)
        return current_reg_value


    def set_prefetcher_status(self, prefetcher_name, status, core):
        """
        Set the status of a specific prefetcher for a given core.

        Args:
            prefetcher_name (str): The name of the prefetcher (e.g., "LLC_STREAMER", "MLC_STREAMER").
            status (str): The desired status of the prefetcher (e.g., "ON", "OFF").
            core (int): The core number to apply the changes to.

        Returns:
            int: The updated register value after applying the changes.
        """
        if prefetcher_name == "LLC_STREAMER":
            command = ["sudo", "rdmsr", "0x1320", "-p", str(core)]
            # print ("command1: ", command)
            try:
                # register_value: current value 
                register_value = subprocess.check_output(command, text=True).strip()
                # print("Current Register_val: ", bin(int(register_value, 16))[2:].zfill(64))
                # print("Current Register Value1: ", bin(int(register_value, 16))[2:].zfill(6))
            except subprocess.CalledProcessError as e:
                print("Error:", e)
        
            register = self.compute_register_value(prefetcher_name, status, int (register_value, 16), "0x1320")
            # print("Register Value111: ", register)
            command = ["sudo", "wrmsr", "-p", str(core), "0x1320", hex(register)]
            # print ("command2: ", command)
            try:
                command_output = subprocess.check_output(command, text=True).strip()
                # print(command_output)
            except subprocess.CalledProcessError as e:
                print("Error:", e)

             
            command = ["sudo", "rdmsr", "0x1322", "-p", str(core)]
            # print ("command1: ", command)
            try:
                # register_value: current value 
                register_value = subprocess.check_output(command, text=True).strip()
                # print("Current Register_val: ", bin(int(register_value, 16))[2:].zfill(64))
                # print("Current Register Value1: ", bin(int(register_value, 16))[2:].zfill(6))
            except subprocess.CalledProcessError as e:
                print("Error:", e)
        
            register = self.compute_register_value(prefetcher_name, status, int (register_value, 16), "0x1322")
            # print("Register Value111: ", register)
            
            command = ["sudo", "wrmsr", "-p", str(core), "0x1322", hex(register)]
            
            # print ("command2: ", command)
            try:
                command_output = subprocess.check_output(command, text=True).strip()
                # print(command_output)
            except subprocess.CalledProcessError as e:
                print("Error:", e)

        elif prefetcher_name == "MLC_STREAMER":
            command = ["sudo", "rdmsr", "0x1A4", "-p", str(core)]
            try:
                # register_value: current value 
                register_value = subprocess.check_output(command, text=True).strip()
                # print("Current Register_val: ", bin(int(register_value, 16))[2:].zfill(64))
                # print("Current Register Value1: ", bin(int(register_value, 16))[2:].zfill(6))
            except subprocess.CalledProcessError as e:
                print("Error:", e)
        
            register = self.compute_register_value(prefetcher_name, status, int (register_value, 16), "0x1A4")
            command = ["sudo", "wrmsr", "-p", str(core), "0x1A4", hex(register)]

            try:
                command_output = subprocess.check_output(command, text=True).strip()
            except subprocess.CalledProcessError as e:
                print("Error:", e)


            command = ["sudo", "rdmsr", "0x1320", "-p", str(core)]
            try:
                # register_value: current value 
                register_value = subprocess.check_output(command, text=True).strip()
                # print("Current Register_val: ", bin(int(register_value, 16))[2:].zfill(64))
                # print("Current Register Value1: ", bin(int(register_value, 16))[2:].zfill(6))
            except subprocess.CalledProcessError as e:
                print("Error:", e)
        
            register = self.compute_register_value(prefetcher_name, status, int (register_value, 16), "0x1320")
            # print("Register Value111: ", register)
            
            command = ["sudo", "wrmsr", "-p", str(core), "0x1320", hex(register)]
            try:
                command_output = subprocess.check_output(command, text=True).strip()
                # print(command_output)
            except subprocess.CalledProcessError as e:
                print("Error:", e)

             
            command = ["sudo", "rdmsr", "0x1321", "-p", str(core)]
            try:
                # register_value: current value 
                register_value = subprocess.check_output(command, text=True).strip()
                # print("Current Register_val: ", bin(int(register_value, 16))[2:].zfill(64))
                # print("Current Register Value1: ", bin(int(register_value, 16))[2:].zfill(6))
            except subprocess.CalledProcessError as e:
                print("Error:", e)
        
            register = self.compute_register_value(prefetcher_name, status, int (register_value, 16), "0x1321")
            # print("Register Value111: ", register)
            
            command = ["sudo", "wrmsr", "-p", str(core), "0x1321", hex(register)]
            try:
                command_output = subprocess.check_output(command, text=True).strip()
                # print(command_output)
            except subprocess.CalledProcessError as e:
                print("Error:", e)

        elif prefetcher_name == "L2_NLP":
            command = ["sudo", "rdmsr", "0x1321", "-p", str(core)]
            
            try:
                # register_value: current value 
                register_value = subprocess.check_output(command, text=True).strip()
                # print("Current Register Value1: ", bin(int(register_value, 16))[2:].zfill(6))
            except subprocess.CalledProcessError as e:
                print("Error:", e)

            register = self.compute_register_value(prefetcher_name, status, int (register_value, 16), "0x1321")
            command = ["sudo", "wrmsr", "-p", str(core), "0x1321", hex(register)]
            try:
                command_output = subprocess.check_output(command, text=True).strip()
                # print(command_output)
            except subprocess.CalledProcessError as e:
                print("Error:", e)

        else:   #l1_nlp, l1_ipp, l1_npp, amp
            command = ["sudo", "rdmsr", "0x1A4", "-p", str(core)]
            # print ("command5: ", command)
            try:
                # register_value: current value 
                register_value = subprocess.check_output(command, text=True).strip()
                # print("Current Register Value1: ", bin(int(register_value, 16))[2:].zfill(6))
            except subprocess.CalledProcessError as e:
                print("Error:", e)

            register = self.compute_register_value(prefetcher_name, status, int (register_value, 16), "0x1A4")
            command = ["sudo", "wrmsr", "-p", str(core), "0x1A4", hex(register)]
            try:
                command_output = subprocess.check_output(command, text=True).strip()
            except subprocess.CalledProcessError as e:
                print("Error:", e)
     
        return register

    def _exec_envcmd(self, config, changes):
        """
        Set environnement parameters through commands

        Args:
            config (dict[str, dict]): The configuration to use
            changes list[bool]: Indicate which compile flags have changed since last compilation
        """
        def write_msr_to_cores(cores, msr, value):
            for core in cores:
                cmd = f"sudo /usr/sbin/wrmsr -p {core} {msr} {value}"
                exec_cmd(cmd, self._custom_env)

        for i, (k, v) in enumerate(config["envcmd"].items()):
            if not changes[i]:
                continue

            if k == "sudo /usr/sbin/wrmsr -a 0x1A4 ":
                write_msr_to_cores(range(8, 24), "0x1A4", v)

            elif v in {"0x108837ea470906c4", "0x10883fea470906c4"}:
                write_msr_to_cores([8, 12, 16, 20], "0x1320", v)

            elif v in {"0x161122147800", "0x171122147800"}:
                write_msr_to_cores([8, 12, 16, 20], "0x1321", v)

            elif "freq.sh" in k:
                exec_cmd(f"{k} {v}", self._custom_env)


    def _reset_envcmd(self):
        """
        Reset environnement parameters through commands
        """
        register_map = {
            "MLC_STREAMER": "0x1A4",
            "L1_NLP": "0x1A4",
            "L1_IPP": "0x1A4",
            "L1_NPP": "0x1A4",
            "AMP": "0x1A4",
            "LLC_STREAMER": "0x1320",
            "L2_NLP": "0x1321",
        }

        full_range_cores = range(8, 24)  # Cores 8-23
        specific_cores = [8, 12, 16, 20]  #LLC_STREAMER & L2_NLP are set per modules, every 4 cores = 1 module
        for cmd in self.config.space["envcmd"]:
            print("resetting: ")
            if cmd["name"] in {"MLC_STREAMER", "L1_NLP", "L1_IPP", "L1_NPP", "AMP"}:
                for core in full_range_cores:
                    k = f"sudo /usr/sbin/wrmsr -p {core} {register_map[cmd['name']]} {cmd['reset']}"
                    exec_cmd(k, self._custom_env)
            elif cmd["name"] in {"LLC_STREAMER","L2_NLP"}:
                for core in specific_cores:
                    k = f"sudo /usr/sbin/wrmsr -p {core} {register_map[cmd['name']]} {cmd['reset']}"
                    exec_cmd(k, self._custom_env)
            elif "freq.sh" in cmd["name"]:
                exec_cmd(cmd["name"] + " " + str(cmd["reset"]), self._custom_env)
           

    # Run the space exploration for all applications
    @abstractmethod
    def run(self):
        pass
