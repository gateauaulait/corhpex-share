from .ExhaustiveExplorer import ExhaustiveExplorer
from .GAExplorer import GAExplorer
from .BayesianOptimExplorer import BayesianOptimExplorer
from .LikwidAggregator import LikwidAggregator
from .ComputedAggregator import ComputedAggregator
from .MetaAggregator import MetaAggregator
from .SimpleAggregator import SimpleAggregator

__explorer_register = {
    "ga": GAExplorer,
    "bo": BayesianOptimExplorer,
    "all": ExhaustiveExplorer
}
"""
dict[str, Explorer]: A register of available explorers
"""

__aggregator_register = {
    "likwid": LikwidAggregator,
    "computed": ComputedAggregator,
    "simple": SimpleAggregator
}
"""
dict[str, Explorer]: A register of available aggregators
"""

def list_aggregators():
    """
    Print a list of the aggregators available
    """
    print("Aggregators")
    for k in __aggregator_register.keys():
        print(k)

def list_explorers():
    """
    Print a list of the explorers available
    """
    print("Explorers")
    for k in __explorer_register.keys():
        print(k)

def register_aggregator(name, aggregator_class):
    """
    Add an aggregator to the register to make it available

    Args:
        name (str): The name of the aggregator. It must be different than other names registered.
        aggregator_class (BaseAggregator): A class that inherits from BaseAggregator
    """
    __aggregator_register[name] = aggregator_class

def register_explorer(name, explorer_class):
    """
    Add an explorer to the register to make it available

    Args:
        name (str): The name of the explorer. It must be different than other names registered.
        explorer_class (BaseExplorer): A class that inherits from BaseExplorer
    """
    __explorer_register[name] = aggregator_class

def explorer_from(configuration, **kwargs):
    """
    Create an Explorer from a configuration object

    Args:
        configuration (Configuration): A configuration object
        kwargs (dict): Additional keyword arguments for the explorer creation (see specific explorers arguments)

    Returns:
        BaseExplorer: An explorer object that inherits from BaseExplorer
    """
    list_aggregators()
    
    metaaggregator = MetaAggregator(configuration)

    for k in configuration.metrics.keys():
        aggregator = __aggregator_register[k](configuration)
        print("ZZZ?",aggregator)
        metaaggregator.add(aggregator)

    algo = configuration.algo
    explorer = __explorer_register[algo](metaaggregator, configuration, **kwargs)
    return explorer
