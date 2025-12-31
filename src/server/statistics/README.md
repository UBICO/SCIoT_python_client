# Statistics Module

The Statistics Module collects and analyzes performance metrics from the SCIoT system, including inference times, latencies, and data transmission sizes.

## Generated Statistics Files

### Inference Time Statistics

1. **device_inference_statistics.csv**
   - Aggregate statistics for all device inference times
   - Contains: count, min, max, mean, median, std dev, total

2. **device_inference_per_layer.csv**
   - Per-layer inference times on device
   - Shows execution time for each neural network layer

3. **edge_inference_statistics.csv**
   - Aggregate statistics for all edge inference times
   - Contains: count, min, max, mean, median, std dev, total

4. **edge_inference_per_layer.csv**
   - Per-layer inference times on edge server
   - Shows execution time for each remaining layer

### Data Transmission Statistics

5. **layer_sizes_statistics.csv**
   - Aggregate statistics for layer output data sizes
   - Contains: count, min, max, mean, median, std dev, total (in bytes)

6. **layer_sizes_per_layer.csv**
   - Per-layer data transmission sizes
   - Shows output size for each layer (affects network transmission time)

### Network Performance Statistics

7. **latency_statistics.csv** (if evaluations CSV is provided)
   - Aggregate latency measurements
   - Contains: count, min, max, mean, median, std dev, total

### Offloading Optimization Metrics

8. **offloading_metrics.csv** (if evaluations CSV is provided)
   - Performance metrics for each possible offloading layer
   - Columns:
     - `layer`: Offloading point (split layer)
     - `device_cost`: Time to run layers 0 to this layer on device
     - `transmission_cost`: Time to transmit intermediate results
     - `edge_cost`: Time to run remaining layers on edge
     - `total_latency`: Sum of all costs (target for optimization)

## Usage

### Generate Statistics Automatically

```bash
# From repository root
python src/server/statistics/generate_statistics.py
```

### With Custom Paths

```bash
python src/server/statistics/generate_statistics.py \
  --device-times /path/to/device_times.json \
  --edge-times /path/to/edge_times.json \
  --layer-sizes /path/to/layer_sizes.json \
  --evaluations /path/to/evaluations.csv \
  --output-dir /path/to/output
```

### Programmatic Usage

```python
from server.statistics import StatisticsCollector
from server.commons import OffloadingDataFiles

# Create collector
collector = StatisticsCollector()

# Generate comprehensive report
collector.generate_comprehensive_report(
    device_inference_file=OffloadingDataFiles.data_file_path_device,
    edge_inference_file=OffloadingDataFiles.data_file_path_edge,
    layer_sizes_file=OffloadingDataFiles.data_file_path_sizes
)
```

## Statistics Metrics

Each statistics file includes the following computed metrics:

- **Count**: Number of samples
- **Minimum**: Smallest value
- **Maximum**: Largest value
- **Mean**: Average value
- **Median**: Middle value (50th percentile)
- **Std Dev**: Standard deviation (measure of spread)
- **Total**: Sum of all values

## Interpretation

### Device vs Edge Performance
Compare `device_inference_statistics.csv` with `edge_inference_statistics.csv` to understand:
- Is edge faster for later layers?
- What is the speedup factor?
- Where is the crossover point?

### Offloading Decision
Use `offloading_metrics.csv` to identify the optimal split point:
- Minimum `total_latency` indicates the best offloading layer
- Consider network conditions (avg_speed affects `transmission_cost`)
- Account for variability in latencies (std dev in latency_statistics.csv)

### Network Impact
Analyze `layer_sizes_statistics.csv` to understand:
- Which layers produce large output sizes?
- How much data must be transmitted for each split point?
- Is transmission time dominating total latency?

## Output Directory

By default, statistics are saved to `/src/server/` alongside other data files:
- Statistics CSV files
- statistics_summary.txt (index of generated files)

## Integration with Evaluations

If you have an `evaluations.csv` file from test runs, the system can:
1. Extract actual latency measurements
2. Calculate average network speeds
3. Generate realistic offloading metrics based on observed data
4. Identify performance patterns and anomalies
