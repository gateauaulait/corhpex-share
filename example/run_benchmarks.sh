#!/bin/bash

# List of applications to run with their respective configuration files
applications=(
    "hpc/test-one-code-bo-no-likwid.toml"
    "hpc/test-one-code-bo-BT.toml"
    "hpc/test-one-code-bo-SP.toml"
    "hpc/test-one-code-bo-rodinia-streamcluster.toml"
    "hpc/test-one-code-bo-rodinia-kmeans.toml"
)

# Descriptive names for each application
descriptions=(
    "CG"
    "BT"
    "SP"
    "Streamcluster"
    "Kmeans"
)

# Loop through the applications
for i in "${!applications[@]}"; do
    echo "Running the ${descriptions[i]} application..."
    python3 ./main.py "${applications[i]}"

    # Check if the application ran successfully
    if [ $? -ne 0 ]; then
        echo "${descriptions[i]} application failed. Exiting."
        exit 1
    fi

    echo "${descriptions[i]} completed successfully."
done
