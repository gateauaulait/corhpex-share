import pandas as pd
import glob
import matplotlib.pyplot as plt

# Find the CSV file that matches the pattern
csv_files = glob.glob('/home/uartdev/behnaz/corhpex-share/example/res-hpc-bo/bo_explo_*.csv')
if not csv_files:
    raise FileNotFoundError("No CSV file matching the pattern 'bo_expl_*.csv' found.")

# Read the CSV file
df = pd.read_csv(csv_files[0])

# Extract the second column for legends
legends = df.iloc[:, 1]
print(legends)

# Check if the CSV has at least 5 columns
if df.shape[1] < 5:
    raise ValueError("CSV file does not have at least 5 columns.")

# Plot the data
plt.figure(figsize=(10, 6))

# Create a colormap for 20 colors
cmap = plt.get_cmap('tab20')
norm = plt.Normalize(vmin=0, vmax=len(df) - 1)

# Scatter plot with legends for each data point
for i in range(len(df)):
    plt.scatter(df.iloc[i, 4], df.iloc[i, 3], label=legends[i] , color=cmap(i % cmap.N))

# Labeling and showing plot
plt.xlabel('Energy Consumption (Joule)')
plt.ylabel('Performance')


# Add the legend (showing only unique labels)
plt.legend()
plt.grid(True)
plt.show()

# Save the plot as a PDF file
pdf_path = '/home/uartdev/behnaz/corhpex-share/example/res-hpc-bo/plot.pdf'
plt.savefig(pdf_path, format='pdf')