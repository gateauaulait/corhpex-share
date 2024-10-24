#!/usr/bin/python3

import argparse
import os
import corhpex

def pruning(config, entry_point="pre_exec"):
    return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('configfile', type=str, nargs=1, help='name of the config file to use, if none is given use "test.toml"')
    parser.add_argument('-d', '--dirname', default=None, type=str, nargs='?',help='path of the result directory')
    parser.add_argument('-f', '--force', action='store_true', help='Force the exploration')

    args = parser.parse_args()
    # Turn dir name to absolute path
    if args.dirname:
        args.dirname = os.path.abspath(args.dirname)

    # Create the exploration configuration from the config file
    explo_config = corhpex.Configuration(args.configfile[0], force=args.force, res_dir=args.dirname)
    # Create the explorer from the configuration
    explorer = corhpex.explorer_from(explo_config, prune=pruning)
    # Run the exploration
    explorer.run()

main()


