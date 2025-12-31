# Analysis Tools Summary

## Overview

The SCIoT project now includes three comprehensive analysis tools:

1. **simulation_runner.py** - Run automated performance simulations
2. **analyze_simulation.py** - Generate plots and statistics from results
3. **example_analysis.py** - Example code for custom analysis

## Quick Reference

### Run Simulations
```bash
python simulation_runner.py
# Creates: simulated_results/simulation_YYYYMMDD_HHMMSS/
```

### Analyze Results
```bash
python analyze_simulation.py simulated_results/simulation_YYYYMMDD_HHMMSS
# Creates: simulated_results/simulation_YYYYMMDD_HHMMSS/analysis/
```

### Custom Analysis
```bash
python example_analysis.py
# Shows 10 examples of programmatic analysis
```

## Output Files

### CSV Files (in simulation folder)
- `*_inference_results.csv` - Raw inference data per scenario (one row per inference)
- `*_scenario_config.json` - Configuration parameters per scenario

### Analysis Plots (in analysis/ subfolder)
- `01_device_vs_edge_time.png` - Time distribution across 50 inferences
- `02_total_inference_time.png` - Average total time per scenario
- `03_throughput_comparison.png` - Inferences per second per scenario
- `04_timing_distributions.png` - Boxplots of execution time distributions
- `05_layer_statistics.png` - Device vs edge layer count per scenario
- `06_scenario_comparison_dashboard.png` - 9-metric comprehensive dashboard
- `07_summary_statistics.png` - Table view of all metrics
- `summary_statistics.csv` - Exportable summary data

## Scenarios Included

1. **baseline** - No delays (baseline performance)
2. **network_delay_20ms** - 20ms network latency (Gaussian 20±5ms)
3. **network_delay_50ms** - 50ms network latency (Gaussian 50±10ms)
4. **computation_delay_2ms** - 2ms computation delay (Gaussian 2±0.5ms)
5. **computation_delay_5ms** - 5ms computation delay (Gaussian 5±1ms)
6. **mobile_realistic** - Realistic combined delays (network 30±8ms, computation 3±1ms)
7. **unstable_network** - High-variance network (40±20ms)
8. **multi_client_baseline** - 3 concurrent clients, no delays
9. **multi_client_network** - 3 concurrent clients with 25±7ms network delay

## Key Metrics

### Per-Inference Metrics
- **avg_device_time** - Average device layer execution time (seconds)
- **min_device_time** - Minimum device layer execution time
- **max_device_time** - Maximum device layer execution time
- **avg_edge_time** - Average edge server execution time (seconds)
- **min_edge_time** - Minimum edge server execution time
- **max_edge_time** - Maximum edge server execution time
- **num_device_layers** - Number of layers executed on device
- **num_edge_layers** - Number of layers executed on edge

### Derived Metrics
- **total_time** = avg_device_time + avg_edge_time
- **throughput** = total_inferences / duration_seconds
- **variance** = std_dev of timing across inferences

## Integration Points

### Run in CI/CD Pipeline
```yaml
# GitHub Actions example
- name: Run Simulations
  run: python simulation_runner.py
  
- name: Analyze Results
  run: python analyze_simulation.py simulated_results/simulation_*/
  
- name: Upload Artifacts
  uses: actions/upload-artifact@v2
  with:
    name: simulation-results
    path: simulated_results/*/analysis/
```

### Monitor Over Time
```bash
# Create timestamped results directory
mkdir -p results_over_time
cd results_over_time
python ../simulation_runner.py
mv simulated_results/simulation_* latest_run
python ../analyze_simulation.py latest_run
# Compare with previous runs
```

### Custom Analysis Script
```python
from analyze_simulation import SimulationAnalyzer

analyzer = SimulationAnalyzer("results_dir")

# Access raw data
for scenario, df in analyzer.data.items():
    print(f"{scenario}: {len(df)} inferences")

# Generate plots
analyzer.analyze_all()

# Or individual plots
analyzer.plot_total_inference_time()
analyzer.plot_throughput_comparison()
```

## Dependencies

### Required
- Python 3.11+
- pandas >= 1.3.0
- matplotlib >= 3.4.0

### Optional
- seaborn >= 0.11.0 (improved plot styling)

### Installation
```bash
pip install pandas matplotlib seaborn
```

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Run all 9 scenarios | ~15 minutes | Depends on server/client performance |
| Analyze results | ~10 seconds | Generates 7 PNG plots + CSV |
| Load 1000 inferences | <100ms | Single scenario analysis |
| Generate all plots | ~5 seconds | At 150 DPI quality |

## File Locations

```
SCIoT_python_client/
├── simulation_runner.py           # Main simulation orchestrator
├── analyze_simulation.py           # Analysis tool (CLI)
├── example_analysis.py             # Programmatic examples
├── SIMULATION_RUNNER_README.md     # Simulation documentation
├── ANALYSIS_README.md              # Analysis tool documentation
├── SIMULATION_ANALYSIS_GUIDE.md    # Complete workflow guide
└── simulated_results/
    └── simulation_20251231_143022/
        ├── baseline_inference_results.csv
        ├── baseline_scenario_config.json
        ├── network_delay_20ms_inference_results.csv
        ├── ... (one pair per scenario)
        └── analysis/
            ├── 01_device_vs_edge_time.png
            ├── 02_total_inference_time.png
            ├── ... (7 PNG plots total)
            └── summary_statistics.csv
```

## Usage Patterns

### Pattern 1: Baseline + Analysis
```bash
python simulation_runner.py
python analyze_simulation.py simulated_results/simulation_*/
```
**Use case:** Understand system performance characteristics

### Pattern 2: A/B Comparison
```bash
# Run baseline
python simulation_runner.py  # baseline_20251231_143022
# Make changes to code
python simulation_runner.py  # baseline_20251231_144000
# Compare results directory
```
**Use case:** Measure impact of optimizations

### Pattern 3: Automated Testing
```bash
# In CI/CD pipeline
python simulation_runner.py
python analyze_simulation.py simulated_results/simulation_*/
# Check summary_statistics.csv for regressions
```
**Use case:** Continuous performance monitoring

### Pattern 4: Custom Analysis
```bash
# Edit example_analysis.py or create custom script
from analyze_simulation import SimulationAnalyzer
analyzer = SimulationAnalyzer("simulated_results/simulation_20251231_143022")
# Your custom analysis here
```
**Use case:** Specific research questions or metrics

## Troubleshooting

### Issue: "No CSV files found"
```bash
# Verify simulation completed
ls simulated_results/simulation_*/
# Should show multiple CSV files like baseline_inference_results.csv
```

### Issue: Plots are empty or cut off
```bash
# Verify matplotlib backend
python -c "import matplotlib; print(matplotlib.get_backend())"
# Regenerate analysis
rm -rf simulated_results/simulation_*/analysis
python analyze_simulation.py simulated_results/simulation_*/
```

### Issue: Memory issues with large simulations
```bash
# Analyze subset of scenarios
# Edit analyze_simulation.py to load specific scenarios
# Or use custom script with manual DataFrame operations
```

## Extensions

### Adding Custom Scenarios
```python
# In simulation_runner.py, modify SIMULATION_SCENARIOS:
{
    'name': 'my_custom_scenario',
    'computation_delay': {'enabled': True, 'mean': 0.003, 'std_dev': 0.0005},
    'network_delay': {'enabled': True, 'mean': 0.015, 'std_dev': 0.003},
    'duration_seconds': 60,
    'num_clients': 2
}
```

### Adding Custom Plots
```python
# In analyze_simulation.py, add method to SimulationAnalyzer:
def plot_custom_metric(self):
    fig, ax = plt.subplots(figsize=(12, 6))
    # Your plot code here
    plt.savefig(self.output_dir / "08_custom_metric.png", dpi=150)
    plt.close()

# In analyze_all(), add: self.plot_custom_metric()
```

### Exporting to Different Formats
```python
# Convert summary CSV to Excel
import pandas as pd
df = pd.read_csv('simulated_results/simulation_*/analysis/summary_statistics.csv')
df.to_excel('summary.xlsx', index=False)

# Or JSON
df.to_json('summary.json', orient='records')
```

## References

- [SIMULATION_RUNNER_README.md](SIMULATION_RUNNER_README.md) - Detailed simulation documentation
- [ANALYSIS_README.md](ANALYSIS_README.md) - Detailed analysis tool documentation
- [SIMULATION_ANALYSIS_GUIDE.md](SIMULATION_ANALYSIS_GUIDE.md) - Complete workflow guide with examples
- [example_analysis.py](example_analysis.py) - 10 runnable examples of custom analysis

## Support

For questions or issues:
1. Check relevant README files above
2. Review example_analysis.py for similar use cases
3. Check existing plots for interpretation guidance
4. See SIMULATION_ANALYSIS_GUIDE.md troubleshooting section
