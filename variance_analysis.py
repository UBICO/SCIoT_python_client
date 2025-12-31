#!/usr/bin/env python3
"""
Variance Analysis Utility
Analyzes variance detection data and provides recommendations.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from server.variance_detector import VarianceDetector
from server.communication.request_handler import RequestHandler


def analyze_current_variance():
    """
    Analyze current variance state from the RequestHandler's detector.
    Provides insights and recommendations.
    """
    
    detector = RequestHandler.variance_detector
    stats = detector.get_all_stats()
    
    print("\n" + "=" * 80)
    print("CURRENT SYSTEM VARIANCE ANALYSIS")
    print("=" * 80)
    
    # Analyze device inference times
    print("\n📱 DEVICE INFERENCE TIMES")
    print("-" * 80)
    
    device_unstable = []
    device_stable_count = 0
    
    for layer_id in sorted(stats['device'].keys()):
        layer_stats = stats['device'][layer_id]
        
        # Show every 5th layer to avoid clutter, plus any unstable ones
        if layer_id % 5 == 0 or not layer_stats['is_stable']:
            status = "🟢 STABLE" if layer_stats['is_stable'] else "🔴 UNSTABLE"
            print(f"  Layer {layer_id:2d}: mean={layer_stats['mean']*1e6:6.1f}µs, "
                  f"CV={layer_stats['cv']:5.2%}, n={layer_stats['measurements']:2d} {status}")
            
            if not layer_stats['is_stable']:
                device_unstable.append((layer_id, layer_stats['cv']))
        
        if layer_stats['is_stable']:
            device_stable_count += 1
    
    total_device_layers = len(stats['device'])
    print(f"\n  Summary: {device_stable_count}/{total_device_layers} layers stable")
    
    if device_unstable:
        print(f"  ⚠️  Unstable layers (CV > 15%): {[l[0] for l in device_unstable]}")
    
    # Analyze edge inference times
    print("\n🖥️  EDGE INFERENCE TIMES")
    print("-" * 80)
    
    edge_unstable = []
    edge_stable_count = 0
    
    for layer_id in sorted(stats['edge'].keys()):
        layer_stats = stats['edge'][layer_id]
        
        # Show every 5th layer to avoid clutter, plus any unstable ones
        if layer_id % 5 == 0 or not layer_stats['is_stable']:
            status = "🟢 STABLE" if layer_stats['is_stable'] else "🔴 UNSTABLE"
            print(f"  Layer {layer_id:2d}: mean={layer_stats['mean']*1e6:7.1f}µs, "
                  f"CV={layer_stats['cv']:5.2%}, n={layer_stats['measurements']:2d} {status}")
            
            if not layer_stats['is_stable']:
                edge_unstable.append((layer_id, layer_stats['cv']))
        
        if layer_stats['is_stable']:
            edge_stable_count += 1
    
    total_edge_layers = len(stats['edge'])
    print(f"\n  Summary: {edge_stable_count}/{total_edge_layers} layers stable")
    
    if edge_unstable:
        print(f"  ⚠️  Unstable layers (CV > 15%): {[l[0] for l in edge_unstable]}")
    
    # Recommendations
    print("\n📋 RECOMMENDATIONS")
    print("-" * 80)
    
    if stats['needs_retest']:
        print("  🔴 OFFLOADING RE-TEST NEEDED")
        print("     Variance detected in inference times. Consider re-running")
        print("     the offloading algorithm to optimize split point.")
    else:
        print("  ✅ Offloading algorithm is optimal (low variance)")
    
    if device_unstable or edge_unstable:
        print("\n  Actions to investigate unstable layers:")
        if device_unstable:
            print(f"    - Check device conditions for layers: {[l[0] for l in device_unstable]}")
            print("      (May indicate variable load or thermal throttling)")
        if edge_unstable:
            print(f"    - Check edge server load for layers: {[l[0] for l in edge_unstable]}")
            print("      (May indicate system under load or network congestion)")
    
    # Overall system health
    total_unstable = len(device_unstable) + len(edge_unstable)
    total_layers = total_device_layers + total_edge_layers
    stability_percentage = ((total_layers - total_unstable) / total_layers * 100) if total_layers > 0 else 0
    
    print(f"\n  System Health Score: {stability_percentage:.1f}%")
    if stability_percentage >= 95:
        print("  Status: 🟢 EXCELLENT - System is stable and optimized")
    elif stability_percentage >= 80:
        print("  Status: 🟡 GOOD - Minor instability detected")
    else:
        print("  Status: 🔴 POOR - Significant variance detected, investigate")
    
    print("\n" + "=" * 80)


def compare_layer_pairs():
    """
    Compare device vs edge performance for each layer.
    Helps identify optimal split points.
    """
    
    detector = RequestHandler.variance_detector
    stats = detector.get_all_stats()
    
    print("\n" + "=" * 80)
    print("DEVICE vs EDGE COMPARISON")
    print("=" * 80)
    
    print("\nDevice and Edge Latency by Layer (best split point analysis):")
    print("-" * 80)
    print("Layer | Device(µs) | Edge(µs) | Device_CV | Edge_CV | Cumulative")
    print("      |            |          |           |         | Device Edge")
    print("-" * 80)
    
    cumulative_device = 0
    cumulative_edge = 0
    
    for layer_id in sorted(stats['device'].keys())[:15]:  # Show first 15 layers
        device = stats['device'].get(layer_id, {})
        edge = stats['edge'].get(layer_id, {})
        
        if device and edge:
            dev_time = device.get('mean', 0) * 1e6
            edge_time = edge.get('mean', 0) * 1e6
            cumulative_device += dev_time
            cumulative_edge += edge_time
            
            print(f"{layer_id:5d} | {dev_time:10.1f} | {edge_time:8.1f} | "
                  f"{device.get('cv', 0):8.2%}  | {edge.get('cv', 0):6.2%} | "
                  f"{cumulative_device:6.0f}  {cumulative_edge:5.0f}")
    
    if len(stats['device']) > 15:
        print("       (... more layers ...)")
        # Show last layer
        last_id = max(stats['device'].keys())
        device = stats['device'][last_id]
        edge = stats['edge'].get(last_id, {})
        
        if edge:
            cumulative_device += device.get('mean', 0) * 1e6
            cumulative_edge += edge.get('mean', 0) * 1e6
            print(f"{last_id:5d} | {device.get('mean', 0)*1e6:10.1f} | "
                  f"{edge.get('mean', 0)*1e6:8.1f} | "
                  f"{device.get('cv', 0):8.2%}  | {edge.get('cv', 0):6.2%} | "
                  f"{cumulative_device:6.0f}  {cumulative_edge:5.0f}")
    
    print("-" * 80)
    print(f"TOTAL   | {cumulative_device:10.0f} | {cumulative_edge:8.0f}")
    print(f"Speedup: Edge is {cumulative_edge/cumulative_device:.1f}x slower (expected for Python/TFLite)")
    
    print("\n" + "=" * 80)


def export_variance_data(output_file: str = "variance_stats.json"):
    """
    Export current variance data to JSON for external analysis.
    
    Args:
        output_file: Path to save the JSON file
    """
    
    detector = RequestHandler.variance_detector
    stats = detector.get_all_stats()
    
    output_path = Path(output_file)
    
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n✅ Variance statistics exported to {output_path}")
    print(f"   File size: {output_path.stat().st_size} bytes")


if __name__ == "__main__":
    print("\n🔍 Variance Analysis Utility")
    print("=" * 80)
    print("""
This utility analyzes inference time variance detected by the system.

Usage:
  from variance_analysis import (
      analyze_current_variance,      # Full analysis report
      compare_layer_pairs,            # Device vs Edge comparison
      export_variance_data            # Export to JSON
  )
  
  analyze_current_variance()
  compare_layer_pairs()
  export_variance_data("my_variance_data.json")
    """)
    
    # Run demonstrations if variance data exists
    print("\nRunning analysis on current system state...")
    try:
        analyze_current_variance()
        compare_layer_pairs()
    except Exception as e:
        print(f"\n⚠️  Could not analyze system variance: {e}")
        print("   (System needs to be running with active inference for data)")
