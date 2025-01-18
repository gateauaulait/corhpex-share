#!/usr/bin/env python

import sys
import csv
import os
import argparse
import subprocess
from subprocess import call
from subprocess import Popen, PIPE
import os
import csv
import sys


# Execute string cmd in shell
def exec_cmd(cmd):
    print(cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,shell=True)
    result = p.communicate()[0]
    p.wait()
    return str(result)

# build and return header for lib to use
def support_profile_lib():
    # full path to build dir of profile lib
    path_ori = os.getcwd()
    path_lib = path_ori + "/profile/"
    
    # compile the profile lib 
    os.chdir(path_lib)
    exec_cmd("make clean")
    exec_cmd("make")
    os.chdir(path_ori)    

    header_lib = "env OMP_TOOL_LIBRARIES=" + path_lib + "libinit.so"
    return header_lib

# app_exec [0] => exec command
# app_exec [1] => path where to write run cmd
def write_run(run_cmd,app_exec):
    run_cmd = run_cmd + " " + app_exec[0]
    exec_cmd("echo '" + run_cmd + "' > " + app_exec[1] + "/run.sh")
    exec_cmd("chmod 777 " + app_exec[1] + "/run.sh")

# iterate over all the hpc bencharks and generate run.sh files
def write_run_files():
    run_cmd = support_profile_lib()
    print(run_cmd)
    
    # collect info to execute each benchmark
    app_exec = {}
    with open('execution_description.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile,delimiter=';')
        for row in reader:
            app_exec[row['app']] = []
            app_exec[row['app']].append(row['exec'])
            # if no location is provided, we use the app name as directory
            # this simplifies csv
            if row['location'] == None:
                app_exec[row['app']].append(row['app'])
            else:
                app_exec[row['app']].append(row['location'])
            
    # write for each benchmark a run file
    for k in app_exec.keys():
        write_run(run_cmd,app_exec[k])

def main():
    write_run_files()

main()