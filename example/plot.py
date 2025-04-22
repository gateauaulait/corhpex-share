import pandas as pd
import glob
import os
import plotly.graph_objects as go
import plotly.express as px

# benchmark names and corresponding file patterns
benchmark_files = {
    "CG": "bo_explo_CG*.csv",
    "BT": "bo_explo_BT*.csv",
    "SP": "bo_explo_SP*.csv",
    "streamcluster": "bo_explo_streamcluster*.csv",
    "kmeans": "bo_explo_kmeans*.csv"
}

# base directory for results
results_dir = '/home/uartdev/behnaz/corhpex-share/example/res-hpc-bo/'

# Create a color scale that generates unique colors for each point
color_scale = px.colors.sequential.Viridis  # You can choose other scales like "Rainbow", "Blues", etc.

# Loop through each benchmark and generate plots
for benchmark, pattern in benchmark_files.items():
    csv_files = glob.glob(os.path.join(results_dir, pattern))

    # Check if any CSV files were found
    if not csv_files:
        raise FileNotFoundError(f"No CSV files matching the pattern '{pattern}' found.")

    # Read the first matching CSV file
    df = pd.read_csv(csv_files[0])

    # Extract the second column for legends
    legends = df.iloc[:, 1]

    # Create the Plotly figure for the benchmark
    fig = go.Figure()

    # Create a scatter plot for each point with its corresponding legend and color
    for i in range(len(df)):
        # Assign a unique color for each point using the color scale
        color = color_scale[i % len(color_scale)]  # Ensures the colors loop if there are more than the number of colors in the scale

        # Add a trace for each point
        fig.add_trace(go.Scatter(
            x=[df.iloc[i, 4]],
            y=[df.iloc[i, 3]],
            mode='markers',
            marker=dict(color=color, size=10),
            name=f'{legends[i]} ({i+1})',  # Make the legend informative with the index
            hovertext=f'Benchmark: {benchmark}<br>Legend: {legends[i]}<br>Index: {i+1}',  # Show more info on hover
            hoverinfo='text',  # Display only the custom hover text
            customdata=[legends[i]]  # Store the legend in the customdata field
        ))

    # Update layout for labels, title, and legend
    fig.update_layout(
        title=f'{benchmark} Benchmark Results',
        xaxis_title='Energy Consumption (1/energy consumption -Joule)',
        yaxis_title='Performance (1/execution time)',
        showlegend=True,  # Make sure the legend is visible
        legend_title="Configurations",
        clickmode='event+select'  # Enable click events
    )

    # Add a callback for click events (this needs to be done in the HTML/js code, so it won't directly work in Python).
    # However, we can add customdata to store information and visualize it on hover.

    # Define the path where the HTML will be saved
    html_path = os.path.join(results_dir, f'{benchmark}_plot.html')

    # Save the interactive plot as an HTML file
    fig.write_html(html_path)

    # Print confirmation for the user
    print(f"Interactive plot saved as: {html_path}")