# Simulation Analysis Tool

The analysis tool generates comprehensive visualizations and statistics from simulation results.

## Installation

Ensure required dependencies are installed:

```bash
pip install pandas matplotlib seaborn
```

## Usage

### Run Analysis on a Simulation Folder

```bash
python analyze_simulation.py <results_directory>
```

**Example:**

```bash
# Analyze the most recent simulation
python analyze_simulation.py simulated_results/simulation_20251231_143022

# Or find and analyze any simulation
ls simulated_results/
python analyze_simulation.py simulated_results/simulation_20251224_081530
```

## Output

The analysis script generates the following files in `<results_directory>/analysis/`:

### Visualizations (PNG files)

1. **01_device_vs_edge_time.png**
   - Line plots showing device vs edge execution times for each scenario
   - Displays first 50 inferences per scenario
   - Useful for understanding the distribution of work between device and edge

2. **02_total_inference_time.png**
   - Bar chart of average total inference time (device + edge) per scenario
   - Shows standard deviation as error bars
   - Helps identify which scenarios are slowest

3. **03_throughput_comparison.png**
   - Bar chart of inference throughput (inferences/second) per scenario
   - Color-coded by simulation duration (30s, 45s, 60s)
   - Useful for comparing scenario efficiency

4. **04_timing_distributions.png**
   - Boxplots of device and edge execution time distributions
   - Shows median, quartiles, and outliers
   - Helps identify variability and outliers in each scenario

5. **05_layer_statistics.png**
   - Grouped bar chart of device vs edge layer counts
   - Shows on average how many layers run on each side
   - Useful for understanding partitioning strategies

6. **06_scenario_comparison_dashboard.png**
   - Comprehensive 3x3 dashboard with 9 subplots:
     - Average device time
     - Average edge time
     - Average total time
     - Device time variance
     - Edge time variance
     - Inference count
     - Min device time
     - Max device time
     - Device layer count
   - Provides complete overview of all metrics

7. **07_summary_statistics.png**
   - Table visualization of summary statistics
   - Includes all key metrics for each scenario in tabular format
   - Easy reference for comparison

### Data Files

**summary_statistics.csv**
- Comma-separated values with summary metrics
- Columns: Scenario, Inferences, Device, Edge, Total, Throughput, Clients
- Can be imported into Excel or other analysis tools
- Device/Edge times shown as mean ± std dev in milliseconds

## Understanding the Results

### Device vs Edge Time
- **Device time**: Inference execution on the mobile device
- **Edge time**: Inference execution on the edge server
- Lower device time suggests more work pushed to edge
- Higher device time suggests more work kept on device

### Throughput
- **Inferences/sec** = Total inferences / Duration
- Higher throughput indicates better responsiveness
- Multi-client scenarios may show lower throughput due to server load

### Variance (Std Dev)
- Measures consistency of execution times
- Lower variance indicates predictable performance
- High variance may indicate resource contention or network instability

### Layer Statistics
- Shows how the model is partitioned
- Device layers run on mobile
- Edge layers run on server
- Sum of device + edge layers equals total model depth

## Interpreting Specific Scenarios

### Baseline vs Delay Scenarios
Compare `baseline` with delay scenarios to see impact:
- **network_delay_20ms** - Adds 20ms network latency
- **computation_delay_2ms** - Adds 2ms computation delay
- **mobile_realistic** - Realistic combined delays

### Multi-Client Scenarios
- **multi_client_baseline** - 3 clients, no delays (baseline load)
- **multi_client_network** - 3 clients with 25ms network delay

Look for:
- Throughput reduction under multiple clients
- Increased latency variance
- Server CPU/memory impact

## Analysis Examples

### Compare Two Scenarios

```python
import pandas as pd

# Load both scenarios from the same simulation folder
baseline = pd.read_csv('simulated_results/simulation_20251231_143022/baseline_inference_results.csv')
network = pd.read_csv('simulated_results/simulation_20251231_143022/network_delay_20ms_inference_results.csv')

# Calculate impact
baseline_total = (baseline['avg_device_time'] + baseline['avg_edge_time']).mean() * 1000
network_total = (network['avg_device_time'] + network['avg_edge_time']).mean() * 1000
impact = ((network_total - baseline_total) / baseline_total) * 100

print(f"Baseline total time: {baseline_total:.2f}ms")
print(f"Network delay impact: +{impact:.1f}%")
```

### Calculate Throughput by Duration

```python
import pandas as pd
import json

# Load CSV and config
results = pd.read_csv('simulated_results/simulation_20251231_143022/baseline_inference_results.csv')
with open('simulated_results/simulation_20251231_143022/baseline_scenario_config.json') as f:
    config = json.load(f)

duration = config['duration_seconds']
throughput = len(results) / duration
print(f"Throughput: {throughput:.2f} inferences/sec")
```

### Find Performance Outliers

```python
import pandas as pd

df = pd.read_csv('simulated_results/simulation_20251231_143022/baseline_inference_results.csv')
total_time = df['avg_device_time'] + df['avg_edge_time']
threshold = total_time.mean() + 2 * total_time.std()

print(f"Mean total time: {total_time.mean()*1000:.2f}ms")
print(f"Std dev: {total_time.std()*1000:.2f}ms")
print(f"Outlier threshold: {threshold*1000:.2f}ms")

outliers = df[total_time > threshold]
print(f"Found {len(outliers)} outliers ({len(outliers)/len(df)*100:.1f}%)")
```

## Troubleshooting

### "No inference results CSV files found"
- Ensure simulation completed successfully
- Check that results directory path is correct
- Verify CSV files exist: `ls <results_directory>/*_inference_results.csv`

### Missing plots
- Check that matplotlib is installed: `pip install matplotlib`
- Verify write permissions to the analysis output directory
- Look for error messages in terminal output

### Plot looks empty or cut off
- This is usually a rendering issue with matplotlib
- Try recreating the analysis or adjusting figure size in the script

### Can't import seaborn
- Seaborn is optional and provides prettier styling
- Analysis works fine without it
- Install with: `pip install seaborn`

## Extending the Analysis

To add custom plots, edit `analyze_simulation.py`:

```python
def plot_custom_metric(self):
    """Add a new plot"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    scenarios = sorted(self.data.keys())
    custom_values = []
    
    for scenario in scenarios:
        df = self.data[scenario]
        # Your custom calculation here
        value = df['column_name'].mean()
        custom_values.append(value)
    
    ax.bar(range(len(scenarios)), custom_values)
    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels(scenarios, rotation=45, ha='right')
    ax.set_title('Your Custom Metric')
    
    plt.tight_layout()
    plt.savefig(self.output_dir / "08_custom_metric.png", dpi=150, bbox_inches='tight')
    plt.close()

# In analyze_all() method, add:
# self.plot_custom_metric()
```

## Performance Notes

- Analysis typically completes in 5-10 seconds
- Supports simulations with thousands of inferences
- Memory usage is proportional to CSV file size
- PNG generation uses 150 DPI for high quality (adjust with `dpi=` parameter if needed)
