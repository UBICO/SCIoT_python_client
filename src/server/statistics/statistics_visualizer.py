"""
Visualization Module for SCIoT Statistics
Generates plots and visualizations from collected performance metrics
"""

import json
import csv
from pathlib import Path
from typing import List, Dict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from server.logger.log import logger


class StatisticsVisualizer:
    """Creates visualizations from SCIoT statistics data"""

    def __init__(self, stats_dir: str = None, output_dir: str = None):
        """
        Initialize the visualizer
        
        Args:
            stats_dir: Directory containing statistics CSV files
            output_dir: Directory to save plot images
        """
        self.stats_dir = Path(stats_dir) if stats_dir else Path(__file__).resolve().parent.parent
        self.output_dir = Path(output_dir) if output_dir else self.stats_dir / 'plots'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set plot style
        plt.style.use('seaborn-v0_8-darkgrid')
        self.colors = {
            'device': '#3498db',
            'edge': '#e74c3c',
            'transmission': '#f39c12',
            'total': '#2ecc71'
        }

    def load_csv_data(self, filename: str) -> pd.DataFrame:
        """Load CSV data into DataFrame"""
        filepath = self.stats_dir / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return None
        try:
            return pd.read_csv(filepath)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return None

    def plot_inference_times_comparison(self):
        """Plot device vs edge inference times side by side"""
        device_df = self.load_csv_data('device_inference_per_layer.csv')
        edge_df = self.load_csv_data('edge_inference_per_layer.csv')
        
        if device_df is None or edge_df is None:
            logger.warning("Cannot create inference times comparison plot")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # Device inference times
        ax1.bar(range(len(device_df)), device_df['Value'].values, color=self.colors['device'], alpha=0.8)
        ax1.set_xlabel('Layer', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Time (seconds)', fontsize=11, fontweight='bold')
        ax1.set_title('Device Inference Times per Layer', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        # Edge inference times
        ax2.bar(range(len(edge_df)), edge_df['Value'].values, color=self.colors['edge'], alpha=0.8)
        ax2.set_xlabel('Layer', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Time (seconds)', fontsize=11, fontweight='bold')
        ax2.set_title('Edge Inference Times per Layer', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.output_dir / 'inference_times_comparison.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_path}")
        plt.close()

    def plot_device_vs_edge_distribution(self):
        """Plot distribution comparison as boxplots"""
        device_df = self.load_csv_data('device_inference_per_layer.csv')
        edge_df = self.load_csv_data('edge_inference_per_layer.csv')
        
        if device_df is None or edge_df is None:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        data_to_plot = [
            device_df['Value'].values * 1000,  # Convert to ms
            edge_df['Value'].values * 1000
        ]
        
        bp = ax.boxplot(data_to_plot, labels=['Device', 'Edge'], patch_artist=True)
        
        colors = [self.colors['device'], self.colors['edge']]
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax.set_ylabel('Inference Time (ms)', fontsize=11, fontweight='bold')
        ax.set_title('Device vs Edge Inference Times Distribution', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        output_path = self.output_dir / 'inference_distribution.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_path}")
        plt.close()

    def plot_layer_sizes(self):
        """Plot data transmission sizes per layer"""
        sizes_df = self.load_csv_data('layer_sizes_per_layer.csv')
        
        if sizes_df is None:
            return
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Convert to KB for better readability
        values_kb = sizes_df['Value'].values / 1024
        
        bars = ax.bar(range(len(sizes_df)), values_kb, color=self.colors['transmission'], alpha=0.8)
        
        ax.set_xlabel('Layer', fontsize=11, fontweight='bold')
        ax.set_ylabel('Data Size (KB)', fontsize=11, fontweight='bold')
        ax.set_title('Layer Output Sizes (Data to Transmit)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Highlight maximum
        max_idx = np.argmax(values_kb)
        bars[max_idx].set_color(self.colors['edge'])
        bars[max_idx].set_alpha(1.0)
        
        plt.tight_layout()
        output_path = self.output_dir / 'layer_sizes.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_path}")
        plt.close()

    def plot_offloading_metrics(self):
        """Plot offloading cost analysis"""
        metrics_df = self.load_csv_data('offloading_metrics.csv')
        
        if metrics_df is None:
            logger.warning("Offloading metrics file not found")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        layers = metrics_df['layer'].values
        
        # Plot 1: Stacked area chart
        device_cost = metrics_df['device_cost'].values * 1000  # Convert to ms
        transmission_cost = metrics_df['transmission_cost'].values * 1000
        edge_cost = metrics_df['edge_cost'].values * 1000
        
        ax1.stackplot(layers, device_cost, transmission_cost, edge_cost,
                      labels=['Device Cost', 'Transmission Cost', 'Edge Cost'],
                      colors=[self.colors['device'], self.colors['transmission'], self.colors['edge']],
                      alpha=0.8)
        ax1.set_xlabel('Offloading Layer', fontsize=10, fontweight='bold')
        ax1.set_ylabel('Time (ms)', fontsize=10, fontweight='bold')
        ax1.set_title('Cost Breakdown by Offloading Point', fontsize=11, fontweight='bold')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Total latency
        total_latency = metrics_df['total_latency'].values * 1000
        min_idx = np.argmin(total_latency)
        
        bars = ax2.bar(layers, total_latency, color=self.colors['total'], alpha=0.8)
        bars[min_idx].set_color('#27ae60')
        bars[min_idx].set_alpha(1.0)
        
        ax2.set_xlabel('Offloading Layer', fontsize=10, fontweight='bold')
        ax2.set_ylabel('Total Latency (ms)', fontsize=10, fontweight='bold')
        ax2.set_title('Total Latency per Offloading Point', fontsize=11, fontweight='bold')
        ax2.axhline(y=total_latency[min_idx], color='green', linestyle='--', alpha=0.5)
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Add optimal point annotation
        ax2.annotate(f'Optimal: Layer {layers[min_idx]}',
                    xy=(layers[min_idx], total_latency[min_idx]),
                    xytext=(layers[min_idx] + 5, total_latency[min_idx] + 5),
                    arrowprops=dict(arrowstyle='->', color='green'),
                    fontsize=10, color='green', fontweight='bold')
        
        # Plot 3: Individual costs
        ax3.plot(layers, device_cost, marker='o', label='Device Cost', 
                color=self.colors['device'], linewidth=2)
        ax3.plot(layers, transmission_cost, marker='s', label='Transmission Cost',
                color=self.colors['transmission'], linewidth=2)
        ax3.plot(layers, edge_cost, marker='^', label='Edge Cost',
                color=self.colors['edge'], linewidth=2)
        ax3.set_xlabel('Offloading Layer', fontsize=10, fontweight='bold')
        ax3.set_ylabel('Time (ms)', fontsize=10, fontweight='bold')
        ax3.set_title('Individual Cost Components', fontsize=11, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Cost ratio
        total_sum = device_cost + transmission_cost + edge_cost
        device_ratio = (device_cost / total_sum) * 100
        transmission_ratio = (transmission_cost / total_sum) * 100
        edge_ratio = (edge_cost / total_sum) * 100
        
        ax4.stackplot(layers, device_ratio, transmission_ratio, edge_ratio,
                     labels=['Device %', 'Transmission %', 'Edge %'],
                     colors=[self.colors['device'], self.colors['transmission'], self.colors['edge']],
                     alpha=0.8)
        ax4.set_xlabel('Offloading Layer', fontsize=10, fontweight='bold')
        ax4.set_ylabel('Percentage (%)', fontsize=10, fontweight='bold')
        ax4.set_title('Cost Distribution (Percentage)', fontsize=11, fontweight='bold')
        ax4.set_ylim([0, 100])
        ax4.legend(loc='upper left')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.output_dir / 'offloading_metrics.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_path}")
        plt.close()

    def plot_latency_distribution(self):
        """Plot latency distribution if available"""
        latency_df = self.load_csv_data('latency_statistics.csv')
        
        if latency_df is None:
            logger.info("Latency statistics not available")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Extract statistics
        stats_dict = dict(zip(latency_df['Metric'], latency_df['Value']))
        
        metrics = ['Minimum (s)', 'Mean (s)', 'Median (s)', 'Maximum (s)']
        values = []
        for metric in metrics:
            try:
                values.append(float(stats_dict.get(metric, 0)))
            except:
                values.append(0)
        
        colors_list = ['#3498db', '#f39c12', '#9b59b6', '#e74c3c']
        bars = ax.bar(range(len(metrics)), values, color=colors_list, alpha=0.8)
        
        ax.set_ylabel('Latency (seconds)', fontsize=11, fontweight='bold')
        ax.set_title('Network Latency Distribution', fontsize=12, fontweight='bold')
        ax.set_xticklabels(metrics)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{value:.6f}s',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        output_path = self.output_dir / 'latency_distribution.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_path}")
        plt.close()

    def plot_statistics_summary(self):
        """Create a summary statistics visualization"""
        device_stats = self.load_csv_data('device_inference_statistics.csv')
        edge_stats = self.load_csv_data('edge_inference_statistics.csv')
        sizes_stats = self.load_csv_data('layer_sizes_statistics.csv')
        
        if device_stats is None:
            return
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        # Helper function to plot statistics
        def plot_stats(ax, stats_df, title, color):
            stats_dict = dict(zip(stats_df['Metric'], stats_df['Value']))
            
            metrics = ['Minimum (s)', 'Mean (s)', 'Median (s)', 'Maximum (s)']
            try:
                values = [float(stats_dict.get(m, 0)) for m in metrics]
            except:
                values = [0, 0, 0, 0]
            
            bars = ax.bar(range(len(metrics)), values, color=color, alpha=0.8)
            ax.set_title(title, fontsize=11, fontweight='bold')
            ax.set_xticklabels(['Min', 'Mean', 'Med', 'Max'], fontsize=9)
            ax.set_ylabel('Time (seconds)', fontsize=10, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y')
            
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{value:.2e}',
                       ha='center', va='bottom', fontsize=8)
        
        plot_stats(axes[0], device_stats, 'Device Inference Times', self.colors['device'])
        plot_stats(axes[1], edge_stats, 'Edge Inference Times', self.colors['edge'])
        
        if sizes_stats is not None:
            plot_stats(axes[2], sizes_stats, 'Layer Sizes (bytes)', self.colors['transmission'])
        
        plt.tight_layout()
        output_path = self.output_dir / 'statistics_summary.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_path}")
        plt.close()

    def plot_cumulative_costs(self):
        """Plot cumulative inference time across layers"""
        device_df = self.load_csv_data('device_inference_per_layer.csv')
        edge_df = self.load_csv_data('edge_inference_per_layer.csv')
        
        if device_df is None or edge_df is None:
            return
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        device_cumsum = np.cumsum(device_df['Value'].values) * 1000  # Convert to ms
        edge_cumsum = np.cumsum(edge_df['Value'].values) * 1000
        
        layers = range(len(device_df))
        
        ax.plot(layers, device_cumsum, marker='o', label='Cumulative Device Time',
               color=self.colors['device'], linewidth=2.5, markersize=5)
        ax.plot(layers, edge_cumsum, marker='s', label='Cumulative Edge Time',
               color=self.colors['edge'], linewidth=2.5, markersize=5)
        
        ax.fill_between(layers, device_cumsum, alpha=0.2, color=self.colors['device'])
        ax.fill_between(layers, edge_cumsum, alpha=0.2, color=self.colors['edge'])
        
        ax.set_xlabel('Layer', fontsize=11, fontweight='bold')
        ax.set_ylabel('Cumulative Time (ms)', fontsize=11, fontweight='bold')
        ax.set_title('Cumulative Inference Time per Layer', fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_path = self.output_dir / 'cumulative_costs.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_path}")
        plt.close()

    def generate_all_plots(self):
        """Generate all available plots"""
        logger.info("Generating all visualization plots...")
        
        self.plot_inference_times_comparison()
        self.plot_device_vs_edge_distribution()
        self.plot_layer_sizes()
        self.plot_statistics_summary()
        self.plot_cumulative_costs()
        self.plot_offloading_metrics()
        self.plot_latency_distribution()
        
        logger.info(f"All plots saved to: {self.output_dir}")
        
        # Create index file
        self.create_plot_index()

    def create_plot_index(self):
        """Create an HTML index of all plots"""
        plot_files = sorted(list(self.output_dir.glob('*.png')))
        
        if not plot_files:
            logger.warning("No plot files found")
            return
        
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>SCIoT Statistics Visualization</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .plot-container {
            margin: 30px 0;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .plot-container h2 {
            color: #2c3e50;
            margin-top: 0;
        }
        img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <h1>SCIoT Performance Statistics - Visualizations</h1>
    <p style="text-align: center; color: #666;">Generated plots for inference times, data sizes, and offloading metrics</p>
"""
        
        plot_descriptions = {
            'inference_times_comparison.png': 'Device vs Edge Inference Times per Layer',
            'inference_distribution.png': 'Distribution Comparison (Boxplots)',
            'layer_sizes.png': 'Data Transmission Sizes per Layer',
            'statistics_summary.png': 'Summary Statistics Overview',
            'cumulative_costs.png': 'Cumulative Inference Time Progression',
            'offloading_metrics.png': 'Offloading Cost Analysis (4-panel)',
            'latency_distribution.png': 'Network Latency Distribution'
        }
        
        for plot_file in plot_files:
            description = plot_descriptions.get(plot_file.name, plot_file.name)
            html_content += f"""
    <div class="plot-container">
        <h2>{description}</h2>
        <img src="{plot_file.name}" alt="{description}">
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        index_path = self.output_dir / 'index.html'
        with open(index_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Plot index saved to: {index_path}")
