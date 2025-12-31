"""
Statistics Collector Module
Collects and analyzes performance metrics from SCIoT system
"""

import json
import csv
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple
import statistics as stat_module

from server.logger.log import logger


@dataclass
class StatisticsResult:
    """Container for statistical results"""
    metric_name: str
    count: int
    min_value: float
    max_value: float
    mean_value: float
    median_value: float
    std_dev: float
    sum_value: float


class StatisticsCollector:
    """Collects and generates statistics from inference times, latencies, and data sizes"""

    def __init__(self, output_dir: str = None):
        """
        Initialize the statistics collector
        
        Args:
            output_dir: Directory to save statistics files
        """
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).resolve().parent.parent
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_times(self, times: List[float], metric_name: str) -> StatisticsResult:
        """
        Analyze a list of timing values
        
        Args:
            times: List of timing values
            metric_name: Name of the metric being analyzed
            
        Returns:
            StatisticsResult with computed statistics
        """
        if not times:
            logger.warning(f"No data available for {metric_name}")
            return None

        return StatisticsResult(
            metric_name=metric_name,
            count=len(times),
            min_value=min(times),
            max_value=max(times),
            mean_value=stat_module.mean(times),
            median_value=stat_module.median(times),
            std_dev=stat_module.stdev(times) if len(times) > 1 else 0.0,
            sum_value=sum(times)
        )

    def analyze_inference_times(self, inference_times_file: str) -> Dict[str, StatisticsResult]:
        """
        Analyze device or edge inference times from JSON file
        
        Args:
            inference_times_file: Path to JSON file with inference times
            
        Returns:
            Dictionary with statistics results for each layer
        """
        try:
            with open(inference_times_file, 'r') as f:
                data = json.load(f)
            
            times = list(data.values())
            return {
                'all_layers': self.analyze_times(times, Path(inference_times_file).stem),
                'per_layer': data
            }
        except Exception as e:
            logger.error(f"Error analyzing inference times: {e}")
            return None

    def analyze_layer_sizes(self, layer_sizes_file: str) -> Dict[str, any]:
        """
        Analyze data transmission sizes from JSON file
        
        Args:
            layer_sizes_file: Path to JSON file with layer sizes
            
        Returns:
            Dictionary with size statistics
        """
        try:
            with open(layer_sizes_file, 'r') as f:
                data = json.load(f)
            
            sizes = [float(v) for v in data.values()]
            return {
                'statistics': self.analyze_times(sizes, 'layer_sizes'),
                'per_layer': data,
                'total_size': sum(sizes),
                'average_size': stat_module.mean(sizes)
            }
        except Exception as e:
            logger.error(f"Error analyzing layer sizes: {e}")
            return None

    def calculate_offloading_metrics(self, 
                                     device_times: Dict[str, float],
                                     edge_times: Dict[str, float],
                                     layer_sizes: Dict[int, float],
                                     avg_speeds: List[float]) -> List[Dict]:
        """
        Calculate metrics for each possible offloading layer
        
        Args:
            device_times: Device inference times per layer
            edge_times: Edge inference times per layer
            layer_sizes: Data sizes for each layer
            avg_speeds: Average network speeds
            
        Returns:
            List of dictionaries with offloading metrics
        """
        metrics = []
        
        for layer_idx in range(len(device_times)):
            device_cost = sum(list(device_times.values())[:layer_idx + 1])
            edge_cost = sum(list(edge_times.values())[layer_idx + 1:])
            transmission_cost = layer_sizes.get(str(layer_idx), 0) / (stat_module.mean(avg_speeds) if avg_speeds else 1)
            
            total_latency = device_cost + transmission_cost + edge_cost
            
            metrics.append({
                'layer': layer_idx,
                'device_cost': device_cost,
                'transmission_cost': transmission_cost,
                'edge_cost': edge_cost,
                'total_latency': total_latency
            })
        
        return metrics

    def save_statistics_csv(self, stats_result: StatisticsResult, filename: str):
        """Save single statistic result to CSV"""
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Metric', 'Value'])
                writer.writerow(['Name', stats_result.metric_name])
                writer.writerow(['Count', stats_result.count])
                writer.writerow(['Minimum (s)', f"{stats_result.min_value:.6f}"])
                writer.writerow(['Maximum (s)', f"{stats_result.max_value:.6f}"])
                writer.writerow(['Mean (s)', f"{stats_result.mean_value:.6f}"])
                writer.writerow(['Median (s)', f"{stats_result.median_value:.6f}"])
                writer.writerow(['Std Dev (s)', f"{stats_result.std_dev:.6f}"])
                writer.writerow(['Total (s)', f"{stats_result.sum_value:.6f}"])
            
            logger.info(f"Statistics saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving statistics CSV: {e}")

    def save_layer_statistics_csv(self, per_layer_data: Dict, filename: str):
        """Save per-layer statistics to CSV"""
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Layer', 'Value'])
                
                for layer, value in sorted(per_layer_data.items(), key=lambda x: int(x[0]) if x[0].isdigit() else int(x[0].split('_')[1])):
                    writer.writerow([layer, f"{float(value):.6f}"])
            
            logger.info(f"Layer statistics saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving layer statistics CSV: {e}")

    def save_offloading_metrics_csv(self, metrics: List[Dict], filename: str):
        """Save offloading metrics to CSV"""
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['layer', 'device_cost', 'transmission_cost', 'edge_cost', 'total_latency'])
                writer.writeheader()
                
                for metric in metrics:
                    writer.writerow({
                        'layer': metric['layer'],
                        'device_cost': f"{metric['device_cost']:.6f}",
                        'transmission_cost': f"{metric['transmission_cost']:.6f}",
                        'edge_cost': f"{metric['edge_cost']:.6f}",
                        'total_latency': f"{metric['total_latency']:.6f}"
                    })
            
            logger.info(f"Offloading metrics saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving offloading metrics CSV: {e}")

    def save_latency_statistics_csv(self, latencies: List[float], filename: str):
        """Save latency statistics to CSV"""
        if not latencies:
            logger.warning("No latency data available")
            return
        
        stats = self.analyze_times(latencies, 'network_latency')
        self.save_statistics_csv(stats, filename)

    def generate_comprehensive_report(self,
                                     device_inference_file: str,
                                     edge_inference_file: str,
                                     layer_sizes_file: str,
                                     latencies: List[float] = None,
                                     avg_speeds: List[float] = None):
        """
        Generate comprehensive statistics report with multiple files
        
        Args:
            device_inference_file: Path to device inference times JSON
            edge_inference_file: Path to edge inference times JSON
            layer_sizes_file: Path to layer sizes JSON
            latencies: Optional list of latency measurements
            avg_speeds: Optional list of network speeds
        """
        logger.info("Generating comprehensive statistics report...")
        
        # Analyze device inference times
        device_stats = self.analyze_inference_times(device_inference_file)
        if device_stats:
            self.save_statistics_csv(device_stats['all_layers'], 'device_inference_statistics.csv')
            self.save_layer_statistics_csv(device_stats['per_layer'], 'device_inference_per_layer.csv')
        
        # Analyze edge inference times
        edge_stats = self.analyze_inference_times(edge_inference_file)
        if edge_stats:
            self.save_statistics_csv(edge_stats['all_layers'], 'edge_inference_statistics.csv')
            self.save_layer_statistics_csv(edge_stats['per_layer'], 'edge_inference_per_layer.csv')
        
        # Analyze layer sizes
        size_stats = self.analyze_layer_sizes(layer_sizes_file)
        if size_stats:
            self.save_statistics_csv(size_stats['statistics'], 'layer_sizes_statistics.csv')
            self.save_layer_statistics_csv(size_stats['per_layer'], 'layer_sizes_per_layer.csv')
        
        # Analyze latencies if provided
        if latencies:
            self.save_latency_statistics_csv(latencies, 'latency_statistics.csv')
        
        # Calculate and save offloading metrics
        if device_stats and edge_stats and size_stats and avg_speeds:
            with open(device_inference_file, 'r') as f:
                device_times = json.load(f)
            with open(edge_inference_file, 'r') as f:
                edge_times = json.load(f)
            with open(layer_sizes_file, 'r') as f:
                layer_sizes = json.load(f)
            
            offloading_metrics = self.calculate_offloading_metrics(device_times, edge_times, layer_sizes, avg_speeds)
            self.save_offloading_metrics_csv(offloading_metrics, 'offloading_metrics.csv')
        
        logger.info("Statistics report generation completed!")

    def summary_report(self, output_file: str = None):
        """Generate a summary report of all statistics files"""
        output_file = output_file or self.output_dir / 'statistics_summary.txt'
        
        try:
            with open(output_file, 'w') as f:
                f.write("=" * 80 + "\n")
                f.write("SCIoT Performance Statistics Summary\n")
                f.write("=" * 80 + "\n\n")
                
                f.write("Generated Files:\n")
                f.write("-" * 80 + "\n")
                
                for csv_file in sorted(self.output_dir.glob('*.csv')):
                    f.write(f"  - {csv_file.name}\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("Files are ready for analysis and visualization\n")
                f.write("=" * 80 + "\n")
            
            logger.info(f"Summary report saved to {output_file}")
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
