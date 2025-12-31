#!/usr/bin/env python
"""
Convenience script to generate statistics and plots for SCIoT system.
Run this from the project root directory.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report its status."""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout:
            print(result.stdout)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main():
    """Generate statistics and plots."""
    print("\n" + "="*70)
    print("SCIoT Analysis Generator")
    print("="*70)
    
    # Check if we're in the right directory
    if not Path("src/server/statistics").exists():
        print("Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Generate statistics
    success = run_command(
        "python src/server/statistics/generate_statistics.py",
        "Generating Statistics"
    )
    
    if not success:
        print("\n✗ Statistics generation failed. Aborting.")
        sys.exit(1)
    
    # Generate plots
    success = run_command(
        "python src/server/statistics/generate_plots.py",
        "Generating Plots"
    )
    
    if not success:
        print("\n✗ Plot generation failed.")
        sys.exit(1)
    
    # Final summary
    print("\n" + "="*70)
    print("Analysis Generation Complete!")
    print("="*70)
    print(f"Statistics saved to: src/server/")
    print(f"  - device_inference_statistics.csv")
    print(f"  - edge_inference_statistics.csv")
    print(f"  - layer_sizes_statistics.csv")
    print(f"  - statistics_summary.txt")
    print(f"\nPlots saved to: src/server/plots/")
    print(f"  - inference_times_comparison.png")
    print(f"  - inference_distribution.png")
    print(f"  - layer_sizes.png")
    print(f"  - statistics_summary.png")
    print(f"  - cumulative_costs.png")
    print(f"  - index.html (interactive dashboard)")
    print(f"\nOpen src/server/plots/index.html in your browser to view all plots.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
