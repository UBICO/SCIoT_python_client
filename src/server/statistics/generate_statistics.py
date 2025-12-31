#!/usr/bin/env python3
"""
Statistics Generation Utility Script
Run this script to generate comprehensive statistics from collected data
"""

import json
import argparse
from pathlib import Path

from server.statistics import StatisticsCollector
from server.commons import OffloadingDataFiles
from server.logger.log import logger


def load_latencies_from_csv(csv_file: str) -> list:
    """Load latencies from evaluations CSV"""
    try:
        import pandas as pd
        df = pd.read_csv(csv_file)
        if 'latency' in df.columns:
            return df['latency'].dropna().tolist()
    except Exception as e:
        logger.error(f"Could not load latencies from CSV: {e}")
    return []


def load_speeds_from_csv(csv_file: str) -> list:
    """Load average speeds from evaluations CSV"""
    try:
        import pandas as pd
        df = pd.read_csv(csv_file)
        if 'avg_speed' in df.columns:
            return df['avg_speed'].dropna().tolist()
    except Exception as e:
        logger.error(f"Could not load speeds from CSV: {e}")
    return []


def main():
    """Main function to generate statistics"""
    parser = argparse.ArgumentParser(
        description='Generate comprehensive statistics for SCIoT system'
    )
    
    parser.add_argument(
        '--device-times',
        default=OffloadingDataFiles.data_file_path_device,
        help='Path to device inference times JSON'
    )
    parser.add_argument(
        '--edge-times',
        default=OffloadingDataFiles.data_file_path_edge,
        help='Path to edge inference times JSON'
    )
    parser.add_argument(
        '--layer-sizes',
        default=OffloadingDataFiles.data_file_path_sizes,
        help='Path to layer sizes JSON'
    )
    parser.add_argument(
        '--evaluations',
        default=None,
        help='Path to evaluations CSV to extract latencies and speeds'
    )
    parser.add_argument(
        '--output-dir',
        default=None,
        help='Output directory for statistics files'
    )
    
    args = parser.parse_args()
    
    # Initialize collector
    collector = StatisticsCollector(output_dir=args.output_dir)
    
    logger.info("Starting statistics generation...")
    
    # Load latencies and speeds if available
    latencies = []
    avg_speeds = []
    
    if args.evaluations and Path(args.evaluations).exists():
        logger.info(f"Loading data from {args.evaluations}")
        latencies = load_latencies_from_csv(args.evaluations)
        avg_speeds = load_speeds_from_csv(args.evaluations)
        
        if latencies:
            logger.info(f"Loaded {len(latencies)} latency measurements")
        if avg_speeds:
            logger.info(f"Loaded {len(avg_speeds)} speed measurements")
    
    # Generate comprehensive report
    try:
        collector.generate_comprehensive_report(
            device_inference_file=args.device_times,
            edge_inference_file=args.edge_times,
            layer_sizes_file=args.layer_sizes,
            latencies=latencies if latencies else None,
            avg_speeds=avg_speeds if avg_speeds else None
        )
        
        # Generate summary report
        collector.summary_report()
        
        logger.info("Statistics generation completed successfully!")
        
    except Exception as e:
        logger.error(f"Error generating statistics: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
