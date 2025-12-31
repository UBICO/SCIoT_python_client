# Complete Simulation and Analysis Workflow

This guide shows the complete workflow from running simulations to analyzing results.

## Quickstart (5 steps)

### 1. Run Simulations (~15 minutes)

```bash
python simulation_runner.py
```

This runs 9 scenarios and creates a folder like: `simulated_results/simulation_20251231_143022/`

**Output structure:**
```
simulated_results/simulation_20251231_143022/
├── baseline_inference_results.csv
├── baseline_scenario_config.json
├── network_delay_20ms_inference_results.csv
├── network_delay_20ms_scenario_config.json
├── ... (7 more scenarios)
```

### 2. Analyze Results (~10 seconds)

```bash
python analyze_simulation.py simulated_results/simulation_20251231_143022
```

This generates 7 plot PNGs and a CSV with summary statistics.

**Output structure:**
```
simulated_results/simulation_20251231_143022/analysis/
├── 01_device_vs_edge_time.png
├── 02_total_inference_time.png
├── 03_throughput_comparison.png
├── 04_timing_distributions.png
├── 05_layer_statistics.png
├── 06_scenario_comparison_dashboard.png
├── 07_summary_statistics.png
└── summary_statistics.csv
```

### 3. View Results

Open PNG files in your image viewer:
- Finder: `simulated_results/simulation_20251231_143022/analysis/`
- Or: `open simulated_results/simulation_20251231_143022/analysis/06_scenario_comparison_dashboard.png`

### 4. Compare Metrics

Open summary CSV in Excel or view in terminal:

```bash
cat simulated_results/simulation_20251231_143022/analysis/summary_statistics.csv
```

### 5. Interpret Results

See section **"Understanding Plots"** below.

---

## Understanding Plots

### 01_device_vs_edge_time.png
**What it shows:** How inference time is split between device and edge for each scenario

**How to read it:**
- X-axis: Inference number (first 50 shown)
- Y-axis: Time in milliseconds
- Blue line = Device time (mobile execution)
- Orange line = Edge time (server execution)

**What it means:**
- High device time = More work on phone, less server usage
- High edge time = More offloading to server
- Both high = Slow inference overall

**Example interpretation:**
```
Baseline: Both low (~0.1ms) = System is fast
Network delay 20ms: Still low for actual execution, but network adds latency
Computation delay 5ms: Device time jumps to ~5ms = Simulated slowdown visible
```

### 02_total_inference_time.png
**What it shows:** Average total time (device + edge) for each scenario

**How to read it:**
- Each bar = One scenario
- Height = Average time in milliseconds
- Error bars = Standard deviation (consistency)

**What it means:**
- Taller bars = Slower inference
- Bigger error bars = More variable/inconsistent performance
- Most important metric for user experience

**Example interpretation:**
```
Baseline: ~0.14ms (fast)
Network delay 50ms: ~0.03ms execution + network latency = overall slow
Computation delay 5ms: ~5ms (slowest) due to simulated phone slowness
Multi-client network: ~0.02ms (best execution, 3 clients together)
```

### 03_throughput_comparison.png
**What it shows:** How many inferences per second each scenario achieves

**How to read it:**
- Each bar = One scenario
- Height = Inferences per second
- Color = Simulation duration (green=30s, red=45-60s, blue=other)

**What it means:**
- Taller bars = More responsive system
- Lower throughput = System busy processing
- Useful for real-time applications

**Example interpretation:**
```
Baseline: 1.0 inferences/sec = 1 inference every second
Multi-client network: 2.13 inferences/sec = 3 clients running, higher throughput
Computation delay 5ms: 0.9 inferences/sec = Slower due to simulated delay
```

### 04_timing_distributions.png
**What it shows:** Distribution of execution times (boxplots)

**How to read it:**
- Box = middle 50% of data (1st to 3rd quartile)
- Line in box = median (50th percentile)
- Whiskers = full range (95% of data)
- Dots = outliers

**What it means:**
- Small boxes = Consistent performance
- Large boxes = Highly variable performance
- Outliers = occasional slow inferences

**Example interpretation:**
```
Baseline: Small boxes = very consistent (good)
Unstable network: Large boxes = inconsistent (network variance)
Computation delay: Shifted boxes = all slower but still consistent
```

### 05_layer_statistics.png
**What it shows:** How many model layers run on device vs edge

**How to read it:**
- Blue bars = Device layers
- Red bars = Edge layers
- Each scenario shows the split

**What it means:**
- More blue = More local execution
- More red = More offloading
- Sum of blue + red = total model depth (59 for FOMO 96x96)

**Example interpretation:**
```
Baseline: May have 20 device + 39 edge = Balanced split
Network delay: Might increase device layers (less worth offloading with high latency)
Computation delay: Might decrease device layers (slow phone, better to offload)
```

### 06_scenario_comparison_dashboard.png
**What it shows:** 9 different metrics in one comprehensive view

**The 9 panels (3x3 grid):**
1. **Avg Device Time** - Average device execution
2. **Avg Edge Time** - Average server execution
3. **Avg Total Time** - Device + Edge combined
4. **Device Time Variance** - Consistency of device execution
5. **Edge Time Variance** - Consistency of server execution
6. **Inference Count** - Total inferences run in scenario
7. **Min Device Time** - Fastest device execution
8. **Max Device Time** - Slowest device execution
9. **Device Layer Count** - Layers executed on device

**How to read it:**
- Compare bar heights across scenarios
- Look for patterns (e.g., all metrics worse in network delay?)
- Identify which scenarios are most affected by delays

**Quick scan tips:**
- Panels 1-3 (top row): Overall performance
- Panels 4-5 (middle row): Consistency/variance
- Panels 7-9 (bottom row): Extremes and layer distribution

### 07_summary_statistics.png
**What it shows:** Table of all metrics in one place

**The columns:**
- **Scenario**: Name of the test scenario
- **Inferences**: How many inferences ran
- **Device (ms)**: Average ± standard deviation of device time
- **Edge (ms)**: Average ± standard deviation of edge time
- **Total (ms)**: Average ± standard deviation of total time
- **Throughput**: Inferences per second
- **Clients**: Number of concurrent clients

**How to read it:**
- Read like a spreadsheet
- Compare values in same column across scenarios
- Focus on scenarios relevant to your use case

**Quick interpretation:**
```
Row format: "0.14 ± 0.14" means average 0.14ms with variation of ±0.14ms
Small variation (e.g., ± 0.01) = consistent
Large variation (e.g., ± 0.99) = inconsistent
```

---

## Detailed Analysis Examples

### Compare Baseline vs Network Delay

```bash
# View summary
cat simulated_results/simulation_20251231_143022/analysis/summary_statistics.csv

# Or use Python
import pandas as pd

baseline = pd.read_csv('simulated_results/simulation_20251231_143022/baseline_inference_results.csv')
network = pd.read_csv('simulated_results/simulation_20251231_143022/network_delay_20ms_inference_results.csv')

baseline_total = (baseline['avg_device_time'] + baseline['avg_edge_time']).mean() * 1000
network_total = (network['avg_device_time'] + network['avg_edge_time']).mean() * 1000

print(f"Impact of 20ms network delay: {network_total - baseline_total:.2f}ms slower")
```

### Compare Single vs Multi-Client

```python
import pandas as pd

single = pd.read_csv('simulated_results/simulation_20251231_143022/baseline_inference_results.csv')
multi = pd.read_csv('simulated_results/simulation_20251231_143022/multi_client_baseline_inference_results.csv')

print(f"Single client throughput: {len(single)/30:.2f} inferences/sec")
print(f"Multi client throughput: {len(multi)/45:.2f} inferences/sec")
print(f"Throughput per client: {(len(multi)/45)/3:.2f} inferences/sec")
```

### Measure Delay Impact

```python
import pandas as pd
import json

# Load baseline
baseline = pd.read_csv('simulated_results/simulation_20251231_143022/baseline_inference_results.csv')
baseline_time = (baseline['avg_device_time'] + baseline['avg_edge_time']).mean() * 1000

# Load all delays and compare
delays = {
    'baseline': ('simulated_results/simulation_20251231_143022/baseline_inference_results.csv', 0),
    'network_20ms': ('simulated_results/simulation_20251231_143022/network_delay_20ms_inference_results.csv', 20),
    'network_50ms': ('simulated_results/simulation_20251231_143022/network_delay_50ms_inference_results.csv', 50),
    'computation_2ms': ('simulated_results/simulation_20251231_143022/computation_delay_2ms_inference_results.csv', 2),
    'computation_5ms': ('simulated_results/simulation_20251231_143022/computation_delay_5ms_inference_results.csv', 5),
}

for name, (filepath, expected_delay) in delays.items():
    df = pd.read_csv(filepath)
    total_time = (df['avg_device_time'] + df['avg_edge_time']).mean() * 1000
    increase = total_time - baseline_time
    print(f"{name:20} | Expected: +{expected_delay:3}ms | Measured: +{increase:6.2f}ms")
```

---

## Common Questions

**Q: Why is throughput sometimes lower with faster execution times?**
A: Simulation duration varies (30-60 seconds). Multi-client scenarios run longer to gather more data.

**Q: Why do multi-client scenarios show lower per-client times?**
A: Multiple clients on device might run inference sequentially, reducing contention. Edge server parallelizes well.

**Q: Should I optimize for low variance or low total time?**
A: Depends on use case:
- Real-time (autonomous driving): Low total time critical
- Background processing: Can tolerate variance
- User-facing (voice assistant): Both matter

**Q: What do outliers in boxplots mean?**
A: One-off slow inferences. Could be OS scheduling, garbage collection, or network hiccup.

**Q: How do I reproduce a specific scenario?**
A: Edit `simulation_runner.py` and modify `SIMULATION_SCENARIOS` list with your custom parameters.

---

## Troubleshooting

### Analysis script fails: "No CSV files found"
- Verify simulation completed: `ls simulated_results/simulation_20251231_143022/`
- Should show: `baseline_inference_results.csv`, `network_delay_20ms_inference_results.csv`, etc.
- If missing, run: `python simulation_runner.py` again

### Plots look empty or corrupted
- Check matplotlib installed: `pip install matplotlib`
- Ensure no terminal was interrupted during analysis
- Try regenerating: `rm -rf simulated_results/simulation_20251231_143022/analysis && python analyze_simulation.py simulated_results/simulation_20251231_143022`

### "Permission denied" when saving
- Check directory permissions: `chmod -R u+w simulated_results/`
- Or use different output directory

### Results seem unrealistic
- Check server and clients running correctly during simulation
- Review simulation logs in terminal output
- Verify models are present and loaded correctly

---

## Next Steps

1. **Run baseline simulation**: Understand your system's baseline performance
2. **Test your specific scenario**: Add custom scenarios to `SIMULATION_SCENARIOS`
3. **Compare implementations**: Run before/after tests when optimizing
4. **Monitor production**: Use same analysis pipeline on production data
5. **Share results**: Include plots and summaries in project documentation

For more details, see:
- [SIMULATION_RUNNER_README.md](SIMULATION_RUNNER_README.md) - Simulation configuration
- [ANALYSIS_README.md](ANALYSIS_README.md) - Analysis tool API and customization
- [DELAY_SIMULATION.md](DELAY_SIMULATION.md) - Delay types and parameters
