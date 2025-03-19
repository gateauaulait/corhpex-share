#!/usr/bin/bash

# Reset the frequencies and the governor of the CPUs to the default values

#P-cores: 800000 5000000
for i in {0..7}; do
    echo powersave | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor
    echo 800000 | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_min_freq
    echo 5000000 | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_max_freq
done

#E-cores: 800000 4600000
for i in {8..23}; do
    echo powersave | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor
    echo 800000 | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_min_freq
    echo 4600000 | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_max_freq
done