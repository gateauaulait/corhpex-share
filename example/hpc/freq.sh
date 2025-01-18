#!/usr/bin/bash

# when using governors
#for i in {0..$1}; do sudo cpufreq-set -c $i -g $2; done

# when using explicit values
for i in $( seq 0 $1 ); do sudo cpufreq-set -c $i -d $2 -u $2; done