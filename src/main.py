#!/usr/bin/python3

import argparse
import subprocess
import os
#from spacex import Explorer
from ExhaustiveExplorer import ExhaustiveExplorer
from GAExplorer import GAExplorer
from BayesianOptimExplorer import BayesianOptimExplorer

def custom_pruning(config, entry_point="pre_exec"):
    # Early pruning for compiler flags only
    if entry_point == "pre_bench":
        if config["compileflags"]:
            if config["compileflags"].get("-O3", False) and config["compileflags"].get("-O2", False):
                return True
            if not config["compileflags"].get("-O3", False) and not config["compileflags"].get("-O2", False):
                return True

    # Late pruning : happens right before the evaluation can mix conditions on all dimensions
    if entry_point == "pre_exec":
        if config["execflags"].get("--fpstore", None) == "double" and config["execflags"].get("--fpcomp", None) == "float":
            return True
    return False

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='cmd', required=True)

    parser_explo = subparsers.add_parser("explo", aliases=["e", "exp"], help="Exploration of the space")
    parser_explo.add_argument('configfile', type=str, nargs=1, help='name of the config file to use, if none is given use "test.toml"')
    parser_explo.add_argument('-d', '--dirname', default=None, type=str, nargs='?',help='path of the result directory')
    parser_explo.add_argument('-f', '--force', action='store_true', help='Force the exploration')
    parser_explo.add_argument('-a', '--algo', choices=["all", "ga", "bo"], default="all", help='Force the exploration')

    args = parser.parse_args()
    if args.dirname:
        args.dirname = os.path.abspath(args.dirname)

    if args.algo == "all":
        explorer = ExhaustiveExplorer(args.configfile[0], custom_pruning, args.force, args.dirname)
    if args.algo == "ga":
            explorer = GAExplorer(args.configfile[0], custom_pruning, args.force, args.dirname)
    if args.algo == "bo":
            explorer = BayesianOptimExplorer(args.configfile[0], custom_pruning, args.force, args.dirname)

    if (args.cmd == "explo" or args.cmd == "exp" or args.cmd == "e"):
        explorer.run()
    if (args.cmd == "aggregation" or args.cmd == "a"):
        explorer.data_agreggation()

main()


