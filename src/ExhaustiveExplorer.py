from .BaseExplorer import BaseExplorer
from .space_iterators import MultiSpaceExplorer, BenchAppIter

class ExhaustiveExplorer(BaseExplorer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _explore(self, action_func, bench_iter, apply_config=True):
        """
        Run the exhaustive exploration

        Iterate over the design space and the applications and execute the action function for
        all combinations.

        Args:
            action_func (fn): The function to execute for each design on each application
            bench_iter (Iterator): The applications iterator
            apply_config (bool): if true apply the configuration, else don't apply (to save time)
        """
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


                    if not self.aggregator.app_config_was_evaluated(ba["b"], ba["a"], config):
                        action_func(config, ba)
                    else:
                        self.aggregator.get_app_config_metric_stat(ba["b"], ba["a"], config)[0]

        # Clean up environment
        if apply_config:
            self._reset_envcmd()

    def run(self):
        """
        Run an exploration for all applications
        """
        self._explore(self._evaluate, lambda : BenchAppIter(self.config.benchmarks))
