import tomli
import re
import os
from .option import Option, Some, Nothing
from .utils import exec_cmd
import datetime
import time

class Configuration:
    def __init__(self, config_file, force=False, res_dir=None):

        # Compile thread-binding-generator if needed
        dir_path = os.path.dirname(__file__)
        exec_cmd("cd " + dir_path + "/../thread-binding-generator; make; cd -")

        with open(config_file, "rb") as f:
            config = tomli.load(f)
            self.name = config.get("name", datetime.datetime.fromtimestamp(time.time()).strftime("%Y%m%d%H%M"))
            self.benchmarks = config["benchmarks"]
            self.meta_rep = config["meta_rep"]
            self.res_stats = config["stat_fn"]
            self.space = config["exploration-space"]
            self.algo = config["algo"]
            self.algo_params = config.get("algo_params", {})
            envcmd = self.space.get("envcmd", [])
            if isinstance(envcmd, list) and len(envcmd) > 0:
                envcmd = envcmd[0]
            if isinstance(envcmd, dict) and "freqs_gen_cmd" in envcmd:
                script_or_file_path = envcmd["freqs_gen_cmd"]
                exec_cmd("chmod +x " + script_or_file_path)
                exec_cmd(script_or_file_path)
                filename = script_or_file_path.replace(".sh", ".txt")
                filename = filename.split()[1]
                val_list = []
                with open (filename, 'r') as file:
                    for line in file:
                        val_list.append(line.strip())
                envcmd["values"] = val_list

            # directory to hold measurement
            self.res_dir = os.path.abspath(config.get("res_dir", "res_dir")) + "/"
            if res_dir != None:
                self.res_dir = res_dir
            self.force = force
            print(self.res_dir)

            # set up what is mesured and how
            self.metrics = config["metrics"]

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
    def get_conf(self, config, ba=None):
        """
        Returns an id string for the configuration

        Args:
            config dict[str, dict]: the configuration to use
            ba: useless (only here for consistency)

        Returns:
            str: the configuration identifer
        """
        id_str = ""
        pattern = re.compile('[\W_]+')
        for sub, desc in sorted(config.items()):
            for i,(k,v) in enumerate(sorted(desc.items())):
                space_desc_entry = next(dim for dim in self.space[sub] if dim["name"] == k)
                if space_desc_entry["values"] == [True, False]:
                    if v:
                        id_str = id_str + "_" + pattern.sub('', k)
                elif "id" in space_desc_entry:
                    id_str = id_str + "_" + space_desc_entry["id"] + str(v)
                else:
                    id_str = id_str + "_" + pattern.sub('', str(v))

        return id_str.lstrip("_")
