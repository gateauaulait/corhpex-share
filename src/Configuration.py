import tomli
import re
import os
from option import Option, Some, Nothing
from utils import exec_cmd

class Configuration:
    def __init__(self, config_file, force=False, res_dir=None):

        # Compile thread-binding-generator if needed
        dir_path = os.path.dirname(__file__)
        exec_cmd("cd " + dir_path + "/../thread-binding-generator; make; cd -")

        with open(config_file, "rb") as f:
            config = tomli.load(f)
            self.benchmarks = config["benchmarks"]
            self.meta_rep = config["meta_rep"]
            self.res_stats = config["stat_fn"]
            self.space = config["exploration-space"]
            self.algo_params = config.get("algo_params", {})
            # directory to hold measurement
            self.res_dir = os.path.abspath(config.get("res_dir", "res_dir/"))
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
                # If the mesure section is absent add an empty perfcounter section
                self.measure["perfcounters"] = Option.empty()

        # ensures all subspaces are declared
        self.space.setdefault("compileflags", dict())
        self.space.setdefault("execflags", dict())
        self.space.setdefault("envvars", dict())
        self.space.setdefault("envcmd", dict())

        # flags on off values
        for d in self.space["compileflags"]:
            d.setdefault("values", [True, False])

        for d in self.space["execflags"]:
            d.setdefault("values", [True, False])

    # TODO rename into get_id
    # Returns an id string for the configuration
    # param config: the configuration to use, a dictionary of dictionaries
    # param ba: useless (only here for consistency)
    def get_conf(self, config, ba=None):
        id_str = ""
        pattern = re.compile('[\W_]+')
        for sub, desc in config.items():
            for i,(k,v) in enumerate(desc.items()):
                space_desc_entry = next(dim for dim in self.space[sub] if dim["name"] == k)
                if space_desc_entry["values"] == [True, False]:
                    if v:
                        id_str = id_str + "_" + pattern.sub('', k)
                elif "id" in space_desc_entry:
                    id_str = id_str + "_" + space_desc_entry["id"] + str(v)
                else:
                    id_str = id_str + "_" + pattern.sub('', str(v))

        return id_str.lstrip("_")
