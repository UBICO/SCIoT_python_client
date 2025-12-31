#!/usr/bin/env python3
"""
Simulation Results Analysis Tool

Analyzes simulation results from the simulation runner and generates comprehensive
graphs and plots for performance analysis.

Usage:
    python analyze_simulation.py simulated_results/simulation_YYYYMMDD_HHMMSS

The script generates:
- Device vs Edge execution time comparison
- Total inference time per scenario
- Throughput analysis
- Timing distribution boxplots
- Per-layer execution statistics
- Multi-client performance comparison
- Network/computation delay impact analysis
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime

# Try to import seaborn for better styling
try:
    import seaborn as sns
    sns.set_style("whitegrid")
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False


class SimulationAnalyzer:
    def __init__(self, results_dir: Path):
        """Initialize analyzer with results directory"""
        self.results_dir = Path(results_dir)
        if not self.results_dir.exists():
            raise ValueError(f"Results directory not found: {results_dir}")
        
        self.data = {}  # scenario_name -> DataFrame
        self.configs = {}  # scenario_name -> config dict
        self.output_dir = self.results_dir / "analysis"
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"📊 Analyzing simulation results from: {self.results_dir}")
        self._load_data()
    
    def _load_data(self):
        """Load all CSV files and configs from results directory"""
        csv_files = list(self.results_dir.glob("*_inference_results.csv"))
        
        if not csv_files:
            raise ValueError(f"No inference results CSV files found in {self.results_dir}")
        
        print(f"\n📁 Found {len(csv_files)} scenario results")
        
        for csv_file in sorted(csv_files):
            scenario_name = csv_file.stem.replace("_inference_results", "")
            
            # Load CSV
            try:
                df = pd.read_csv(csv_file)
                self.data[scenario_name] = df
                print(f"  ✓ {scenario_name}: {len(df)} inferences")
            except Exception as e:
                print(f"  ✗ Error loading {scenario_name}: {e}")
                continue
            
            # Load config
            config_file = self.results_dir / f"{scenario_name}_scenario_config.json"
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        self.configs[scenario_name] = json.load(f)
                except Exception as e:
                    print(f"  ⚠ Error loading config for {scenario_name}: {e}")
    
    def analyze_all(self):
        """Generate all analysis plots"""
        print("\n📈 Generating analysis plots...\n")
        
        self.plot_device_vs_edge_time()
        self.plot_total_inference_time()
        self.plot_throughput_comparison()
        self.plot_timing_distributions()
        self.plot_layer_statistics()
        self.plot_scenario_comparison()
        self.generate_summary_stats()
        
        print(f"\n✅ Analysis complete! Plots saved to: {self.output_dir}\n")
    
    def plot_device_vs_edge_time(self):
        """Compare device vs edge execution times"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle("Device vs Edge Execution Time Comparison", fontsize=16, fontweight='bold')
        
        scenarios = sorted(self.data.keys())
        
        for idx, ax in enumerate(axes.flat):
            if idx < len(scenarios):
                scenario = scenarios[idx]
                df = self.data[scenario]
                
                # Calculate averages per inference
                device_times = df['avg_device_time'] * 1000  # Convert to ms
                edge_times = df['avg_edge_time'] * 1000
                
                x = range(min(50, len(df)))  # Plot first 50 inferences
                
                ax.plot(x, device_times.iloc[:len(x)], label='Device', marker='o', linewidth=2, markersize=4)
                ax.plot(x, edge_times.iloc[:len(x)], label='Edge', marker='s', linewidth=2, markersize=4)
                
                ax.set_xlabel('Inference #')
                ax.set_ylabel('Time (ms)')
                ax.set_title(f"{scenario}")
                ax.legend()
                ax.grid(True, alpha=0.3)
            else:
                ax.set_visible(False)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "01_device_vs_edge_time.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Device vs Edge time comparison")
    
    def plot_total_inference_time(self):
        """Plot total (device + edge) inference time per scenario"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        scenarios = []
        avg_times = []
        std_times = []
        
        for scenario in sorted(self.data.keys()):
            df = self.data[scenario]
            total_time = (df['avg_device_time'] + df['avg_edge_time']) * 1000  # ms
            scenarios.append(scenario)
            avg_times.append(total_time.mean())
            std_times.append(total_time.std())
        
        x_pos = range(len(scenarios))
        ax.bar(x_pos, avg_times, yerr=std_times, capsize=5, alpha=0.7, color='steelblue')
        
        ax.set_xticks(x_pos)
        ax.set_xticklabels(scenarios, rotation=45, ha='right')
        ax.set_ylabel('Total Inference Time (ms)')
        ax.set_title('Average Total Inference Time per Scenario')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for i, (mean, std) in enumerate(zip(avg_times, std_times)):
            ax.text(i, mean + std + 1, f'{mean:.1f}ms', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "02_total_inference_time.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Total inference time comparison")
    
    def plot_throughput_comparison(self):
        """Plot throughput (inferences per second) for each scenario"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        scenarios = []
        throughputs = []
        durations = []
        
        for scenario in sorted(self.data.keys()):
            df = self.data[scenario]
            config = self.configs.get(scenario, {})
            duration = config.get('duration_seconds', 30)
            
            throughput = len(df) / duration
            scenarios.append(scenario)
            throughputs.append(throughput)
            durations.append(duration)
        
        colors = ['#2ecc71' if d == 30 else '#e74c3c' if d == 45 else '#3498db' for d in durations]
        x_pos = range(len(scenarios))
        ax.bar(x_pos, throughputs, alpha=0.7, color=colors)
        
        ax.set_xticks(x_pos)
        ax.set_xticklabels(scenarios, rotation=45, ha='right')
        ax.set_ylabel('Throughput (inferences/sec)')
        ax.set_title('Inference Throughput per Scenario')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels
        for i, (tp, dur) in enumerate(zip(throughputs, durations)):
            ax.text(i, tp + 0.1, f'{tp:.2f}', ha='center', va='bottom', fontsize=9)
        
        # Add legend for duration
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#2ecc71', alpha=0.7, label='30s duration'),
            Patch(facecolor='#e74c3c', alpha=0.7, label='45-60s duration'),
            Patch(facecolor='#3498db', alpha=0.7, label='Other duration')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "03_throughput_comparison.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Throughput comparison")
    
    def plot_timing_distributions(self):
        """Create boxplots of timing distributions"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle("Timing Distribution Boxplots", fontsize=16, fontweight='bold')
        
        scenarios = sorted(self.data.keys())
        device_times = [self.data[s]['avg_device_time'].values * 1000 for s in scenarios]
        edge_times = [self.data[s]['avg_edge_time'].values * 1000 for s in scenarios]
        
        # Device time boxplot
        bp1 = axes[0].boxplot(device_times, labels=scenarios, patch_artist=True)
        axes[0].set_ylabel('Time (ms)')
        axes[0].set_title('Device Layer Execution Time Distribution')
        axes[0].tick_params(axis='x', rotation=45)
        for patch in bp1['boxes']:
            patch.set_facecolor('#3498db')
        axes[0].grid(True, alpha=0.3, axis='y')
        
        # Edge time boxplot
        bp2 = axes[1].boxplot(edge_times, labels=scenarios, patch_artist=True)
        axes[1].set_ylabel('Time (ms)')
        axes[1].set_title('Edge Layer Execution Time Distribution')
        axes[1].tick_params(axis='x', rotation=45)
        for patch in bp2['boxes']:
            patch.set_facecolor('#e74c3c')
        axes[1].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "04_timing_distributions.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Timing distribution boxplots")
    
    def plot_layer_statistics(self):
        """Plot number of layers executed on device vs edge"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        scenarios = sorted(self.data.keys())
        device_layers = []
        edge_layers = []
        
        for scenario in scenarios:
            df = self.data[scenario]
            device_layers.append(df['num_device_layers'].mean())
            edge_layers.append(df['num_edge_layers'].mean())
        
        x_pos = range(len(scenarios))
        width = 0.35
        
        ax.bar([x - width/2 for x in x_pos], device_layers, width, label='Device Layers', alpha=0.8, color='#3498db')
        ax.bar([x + width/2 for x in x_pos], edge_layers, width, label='Edge Layers', alpha=0.8, color='#e74c3c')
        
        ax.set_xticks(x_pos)
        ax.set_xticklabels(scenarios, rotation=45, ha='right')
        ax.set_ylabel('Average Number of Layers')
        ax.set_title('Average Layer Distribution: Device vs Edge')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "05_layer_statistics.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Layer statistics comparison")
    
    def plot_scenario_comparison(self):
        """Create a comprehensive scenario comparison dashboard"""
        scenarios = sorted(self.data.keys())
        n_scenarios = len(scenarios)
        
        fig = plt.figure(figsize=(16, 12))
        gs = gridspec.GridSpec(3, 3, figure=fig)
        
        fig.suptitle("Comprehensive Scenario Comparison Dashboard", fontsize=18, fontweight='bold')
        
        # 1. Avg Device Time
        ax1 = fig.add_subplot(gs[0, 0])
        device_avg = [self.data[s]['avg_device_time'].mean() * 1000 for s in scenarios]
        ax1.bar(range(n_scenarios), device_avg, alpha=0.7, color='#3498db')
        ax1.set_xticks(range(n_scenarios))
        ax1.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
        ax1.set_ylabel('Time (ms)')
        ax1.set_title('Avg Device Time')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # 2. Avg Edge Time
        ax2 = fig.add_subplot(gs[0, 1])
        edge_avg = [self.data[s]['avg_edge_time'].mean() * 1000 for s in scenarios]
        ax2.bar(range(n_scenarios), edge_avg, alpha=0.7, color='#e74c3c')
        ax2.set_xticks(range(n_scenarios))
        ax2.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
        ax2.set_ylabel('Time (ms)')
        ax2.set_title('Avg Edge Time')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # 3. Total Time
        ax3 = fig.add_subplot(gs[0, 2])
        total_avg = [(self.data[s]['avg_device_time'].mean() + self.data[s]['avg_edge_time'].mean()) * 1000 
                     for s in scenarios]
        ax3.bar(range(n_scenarios), total_avg, alpha=0.7, color='#2ecc71')
        ax3.set_xticks(range(n_scenarios))
        ax3.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
        ax3.set_ylabel('Time (ms)')
        ax3.set_title('Avg Total Time')
        ax3.grid(True, alpha=0.3, axis='y')
        
        # 4. Device Time Variance
        ax4 = fig.add_subplot(gs[1, 0])
        device_std = [self.data[s]['avg_device_time'].std() * 1000 for s in scenarios]
        ax4.bar(range(n_scenarios), device_std, alpha=0.7, color='#9b59b6')
        ax4.set_xticks(range(n_scenarios))
        ax4.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
        ax4.set_ylabel('Std Dev (ms)')
        ax4.set_title('Device Time Variance')
        ax4.grid(True, alpha=0.3, axis='y')
        
        # 5. Edge Time Variance
        ax5 = fig.add_subplot(gs[1, 1])
        edge_std = [self.data[s]['avg_edge_time'].std() * 1000 for s in scenarios]
        ax5.bar(range(n_scenarios), edge_std, alpha=0.7, color='#f39c12')
        ax5.set_xticks(range(n_scenarios))
        ax5.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
        ax5.set_ylabel('Std Dev (ms)')
        ax5.set_title('Edge Time Variance')
        ax5.grid(True, alpha=0.3, axis='y')
        
        # 6. Inference Count
        ax6 = fig.add_subplot(gs[1, 2])
        counts = [len(self.data[s]) for s in scenarios]
        ax6.bar(range(n_scenarios), counts, alpha=0.7, color='#1abc9c')
        ax6.set_xticks(range(n_scenarios))
        ax6.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
        ax6.set_ylabel('Count')
        ax6.set_title('Total Inferences')
        ax6.grid(True, alpha=0.3, axis='y')
        
        # 7. Min Device Time
        ax7 = fig.add_subplot(gs[2, 0])
        device_min = [self.data[s]['min_device_time'].mean() * 1000 for s in scenarios]
        ax7.bar(range(n_scenarios), device_min, alpha=0.7, color='#34495e')
        ax7.set_xticks(range(n_scenarios))
        ax7.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
        ax7.set_ylabel('Time (ms)')
        ax7.set_title('Min Device Time')
        ax7.grid(True, alpha=0.3, axis='y')
        
        # 8. Max Device Time
        ax8 = fig.add_subplot(gs[2, 1])
        device_max = [self.data[s]['max_device_time'].mean() * 1000 for s in scenarios]
        ax8.bar(range(n_scenarios), device_max, alpha=0.7, color='#c0392b')
        ax8.set_xticks(range(n_scenarios))
        ax8.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
        ax8.set_ylabel('Time (ms)')
        ax8.set_title('Max Device Time')
        ax8.grid(True, alpha=0.3, axis='y')
        
        # 9. Device Layer Count
        ax9 = fig.add_subplot(gs[2, 2])
        device_layer_count = [self.data[s]['num_device_layers'].mean() for s in scenarios]
        ax9.bar(range(n_scenarios), device_layer_count, alpha=0.7, color='#16a085')
        ax9.set_xticks(range(n_scenarios))
        ax9.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
        ax9.set_ylabel('Avg Layer Count')
        ax9.set_title('Device Layer Count')
        ax9.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / "06_scenario_comparison_dashboard.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Scenario comparison dashboard")
    
    def generate_summary_stats(self):
        """Generate summary statistics table"""
        summary_data = []
        
        for scenario in sorted(self.data.keys()):
            df = self.data[scenario]
            config = self.configs.get(scenario, {})
            
            total_time = (df['avg_device_time'] + df['avg_edge_time']) * 1000
            
            summary_data.append({
                'Scenario': scenario,
                'Inferences': len(df),
                'Device (ms)': f"{df['avg_device_time'].mean() * 1000:.2f} ± {df['avg_device_time'].std() * 1000:.2f}",
                'Edge (ms)': f"{df['avg_edge_time'].mean() * 1000:.2f} ± {df['avg_edge_time'].std() * 1000:.2f}",
                'Total (ms)': f"{total_time.mean():.2f} ± {total_time.std():.2f}",
                'Throughput': f"{len(df) / config.get('duration_seconds', 30):.2f}",
                'Clients': config.get('num_clients', 1),
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        # Save as CSV
        summary_csv = self.output_dir / "summary_statistics.csv"
        summary_df.to_csv(summary_csv, index=False)
        print(f"  ✓ Summary statistics saved to CSV")
        
        # Create a figure with the table
        fig, ax = plt.subplots(figsize=(16, len(summary_data) * 0.5 + 1))
        ax.axis('tight')
        ax.axis('off')
        
        table = ax.table(cellText=summary_df.values, colLabels=summary_df.columns,
                        cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        
        # Style header
        for i in range(len(summary_df.columns)):
            table[(0, i)].set_facecolor('#3498db')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Alternate row colors
        for i in range(1, len(summary_df) + 1):
            color = '#ecf0f1' if i % 2 == 0 else 'white'
            for j in range(len(summary_df.columns)):
                table[(i, j)].set_facecolor(color)
        
        plt.title("Summary Statistics", fontsize=16, fontweight='bold', pad=20)
        plt.savefig(self.output_dir / "07_summary_statistics.png", dpi=150, bbox_inches='tight')
        plt.close()
        
        # Print to console
        print("\n" + "="*120)
        print("SUMMARY STATISTICS")
        print("="*120)
        print(summary_df.to_string(index=False))
        print("="*120)
        
        return summary_df


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_simulation.py <results_directory>")
        print("\nExample:")
        print("  python analyze_simulation.py simulated_results/simulation_20251231_143022")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    
    try:
        analyzer = SimulationAnalyzer(results_dir)
        analyzer.analyze_all()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
