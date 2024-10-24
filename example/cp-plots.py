#!/usr/bin/python3

import pandas as pd
import seaborn as sb
import numpy as np
import matplotlib.pyplot as plt
import argparse
import re
import numpy as np

directory = "exp-cp/"

t = "med"

# Time data
data = pd.read_csv(directory+"/rdtsc_"+t+".csv", sep=",", index_col="apps",nrows=1).sort_values(by='apps')
data.columns.name = 'configs'
data.rename({"rdtsc": "time"})
data_ = data.copy(deep=True)
data_ = data_.reset_index()
data_ = pd.melt(data_, id_vars=['apps'], value_name='time')
time_mean = np.mean(data_['time'])
data_['Speedup'] = np.full(data_['time'].shape, time_mean)/data_['time']
data_['th'] = data_['configs'].str.extractall(r'th(\d+)').unstack().fillna('').sum(axis=1).astype(int)
data_['pkg'] = data_['configs'].str.extractall(r'pkg(\d+)').unstack().fillna('').sum(axis=1).astype(int)
data_['die'] = data_['configs'].str.extractall(r'die(\d+)').unstack().fillna('').sum(axis=1).astype(int)
data_['l3'] = data_['configs'].str.extractall(r'l3(\d+)').unstack().fillna('').sum(axis=1).astype(int)
data_['smt'] = data_['configs'].str.extractall(r'smt(\d+)').unstack().fillna('').sum(axis=1).astype(int)

# Energy data
data2 = pd.read_csv(directory+"/energy_"+t+".csv", sep=",", index_col="apps",nrows=1).sort_values(by='apps')
data2.columns.name = 'configs'
data2_ = data2.copy(deep=True)
data2_ = data2_.reset_index()
data2_ = pd.melt(data2_, id_vars=['apps'], value_name='energy')
energy_mean = np.mean(data2_['energy'])
data2_['energy_savings'] = np.full(data2_['energy'].shape, energy_mean)/data2_['energy']

data_['energy'] = data2_['energy']
data_['Energy_savings'] = data2_['energy_savings']
data_['scatter_factor'] = (1-data_['pkg'])*4 + (1-data_['die'])*2 + (1-data_['l3'])

# Plot 
f, axs = plt.subplots(figsize=(8, 4), layout="tight")
sb.scatterplot(data_, y="Energy_savings", x="Speedup", hue="th", size="scatter_factor", palette="muted", alpha=0.3, sizes=(20, 200), ax=axs)
f.savefig("time_enrgy_cp.png")

# Print the pareto set
def pareto2d(points):
    pareto = []
    points = points.sort_values(["time", "energy"], ascending=[True, True])
    for p in points.itertuples():
        x, y = p.time, p.energy
        if pareto == [] or y < pareto[-1].energy :
            pareto.append(p)
    return pareto

pareto = pd.DataFrame(pareto2d(data_))
print(pareto["configs"])
