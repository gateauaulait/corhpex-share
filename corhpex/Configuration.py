import tomli
import re
from option import Option, Some, Nothing

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
