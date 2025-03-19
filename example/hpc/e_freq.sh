#!/usr/bin/bash

num_cores=23
ep_boundry=8   # 0-7: E-cores, 8-23: P-cores , ep_boundry=8
e_freq=$1
p_core_max=$((ep_boundry - 1))

# set frequency and goernor for E-cores
for i in $(seq $ep_boundry $num_cores); do
    echo performance | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor
    sudo cpufreq-set -c $i -d $e_freq -u $e_freq
done