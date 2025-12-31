# Simulation Runner

The simulation runner is a tool for automated performance testing of the SCIoT system under various delay configurations.

## Overview

The runner executes multiple simulation scenarios sequentially, each with different network and computation delay characteristics. For each scenario, it:
- Starts the server with configured delays
- Launches one or more clients
- Records each inference as a separate row in scenario-specific CSV files
- Saves detailed timing statistics and configurations for all scenarios in a single timestamped folder

## Usage

### Run All Scenarios

```bash
python simulation_runner.py
```

This will run all 9 predefined scenarios sequentially.

### Scenarios

1. **baseline** - No delays (30s)
2. **network_delay_20ms** - Gaussian 20±5ms network delay (30s)
3. **network_delay_50ms** - Gaussian 50±10ms network delay (30s)
4. **computation_delay_2ms** - Gaussian 2±0.5ms computation delay (30s)
5. **computation_delay_5ms** - Gaussian 5±1ms computation delay (30s)
6. **mobile_realistic** - Both network (30±8ms) and computation (3±1ms) delays (60s)
7. **unstable_network** - High variance network delay 40±20ms (45s)
8. **multi_client_baseline** - 3 concurrent clients, no delays (45s)
9. **multi_client_network** - 3 concurrent clients with 25±7ms network delay (60s)

## Results Structure

All scenario results are collected in a single timestamped folder:

```
simulated_results/
└── simulation_20251231_143022/
    ├── baseline_inference_results.csv
    ├── baseline_scenario_config.json
    ├── network_delay_20ms_inference_results.csv
    ├── network_delay_20ms_scenario_config.json
    ├── computation_delay_2ms_inference_results.csv
    ├── computation_delay_2ms_scenario_config.json
    └── ... (one pair per scenario)
```

### CSV Format

Each `*_inference_results.csv` file contains one row per inference with columns:

- `inference_id` - Sequential ID (1, 2, 3, ...)
- `timestamp` - ISO format timestamp
- `avg_device_time` - Average device layer execution time (seconds)
- `min_device_time` - Minimum device layer execution time
- `max_device_time` - Maximum device layer execution time
- `avg_edge_time` - Average edge layer execution time (seconds)
- `min_edge_time` - Minimum edge layer execution time
- `max_edge_time` - Maximum edge layer execution time
- `num_device_layers` - Number of layers executed on device
- `num_edge_layers` - Number of layers executed on edge

### Scenario Config

Each scenario configuration is saved as `scenario_name_scenario_config.json` in the main results folder:

```json
{
  "name": "baseline",
  "computation_delay": {
    "enabled": false,
    "mean": 0.0,
    "std_dev": 0.0
  },
  "network_delay": {
    "enabled": false,
    "mean": 0.0,
    "std_dev": 0.0
  },
  "duration_seconds": 30,
  "num_clients": 1
}
```

## Analysis

After running simulations, you can use the generated CSV files for analysis:

```python
import pandas as pd
from pathlib import Path

# Find the latest simulation folder
results_dir = Path('simulated_results')
latest_sim = max(results_dir.glob('simulation_*'), key=lambda p: p.stat().st_mtime)

# Load results from a specific scenario
df = pd.read_csv(latest_sim / 'baseline_inference_results.csv')

# Calculate statistics
print(f"Total inferences: {len(df)}")
print(f"Avg device time: {df['avg_device_time'].mean():.3f}s")
print(f"Avg edge time: {df['avg_edge_time'].mean():.3f}s")
print(f"Throughput: {len(df)/30:.2f} inferences/sec")

# Compare scenarios
baseline_df = pd.read_csv(latest_sim / 'baseline_inference_results.csv')
network_df = pd.read_csv(latest_sim / 'network_delay_20ms_inference_results.csv')

print(f"Baseline avg total: {(baseline_df['avg_device_time'] + baseline_df['avg_edge_time']).mean():.3f}s")
print(f"Network delay avg total: {(network_df['avg_device_time'] + network_df['avg_edge_time']).mean():.3f}s")
```

## Requirements

- Server and client must be properly configured
- Python dependencies installed (`pip install -r requirements.txt`)
- Server models must be available in `src/server/models/`

## Interrupting

Press `Ctrl+C` to gracefully stop the simulation. The runner will:
- Stop all clients
- Stop the server
- Restore original configurations
- Close any open CSV files

## Troubleshooting

If simulations fail:
1. Check that server starts successfully: `python -m src.server.communication.http_server`
2. Check that client can connect: `python server_client_light/client/http_client.py`
3. Review logs in the scenario folder
4. Ensure all dependencies are installed

## Customization

To add custom scenarios, edit `SIMULATION_SCENARIOS` in `simulation_runner.py`:

```python
SIMULATION_SCENARIOS = [
    # ... existing scenarios ...
    {
        'name': 'custom_scenario',
        'computation_delay': {
            'enabled': True,
            'mean': 0.010,  # 10ms
            'std_dev': 0.002  # ±2ms
        },
        'network_delay': {
            'enabled': True,
            'mean': 0.015,  # 15ms
            'std_dev': 0.005  # ±5ms
        },
        'duration_seconds': 60,
        'num_clients': 2
    }
]
```
