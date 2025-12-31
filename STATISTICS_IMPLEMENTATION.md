# Statistics Module Implementation Summary

## Overview

A comprehensive statistics collection and analysis module has been implemented for the SCIoT project to gather and generate performance metrics.

## Key Features

✅ **Inference Time Analysis**
- Device layer-by-layer inference times
- Edge layer-by-layer inference times
- Aggregate statistics (min, max, mean, median, std dev, total)

✅ **Data Transmission Analysis**
- Layer output sizes for each layer
- Statistics on data transmission requirements
- Impact on network bandwidth

✅ **Network Performance Metrics**
- Latency measurements from evaluations
- Network speed calculations
- Transmission cost estimation

✅ **Offloading Optimization**
- Calculate cost for each possible split point
- Device cost: time running on device
- Transmission cost: time to send intermediate results
- Edge cost: time running remaining layers on edge
- Total latency: optimization target

✅ **Multiple Output Formats**
- CSV files for easy import into analysis tools
- Summary report with file index
- Separate files for different metric categories

## Files Generated

### Statistics Files (in `/src/server/`)

1. **device_inference_statistics.csv** - Aggregate device inference times
2. **device_inference_per_layer.csv** - Per-layer device times
3. **edge_inference_statistics.csv** - Aggregate edge inference times
4. **edge_inference_per_layer.csv** - Per-layer edge times
5. **layer_sizes_statistics.csv** - Aggregate layer size statistics
6. **layer_sizes_per_layer.csv** - Per-layer data sizes
7. **latency_statistics.csv** - Network latency metrics (optional)
8. **offloading_metrics.csv** - Offloading cost analysis (optional)
9. **statistics_summary.txt** - Index of all generated files

## Module Components

### StatisticsCollector Class
Main class for statistics generation with methods:

- `analyze_times()` - Compute statistics for any list of values
- `analyze_inference_times()` - Analyze device/edge inference time JSON files
- `analyze_layer_sizes()` - Analyze layer size JSON file
- `calculate_offloading_metrics()` - Compute costs for each split point
- `save_statistics_csv()` - Save aggregate statistics
- `save_layer_statistics_csv()` - Save per-layer data
- `save_offloading_metrics_csv()` - Save offloading analysis
- `save_latency_statistics_csv()` - Save latency metrics
- `generate_comprehensive_report()` - Generate all statistics files
- `summary_report()` - Create index of generated files

### StatisticsResult Dataclass
Container for computed statistics with fields:
- metric_name, count, min_value, max_value, mean_value, median_value, std_dev, sum_value

## Usage Examples

### Command Line
```bash
# Basic usage with default files
python src/server/statistics/generate_statistics.py

# With custom paths
python src/server/statistics/generate_statistics.py \
  --device-times custom_device.json \
  --edge-times custom_edge.json \
  --layer-sizes custom_sizes.json \
  --evaluations evaluations.csv \
  --output-dir /output/path
```

### Programmatic Usage
```python
from server.statistics import StatisticsCollector

collector = StatisticsCollector()
collector.generate_comprehensive_report(
    device_inference_file='device_inference_times.json',
    edge_inference_file='edge_inference_times.json',
    layer_sizes_file='layer_sizes.json',
    latencies=[0.1, 0.15, 0.12, ...],
    avg_speeds=[1000000, 1200000, ...]  # bytes/sec
)
```

## Statistics Available

Each metric includes:
- **Count**: Sample size
- **Minimum**: Smallest observed value
- **Maximum**: Largest observed value
- **Mean**: Average value
- **Median**: Middle value (50th percentile)
- **Std Dev**: Standard deviation (measure of variability)
- **Total**: Sum of all values

## Practical Applications

1. **Performance Analysis**
   - Identify slow layers
   - Compare device vs edge performance
   - Find performance bottlenecks

2. **Optimization**
   - Determine optimal offloading point
   - Optimize for latency vs bandwidth tradeoff
   - Account for variable network conditions

3. **Reporting**
   - Generate performance reports
   - Create visualizations
   - Export to analysis tools

4. **Monitoring**
   - Track performance over time
   - Detect degradation
   - Validate optimization changes

## Integration Points

The statistics module integrates with:
- **RequestHandler**: Can save statistics from inference results
- **Edge Server**: Tracks execution times during inference
- **Evaluations CSV**: Extracts real network measurements
- **Model Manager**: Uses inference time data

## Future Enhancements

Potential additions:
- Real-time statistics collection during operation
- Confidence intervals for measurements
- Anomaly detection
- Performance forecasting
- Distribution visualization
- Correlation analysis between metrics
