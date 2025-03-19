#!/usr/bin/bash

num_cores=$1
ep_boundry=$2   # 0-7: E-cores, 8-23: P-cores , ep_boundry=8
freq_input=$3

#extract P-cores and E-cores frequency
p_freq=$(echo $freq_input | cut -d'_' -f1) #first part before '_'
e_freq=$(echo $freq_input | cut -d'_' -f2) #second part after '_'

#set frequency and goernor for P-cores
p_core_max_index=$((ep_boundry - 1))
for i in $(seq 0 $p_core_max_index); do
    echo performance | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor
    sudo cpufreq-set -c $i -d $p_freq -u $p_freq
done

#set frequency and governor for E-cores
for i in $(seq $ep_boundry 23); do
    echo performance | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor
    sudo cpufreq-set -c $i -d $e_freq -u $e_freq
done