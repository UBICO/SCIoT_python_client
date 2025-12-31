# Statistics Visualization Module

Comprehensive visualization and plotting tools for SCIoT performance metrics.

## Overview

The `statistics_visualizer.py` module generates high-quality plots from the statistics collected by the `StatisticsCollector` class. It provides multiple visualization methods for analyzing:

- **Inference Times**: Device vs edge execution time distribution
- **Layer Analysis**: Per-layer performance comparison and transmission sizes
- **Cumulative Costs**: Total execution time progression across layers
- **Offloading Metrics**: Cost breakdown for different offloading strategies

## Installation

The visualization module requires:
```bash
pip install matplotlib pandas
```

Already included in the project dependencies.

## Quick Start

### Basic Usage

```python
from src.server.statistics import StatisticsVisualizer

# Create visualizer instance
visualizer = StatisticsVisualizer()

# Generate all plots
visualizer.generate_all_plots()
```

### Command Line

```bash
python src/server/statistics/generate_plots.py
```

### Custom Directories

```bash
python src/server/statistics/generate_plots.py \
    --stats-dir /path/to/stats \
    --output-dir /path/to/output
```

## Generated Plots

### 1. **Inference Times Comparison** (`inference_times_comparison.png`)
- **Type**: Side-by-side bar charts
- **Metrics**: Device vs edge inference times per layer
- **Usage**: Identify layers where edge processing is faster
- **Insights**: Find optimization targets for offloading

### 2. **Inference Distribution** (`inference_distribution.png`)
- **Type**: Boxplot comparison
- **Metrics**: Statistical distribution of inference times
- **Usage**: Compare performance variability
- **Insights**: 
  - Median and quartile comparison
  - Outlier identification
  - Performance consistency

### 3. **Layer Sizes** (`layer_sizes.png`)
- **Type**: Bar chart with maximum highlighted
- **Metrics**: Data transmission size per layer output
- **Unit**: Kilobytes (KB)
- **Usage**: Identify bandwidth-heavy layers
- **Insights**: 
  - Transmission bottlenecks
  - Network cost drivers
  - Data reduction opportunities

### 4. **Statistics Summary** (`statistics_summary.png`)
- **Type**: Three-panel bar charts
- **Metrics**: 
  - Device inference times (min/mean/median/max)
  - Edge inference times (min/mean/median/max)
  - Layer sizes (min/mean/median/max)
- **Usage**: Quick overview of key metrics
- **Insights**: High-level performance characteristics

### 5. **Cumulative Costs** (`cumulative_costs.png`)
- **Type**: Line chart with area fill
- **Metrics**: Cumulative execution time progression
- **Usage**: Identify where cumulative latency increases
- **Insights**: 
  - Total latency contribution per layer
  - Cumulative bottleneck identification
  - Performance degradation points

### 6. **Offloading Metrics** (`offloading_metrics.png`) *[Optional]*
- **Type**: Four-panel analysis
  - **Panel 1**: Stacked area chart of cost components
  - **Panel 2**: Total latency per offloading point (with optimal highlighted)
  - **Panel 3**: Individual cost components (line chart)
  - **Panel 4**: Cost distribution percentages
- **Metrics**: Device, transmission, and edge costs
- **Usage**: Find optimal offloading strategy
- **Insights**: 
  - Best split point for minimal latency
  - Cost-benefit analysis of different strategies
  - Network impact on total latency

### 7. **Latency Distribution** (`latency_distribution.png`) *[Optional]*
- **Type**: Bar chart
- **Metrics**: Network latency statistics
- **Unit**: Seconds
- **Usage**: Understand network impact
- **Insights**: Network overhead quantification

## HTML Dashboard

An interactive `index.html` file is auto-generated in the plots directory:

```bash
# View the dashboard in a browser
open src/server/plots/index.html
```

The dashboard displays all generated plots in a clean, organized layout for easy review.

## Class Reference

### `StatisticsVisualizer`

#### Constructor
```python
StatisticsVisualizer(stats_dir: str = None, output_dir: str = None)
```

**Parameters:**
- `stats_dir`: Directory containing statistics CSV files (default: statistics module directory)
- `output_dir`: Directory to save plots (default: `{stats_dir}/plots`)

#### Methods

##### `generate_all_plots()`
Generates all available visualizations.

```python
visualizer.generate_all_plots()
```

##### Individual Plot Methods

Generate specific plots:

```python
visualizer.plot_inference_times_comparison()   # Inference times side-by-side
visualizer.plot_device_vs_edge_distribution()  # Distribution comparison
visualizer.plot_layer_sizes()                  # Data transmission sizes
visualizer.plot_statistics_summary()           # Key metrics summary
visualizer.plot_cumulative_costs()             # Cumulative latency
visualizer.plot_offloading_metrics()           # Offloading cost analysis
visualizer.plot_latency_distribution()         # Network latency
visualizer.create_plot_index()                 # Generate HTML dashboard
```

##### `load_csv_data(filename: str) -> pd.DataFrame`
Loads a CSV file into a pandas DataFrame.

```python
df = visualizer.load_csv_data('device_inference_per_layer.csv')
```

## Color Scheme

The visualizer uses a consistent color scheme:

| Element | Color | Hex |
|---------|-------|-----|
| Device | Blue | #3498db |
| Edge | Red | #e74c3c |
| Transmission | Orange | #f39c12 |
| Total/Optimal | Green | #2ecc71 |

## Expected CSV Files

The visualizer expects the following statistics files:

**Required:**
- `device_inference_statistics.csv` - Device aggregate statistics
- `device_inference_per_layer.csv` - Device per-layer statistics
- `edge_inference_statistics.csv` - Edge aggregate statistics
- `edge_inference_per_layer.csv` - Edge per-layer statistics
- `layer_sizes_statistics.csv` - Layer size aggregate statistics
- `layer_sizes_per_layer.csv` - Layer size per-layer statistics

**Optional:**
- `offloading_metrics.csv` - Offloading cost analysis
- `latency_statistics.csv` - Network latency statistics

These files are generated by `generate_statistics.py` or manually using `StatisticsCollector`.

## Data Processing

### Unit Conversions

- **Time**: Converted to milliseconds (ms) for readability in plots (internally stored as seconds)
- **Data Size**: Converted to kilobytes (KB) for transmission visualization

### Statistical Aggregation

- **Min/Max**: Minimum and maximum values
- **Mean**: Average value
- **Median**: 50th percentile
- **Std Dev**: Standard deviation

## Integration with Statistics Module

Use together with `StatisticsCollector`:

```python
from src.server.statistics import StatisticsCollector, StatisticsVisualizer

# Collect statistics
collector = StatisticsCollector()
collector.analyze_inference_times()
collector.analyze_layer_sizes()
collector.save_statistics_csv()

# Generate visualizations
visualizer = StatisticsVisualizer()
visualizer.generate_all_plots()

# Open dashboard
import webbrowser
webbrowser.open('src/server/plots/index.html')
```

## Examples

### Example 1: Generate and View Plots
```python
from src.server.statistics import StatisticsVisualizer

visualizer = StatisticsVisualizer()
visualizer.generate_all_plots()
print(f"Plots saved to: {visualizer.output_dir}")
```

### Example 2: Generate Specific Plot
```python
visualizer = StatisticsVisualizer()
visualizer.plot_layer_sizes()
visualizer.create_plot_index()
```

### Example 3: Custom Directories
```python
visualizer = StatisticsVisualizer(
    stats_dir='/data/sciot/statistics',
    output_dir='/data/sciot/visualizations'
)
visualizer.generate_all_plots()
```

## Output Format

**Image Format**: PNG (300 DPI)
- High quality for presentations and publications
- Lossless compression
- Compatible with all platforms

**HTML Format**: Responsive design
- Mobile-friendly layout
- Automatic image scaling
- Easy navigation

## Performance Notes

- Plot generation is fast (< 5 seconds for all plots)
- Memory usage: ~100 MB
- PNG file sizes: 50-200 KB per plot
- HTML dashboard: < 10 KB

## Troubleshooting

### Missing CSV Files
If a CSV file is not found:
- Check that statistics were generated first
- Verify file paths are correct
- Run `generate_statistics.py` before visualizing

### Import Errors
Ensure matplotlib and pandas are installed:
```bash
pip install matplotlib pandas
```

### Plot Quality Issues
For higher quality plots, modify in code:
```python
visualizer.plot_layer_sizes()
# Edit the line: plt.savefig(..., dpi=600)  # for ultra-high quality
```

## Future Enhancements

Potential improvements:
- Interactive plots using Plotly
- Real-time visualization dashboard
- Comparative analysis across multiple runs
- Custom theme support
- Export to PDF/SVG formats
- 3D surface plots for layer comparisons
