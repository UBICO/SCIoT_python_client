# Analysis Tools Index

Complete analysis toolkit for SCIoT performance evaluation.

## Quick Navigation

### 🚀 Getting Started (5 minutes)
- [QUICKSTART.sh](QUICKSTART.sh) - Copy-paste commands to get started
- [SIMULATION_ANALYSIS_GUIDE.md](SIMULATION_ANALYSIS_GUIDE.md) - Step-by-step workflow

### 📊 Tools Documentation
1. **Simulation Tool** → [SIMULATION_RUNNER_README.md](SIMULATION_RUNNER_README.md)
   - How to run simulations with 9 predefined scenarios
   - Results folder structure and CSV format
   - Configuration options

2. **Analysis Tool** → [ANALYSIS_README.md](ANALYSIS_README.md)
   - How to use analyze_simulation.py
   - Output file descriptions
   - Interpreting results and plots

3. **Complete Guide** → [SIMULATION_ANALYSIS_GUIDE.md](SIMULATION_ANALYSIS_GUIDE.md)
   - 5-step workflow from simulation to insights
   - How to interpret each of the 7 plots
   - 5 detailed analysis examples with code
   - Troubleshooting guide

4. **Reference** → [TOOLS_SUMMARY.md](TOOLS_SUMMARY.md)
   - Quick reference for all commands
   - Integration patterns for CI/CD
   - File locations and performance metrics
   - Extension points for customization

### 💻 Tools & Examples
- [simulation_runner.py](simulation_runner.py) - Run automated simulations
- [analyze_simulation.py](analyze_simulation.py) - Generate plots and statistics
- [example_analysis.py](example_analysis.py) - 10 runnable examples

## Typical Workflow

```bash
# 1. Run simulations (~15 minutes)
python simulation_runner.py

# 2. Analyze results (~10 seconds)
python analyze_simulation.py simulated_results/simulation_YYYYMMDD_HHMMSS/

# 3. View plots and statistics
open simulated_results/simulation_YYYYMMDD_HHMMSS/analysis/

# 4. (Optional) Run custom analysis
python example_analysis.py
```

## Output Structure

```
simulated_results/
└── simulation_20251231_143022/
    ├── baseline_inference_results.csv
    ├── baseline_scenario_config.json
    ├── network_delay_20ms_inference_results.csv
    ├── ... (9 scenarios total)
    └── analysis/
        ├── 01_device_vs_edge_time.png
        ├── 02_total_inference_time.png
        ├── 03_throughput_comparison.png
        ├── 04_timing_distributions.png
        ├── 05_layer_statistics.png
        ├── 06_scenario_comparison_dashboard.png  ⭐
        ├── 07_summary_statistics.png
        └── summary_statistics.csv
```

## 9 Simulation Scenarios

| # | Scenario | Type | Duration | Clients | Parameters |
|---|----------|------|----------|---------|------------|
| 1 | baseline | Control | 30s | 1 | No delays |
| 2 | network_delay_20ms | Network | 30s | 1 | 20±5ms |
| 3 | network_delay_50ms | Network | 30s | 1 | 50±10ms |
| 4 | computation_delay_2ms | Computation | 30s | 1 | 2±0.5ms |
| 5 | computation_delay_5ms | Computation | 30s | 1 | 5±1ms |
| 6 | mobile_realistic | Combined | 60s | 1 | Both delays |
| 7 | unstable_network | Variance | 45s | 1 | High variance |
| 8 | multi_client_baseline | Multi-client | 45s | 3 | No delays |
| 9 | multi_client_network | Multi-client | 60s | 3 | Network delay |

## Plot Overview

### 01: Device vs Edge Time
- Shows execution time split between device and edge
- Line plot of first 50 inferences per scenario
- **Use for:** Understanding workload partitioning

### 02: Total Inference Time
- Average total time per scenario with error bars
- Bar chart comparing all scenarios
- **Use for:** Overall performance ranking

### 03: Throughput Comparison
- Inferences per second per scenario
- Color-coded by simulation duration
- **Use for:** Responsiveness metrics

### 04: Timing Distributions
- Boxplots of execution time distributions
- Shows variance and outliers
- **Use for:** Consistency analysis

### 05: Layer Statistics
- Device vs edge layer count comparison
- Shows model partitioning strategy
- **Use for:** Understanding split decisions

### 06: Scenario Dashboard ⭐
- 9-metric comprehensive overview
- All key metrics in one view
- **Use for:** Quick overview and presentation

### 07: Summary Statistics
- Table of all metrics
- Mean ± std dev for each metric
- **Use for:** Detailed comparison and reporting

## Key Metrics

### Per-Inference
- `avg_device_time` - Average device execution time (seconds)
- `avg_edge_time` - Average edge execution time (seconds)
- `num_device_layers` - Layers executed on device
- `num_edge_layers` - Layers executed on edge

### Scenario-Level
- `total_time = device_time + edge_time`
- `throughput = count / duration`
- `variance = std_dev of timing`

## Analysis Capabilities

✓ Multi-scenario batch analysis
✓ Statistical distributions (boxplots)
✓ Variance and outlier detection
✓ Performance ranking
✓ Delay impact quantification
✓ Multi-client analysis
✓ Layer distribution analysis
✓ Custom metric export

## Integration Examples

### Compare Baseline vs Optimized
```bash
# Run baseline
python simulation_runner.py  # baseline_20251231_143022

# Make optimizations...

# Run optimized version
python simulation_runner.py  # baseline_20251231_144000

# Compare results
python analyze_simulation.py simulated_results/simulation_20251231_143022
python analyze_simulation.py simulated_results/simulation_20251231_144000
```

### CI/CD Integration
```yaml
- name: Run Performance Simulations
  run: python simulation_runner.py

- name: Analyze Results
  run: python analyze_simulation.py simulated_results/simulation_*/

- name: Upload Analysis
  uses: actions/upload-artifact@v2
  with:
    name: performance-analysis
    path: simulated_results/*/analysis/
```

### Custom Analysis Script
```python
from analyze_simulation import SimulationAnalyzer

analyzer = SimulationAnalyzer("simulated_results/simulation_20251231_143022")

# Access data
baseline = analyzer.data["baseline"]
network = analyzer.data["network_delay_20ms"]

# Custom analysis
print(f"Network delay impact: {(network['avg_device_time'].mean() - baseline['avg_device_time'].mean()) * 1000:.2f}ms")
```

## Documentation Map

```
User wants to...                          See...
─────────────────────────────────────────────────────────────────────
Get started in 5 minutes                  QUICKSTART.sh
Understand the complete workflow          SIMULATION_ANALYSIS_GUIDE.md
Run simulations                           SIMULATION_RUNNER_README.md
Use the analysis tool                     ANALYSIS_README.md
Interpret the plots                       SIMULATION_ANALYSIS_GUIDE.md (section: Understanding Plots)
Understand all metrics                    ANALYSIS_README.md (section: CSV Format)
Write custom analysis code                example_analysis.py
Extend the tool with new plots            ANALYSIS_README.md (section: Extending)
Integrate into CI/CD                      TOOLS_SUMMARY.md (section: Integration)
Quick reference                           TOOLS_SUMMARY.md
See code examples                         example_analysis.py (10 examples)
Troubleshoot issues                       SIMULATION_ANALYSIS_GUIDE.md (section: Troubleshooting)
```

## File Locations

| Component | Location | Lines |
|-----------|----------|-------|
| Analysis Tool | analyze_simulation.py | 370 |
| Example Code | example_analysis.py | 290 |
| Simulation Tool | simulation_runner.py | 567 |
| Main Guide | SIMULATION_ANALYSIS_GUIDE.md | 374 |
| Analysis Docs | ANALYSIS_README.md | 218 |
| Simulation Docs | SIMULATION_RUNNER_README.md | 152 |
| Reference | TOOLS_SUMMARY.md | 297 |
| Quick Start | QUICKSTART.sh | 40 |

## Dependencies

### Required
- Python 3.11+
- pandas >= 1.3.0
- matplotlib >= 3.4.0

### Optional
- seaborn >= 0.11.0 (better plot styling)

### Install
```bash
pip install pandas matplotlib seaborn
```

## Performance

| Operation | Duration |
|-----------|----------|
| Run all 9 scenarios | ~15 minutes |
| Generate all plots | ~10 seconds |
| Load simulation results | <100ms |
| Generate single plot | <2 seconds |

## Support & Help

1. **Quick questions?** → Check [TOOLS_SUMMARY.md](TOOLS_SUMMARY.md)
2. **Can't interpret plot?** → See [SIMULATION_ANALYSIS_GUIDE.md](SIMULATION_ANALYSIS_GUIDE.md)
3. **Want example code?** → Run [example_analysis.py](example_analysis.py)
4. **Tool not working?** → See troubleshooting in [ANALYSIS_README.md](ANALYSIS_README.md)
5. **Want to extend?** → See customization in [TOOLS_SUMMARY.md](TOOLS_SUMMARY.md)

## Last Updated
- **Date:** December 31, 2025
- **Status:** ✅ Complete and tested
- **Version:** 1.0
- **Test Data:** Available (simulation_20251231_155838)

---

**Ready to analyze performance?** → See [QUICKSTART.sh](QUICKSTART.sh)
