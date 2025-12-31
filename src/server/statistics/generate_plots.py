#!/usr/bin/env python
"""
CLI utility for generating plots from SCIoT statistics
Usage: python generate_plots.py [--stats-dir DIR] [--output-dir DIR]
"""

import argparse
from pathlib import Path
from server.statistics.statistics_visualizer import StatisticsVisualizer


def main():
    parser = argparse.ArgumentParser(
        description='Generate visualization plots from SCIoT statistics'
    )
    parser.add_argument(
        '--stats-dir',
        type=str,
        default=None,
        help='Directory containing statistics CSV files (default: parent directory)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Directory to save plots (default: stats_dir/plots)'
    )
    
    args = parser.parse_args()
    
    visualizer = StatisticsVisualizer(
        stats_dir=args.stats_dir,
        output_dir=args.output_dir
    )
    
    visualizer.generate_all_plots()


if __name__ == '__main__':
    main()
