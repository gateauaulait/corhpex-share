#!/usr/bin/bash

# P/E cores random frequencies between min and max values
p=("1500MHz" "2000MHz" "3000MHz" "3500MHz" "4000MHz" "4500MHz" "5000MHz")
e=("1000MHz" "1500MHz" "2000MHz" "3200MHz" "3500MHz" "4000MHz" "4600MHz")

# Generate all combinations of P-core and E-core frequencies
sudo rm /home/uartdev/behnaz/corhpex-share/example/hpc/freq_generator.txt
path_to_freqs_file=/home/uartdev/behnaz/corhpex-share/example/hpc/freq_generator.txt
for p_freq in "${p[@]}"; do
    for e_freq in "${e[@]}"; do
        echo "${p_freq}_${e_freq}" >> "$path_to_freqs_file"
    done
done
