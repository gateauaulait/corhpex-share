from functools import reduce
import os
import operator
import itertools
from .utils import exec_cmd

class SubSpaceExplorer:

    def __init__(self, space, subspace):
        self.space = space[subspace]

        # Insert values for flags that are just on or off
        for d in self.space:
            d.setdefault("values", [True, False])

        self.subspace_size = reduce(operator.mul, [len(d["values"]) for d in self.space], 1)
        self.subspace = subspace

        self.__counter = 0
        self.__lvl = 0

        # Initialize subconfig with the dimensions'names
        self.__subconfig = {}
        for d in self.space:
            self.__subconfig[d["name"]] = None

        # Initialize iterators on values for each dimension
        self.__val_iter = [iter(d["values"]) for d in self.space]

    def __iter__(self):
        return self

    def __next__(self):
        changes = [False for _ in range(len(self.space))]
        if self.__counter >= self.subspace_size:
            raise StopIteration
        while self.__lvl < len(self.space):
            try:
                self.__subconfig[self.space[self.__lvl]["name"]] = next(self.__val_iter[self.__lvl])
                changes[self.__lvl] = True
                self.__lvl += 1
            except StopIteration:
                # If the values for this dimension have been exhausted
                # Reinitialize the iterator and go to the previous level
                self.__val_iter[self.__lvl] = iter(self.space[self.__lvl]["values"])
                self.__lvl -= 1
        self.__lvl -= 1
        self.__counter += 1
        return self.__subconfig, changes

class MultiSpaceExplorer:

    def __init__(self, space, group, config=dict()):
        self.space = space
        self.subspaces = group
        self.__sub_explorers = [SubSpaceExplorer(self.space, sub) for sub in self.subspaces]
        self.__lvl = 0
        self.__counter = 0
        self.space_size = reduce(operator.mul, [sub.subspace_size for sub in self.__sub_explorers], 1)
        self.__config = config
        for ss in group:
            self.__config[ss] = None

    def __iter__(self):
        return self

    def __next__(self):
        changes = [[False for _ in range(sub.subspace_size)] for sub in self.__sub_explorers]
        if self.__counter >= self.space_size:
            raise StopIteration
        while self.__lvl < len(self.subspaces):
            try:
                self.__config[self.subspaces[self.__lvl]],changes[self.__lvl] = next(self.__sub_explorers[self.__lvl])
                self.__lvl += 1
            except StopIteration:
                # If the values for this dimension have been exhausted
                # Reinitialize the iterator and go to the previous level
                self.__sub_explorers[self.__lvl] = SubSpaceExplorer(self.space, self.subspaces[self.__lvl])
                self.__lvl -= 1
        self.__lvl -= 1
        self.__counter += 1
        return self.__config, changes

class BenchAppIter:
    def __init__(self, benchs):
        self.__benchs = benchs
        self.__nbr_benchs = len(benchs)
        self.__nbr_apps = 0
        self.__current_bench = 0
        self.__current_app = 0
        self.__saved_cwd = []


    def __iter__(self):
        return self

    def __next__(self):
        while self.__current_bench < self.__nbr_benchs:
            b = self.__benchs[self.__current_bench]
            if self.__nbr_apps == 0:
                self.__nbr_apps = len(b["apps"])
                a = b["apps"][self.__current_app]
                self.__saved_cwd.append(os.getcwd())
                # Move to root directory of the benchmark
                os.chdir(b["root_dir"])
                self.__saved_cwd.append(os.getcwd())
                # Go to the application's directory (if there is one)
                os.chdir(a["root_dir"])
            while self.__current_app < self.__nbr_apps:
                a = b["apps"][self.__current_app]
                # Go back to the benchmark directory
                os.chdir(self.__saved_cwd.pop())
                self.__saved_cwd.append(os.getcwd())
                # Go to the application's directory (if there is one)
                os.chdir(a["root_dir"])
                self.__current_app += 1
                return {"b": b, "a": a}
            self.__current_app = 0
            self.__nbr_apps = 0
            self.__current_bench += 1
            # Go back to the user's current working directory for the next benchmark
            os.chdir(self.__saved_cwd.pop())
            os.chdir(self.__saved_cwd.pop())

        raise StopIteration
