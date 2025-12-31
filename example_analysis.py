#!/usr/bin/env python3
"""
Example: Using analyze_simulation.py as a Library

This script shows how to use the SimulationAnalyzer class programmatically
to perform custom analysis on simulation results.
"""

import pandas as pd
from pathlib import Path
from analyze_simulation import SimulationAnalyzer


# Example 1: Generate all plots for a simulation
print("=" * 80)
print("EXAMPLE 1: Generate All Plots")
print("=" * 80)

analyzer = SimulationAnalyzer("simulated_results/simulation_20251231_155838")
analyzer.analyze_all()


# Example 2: Access individual scenario data
print("\n" + "=" * 80)
print("EXAMPLE 2: Access Scenario Data")
print("=" * 80)

for scenario_name, df in analyzer.data.items():
    print(f"\n{scenario_name}:")
    print(f"  - Inferences: {len(df)}")
    print(f"  - Device time (avg): {df['avg_device_time'].mean() * 1000:.2f}ms")
    print(f"  - Edge time (avg): {df['avg_edge_time'].mean() * 1000:.2f}ms")


# Example 3: Compare two scenarios
print("\n" + "=" * 80)
print("EXAMPLE 3: Compare Two Scenarios")
print("=" * 80)

baseline = analyzer.data["baseline"]
network = analyzer.data["network_delay_20ms"]

baseline_time = (baseline["avg_device_time"] + baseline["avg_edge_time"]).mean() * 1000
network_time = (network["avg_device_time"] + network["avg_edge_time"]).mean() * 1000
impact = ((network_time - baseline_time) / baseline_time) * 100

print(f"Baseline total time: {baseline_time:.2f}ms")
print(f"Network delay impact: +{impact:.1f}%")
print(f"Actual delay added: {network_time - baseline_time:.2f}ms")


# Example 4: Multi-client analysis
print("\n" + "=" * 80)
print("EXAMPLE 4: Multi-Client Analysis")
print("=" * 80)

single = analyzer.data["multi_client_baseline"]
duration = analyzer.configs["multi_client_baseline"]["duration_seconds"]
num_clients = analyzer.configs["multi_client_baseline"]["num_clients"]

throughput = len(single) / duration
throughput_per_client = throughput / num_clients
avg_time = (single["avg_device_time"] + single["avg_edge_time"]).mean() * 1000

print(f"Scenario: multi_client_baseline")
print(f"  - Duration: {duration}s")
print(f"  - Clients: {num_clients}")
print(f"  - Total inferences: {len(single)}")
print(f"  - Total throughput: {throughput:.2f} inferences/sec")
print(f"  - Per-client throughput: {throughput_per_client:.2f} inferences/sec")
print(f"  - Avg inference time: {avg_time:.2f}ms")


# Example 5: Statistical analysis
print("\n" + "=" * 80)
print("EXAMPLE 5: Statistical Analysis per Scenario")
print("=" * 80)

for scenario in sorted(analyzer.data.keys()):
    df = analyzer.data[scenario]
    
    device_time = df["avg_device_time"] * 1000
    edge_time = df["avg_edge_time"] * 1000
    total_time = device_time + edge_time
    
    print(f"\n{scenario}:")
    print(f"  Device time:  {device_time.mean():6.2f} ± {device_time.std():5.2f} ms "
          f"(min: {device_time.min():5.2f}, max: {device_time.max():5.2f})")
    print(f"  Edge time:    {edge_time.mean():6.2f} ± {edge_time.std():5.2f} ms "
          f"(min: {edge_time.min():5.2f}, max: {edge_time.max():5.2f})")
    print(f"  Total time:   {total_time.mean():6.2f} ± {total_time.std():5.2f} ms "
          f"(min: {total_time.min():5.2f}, max: {total_time.max():5.2f})")


# Example 6: Layer distribution analysis
print("\n" + "=" * 80)
print("EXAMPLE 6: Layer Distribution")
print("=" * 80)

for scenario in sorted(analyzer.data.keys()):
    df = analyzer.data[scenario]
    
    avg_device_layers = df["num_device_layers"].mean()
    avg_edge_layers = df["num_edge_layers"].mean()
    total_layers = avg_device_layers + avg_edge_layers
    device_pct = (avg_device_layers / total_layers * 100) if total_layers > 0 else 0
    
    print(f"{scenario:25} | Device: {avg_device_layers:4.1f} ({device_pct:5.1f}%) | Edge: {avg_edge_layers:4.1f}")


# Example 7: Identify outliers
print("\n" + "=" * 80)
print("EXAMPLE 7: Outlier Detection")
print("=" * 80)

for scenario in ["baseline", "unstable_network"]:
    if scenario not in analyzer.data:
        continue
    
    df = analyzer.data[scenario]
    total_time = df["avg_device_time"] + df["avg_edge_time"]
    
    mean = total_time.mean()
    std = total_time.std()
    threshold = mean + 2 * std
    
    outliers = df[total_time > threshold]
    pct = len(outliers) / len(df) * 100 if len(df) > 0 else 0
    
    print(f"\n{scenario}:")
    print(f"  Mean total time: {mean * 1000:.2f}ms")
    print(f"  Std dev: {std * 1000:.2f}ms")
    print(f"  Outlier threshold (mean + 2σ): {threshold * 1000:.2f}ms")
    print(f"  Outliers: {len(outliers)} / {len(df)} ({pct:.1f}%)")
    
    if len(outliers) > 0:
        print(f"  Outlier times: {[f'{t*1000:.2f}ms' for t in outliers['avg_device_time'] + outliers['avg_edge_time']][:3]}")


# Example 8: Export custom analysis
print("\n" + "=" * 80)
print("EXAMPLE 8: Export Custom Analysis to CSV")
print("=" * 80)

custom_data = []

for scenario in sorted(analyzer.data.keys()):
    df = analyzer.data[scenario]
    config = analyzer.configs[scenario]
    
    device_time = df["avg_device_time"] * 1000
    edge_time = df["avg_edge_time"] * 1000
    total_time = device_time + edge_time
    
    custom_data.append({
        "scenario": scenario,
        "num_inferences": len(df),
        "device_avg_ms": device_time.mean(),
        "device_std_ms": device_time.std(),
        "edge_avg_ms": edge_time.mean(),
        "edge_std_ms": edge_time.std(),
        "total_avg_ms": total_time.mean(),
        "total_std_ms": total_time.std(),
        "throughput": len(df) / config.get("duration_seconds", 30),
        "num_clients": config.get("num_clients", 1),
        "computation_delay": config.get("computation_delay", {}).get("mean", 0),
        "network_delay": config.get("network_delay", {}).get("mean", 0),
    })

custom_df = pd.DataFrame(custom_data)
output_path = analyzer.output_dir / "custom_analysis.csv"
custom_df.to_csv(output_path, index=False)

print(f"✅ Exported custom analysis to: {output_path}")
print("\nCustom analysis data:")
print(custom_df.to_string())


# Example 9: Performance ranking
print("\n" + "=" * 80)
print("EXAMPLE 9: Performance Ranking")
print("=" * 80)

ranking_data = []

for scenario in analyzer.data.keys():
    df = analyzer.data[scenario]
    total_time = (df["avg_device_time"] + df["avg_edge_time"]).mean() * 1000
    throughput = len(df) / analyzer.configs[scenario].get("duration_seconds", 30)
    
    ranking_data.append({
        "scenario": scenario,
        "inference_time_ms": total_time,
        "throughput": throughput,
    })

# Sort by inference time
ranking_df = pd.DataFrame(ranking_data).sort_values("inference_time_ms")

print("\nScenarios ranked by inference time (fastest to slowest):")
for idx, (_, row) in enumerate(ranking_df.iterrows(), 1):
    print(f"{idx}. {row['scenario']:25} - {row['inference_time_ms']:6.2f}ms ({row['throughput']:.2f} inf/sec)")


# Example 10: Delay impact quantification
print("\n" + "=" * 80)
print("EXAMPLE 10: Quantify Delay Impact")
print("=" * 80)

baseline_total = (analyzer.data["baseline"]["avg_device_time"] + 
                  analyzer.data["baseline"]["avg_edge_time"]).mean() * 1000

print(f"Baseline inference time: {baseline_total:.2f}ms\n")

scenarios_with_delays = [
    ("network_delay_20ms", "Network delay 20ms"),
    ("network_delay_50ms", "Network delay 50ms"),
    ("computation_delay_2ms", "Computation delay 2ms"),
    ("computation_delay_5ms", "Computation delay 5ms"),
    ("unstable_network", "Unstable network"),
]

for scenario, label in scenarios_with_delays:
    if scenario not in analyzer.data:
        continue
    
    scenario_total = (analyzer.data[scenario]["avg_device_time"] + 
                     analyzer.data[scenario]["avg_edge_time"]).mean() * 1000
    
    absolute_impact = scenario_total - baseline_total
    relative_impact = (absolute_impact / baseline_total) * 100
    
    print(f"{label:25} | {absolute_impact:+7.2f}ms ({relative_impact:+6.1f}%)")


print("\n" + "=" * 80)
print("✅ All examples completed!")
print("=" * 80)
