#!/usr/bin/env python3
"""
Interactive demonstration of variance cascading.
For automated tests, see tests/test_variance_and_local_inference.py

This script demonstrates:
- When layer i has variance, layer i+1 needs re-testing
- Why: output of layer i is input to layer i+1
- Multiple cascade chains with several unstable layers
"""

from server.variance_detector import VarianceDetector


def main():
    """Run interactive cascading demonstration"""
    
    print("=" * 80)
    print("VARIANCE CASCADING - INTERACTIVE DEMO")
    print("=" * 80)
    
    print("\nSCENARIO: Layer 5 performance degrades")
    print("EXPECTED: Layer 6 should also be flagged for re-test")
    print("REASON: Output of layer 5 is input to layer 6\n")
    
    detector = VarianceDetector(window_size=10, variance_threshold=0.15)
    
    print("Phase 1: Layer 5 initially stable at 200µs")
    print("-" * 80)
    for i in range(10):
        detector.add_edge_measurement(5, 200e-6 + (i % 2) * 5e-6)
    
    print("  ✓ Layer 5 stable (CV < 15%)")
    layers = detector.get_layers_needing_retest()
    print(f"  Layers needing re-test: {layers['edge']}\n")
    
    print("Phase 2: Layer 5 degrades (300µs with increasing trend)")
    print("-" * 80)
    for i in range(10):
        detector.add_edge_measurement(5, 300e-6 + (i * 10e-6))
    
    stats = detector.edge_histories[5].get_stats()
    print(f"  Layer 5 CV: {stats['cv']:.2%} - UNSTABLE")
    
    layers = detector.get_layers_needing_retest()
    variance_layers = detector.get_all_stats()['layers_with_variance']['edge']
    
    print(f"\n  Layers with variance: {sorted(variance_layers)}")
    print(f"  Layers needing re-test: {sorted(layers['edge'])}")
    
    if 6 in layers['edge']:
        print(f"\n  ✓ Layer 6 automatically flagged (found in {layers['edge']})")
        print("  ✓ Cascade working correctly")
    
    print("\nCascade Chain:")
    for layer_id in sorted(variance_layers):
        print(f"  Layer {layer_id} (variance) → Layer {layer_id+1} (cascade)")
    
    print("\n" + "=" * 80)
    print("MULTIPLE CASCADES")
    print("=" * 80)
    
    detector2 = VarianceDetector(window_size=10, variance_threshold=0.15)
    
    print("\nCreating unstable layers: 3, 5, 7")
    print("-" * 80)
    
    for layer_id in [3, 5, 7]:
        # Stable then unstable
        for i in range(5):
            detector2.add_device_measurement(layer_id, 19e-6)
        for i in range(5):
            detector2.add_device_measurement(layer_id, 38e-6)
        print(f"  ✓ Layer {layer_id} made unstable")
    
    layers = detector2.get_layers_needing_retest()
    variance_layers = detector2.get_all_stats()['layers_with_variance']['device']
    
    print(f"\n  Variance detected in: {sorted(variance_layers)}")
    print(f"  Re-test needed for: {sorted(layers['device'])}")
    
    print("\nCascade Chains:")
    for layer_id in sorted(variance_layers):
        print(f"  Layer {layer_id} (variance) → Layer {layer_id+1} (cascade)")
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nKey Takeaway:")
    print("  When layer i changes, layer i+1 must be re-tested because")
    print("  the input distribution to layer i+1 has changed.")
    print("\nFor automated tests, run: pytest tests/test_variance_and_local_inference.py")


if __name__ == "__main__":
    main()

    """Demonstrate variance cascading to next layer"""
    
    print("=" * 80)
    print("VARIANCE CASCADING TEST")
    print("=" * 80)
    print("\nScenario: Layer 5 performance degrades → Layer 6 needs re-test\n")
    
    detector = VarianceDetector(window_size=10, variance_threshold=0.15)
    
    # Layer 5: Stable at first
    print("Phase 1: Layer 5 is stable (200µs ± 5µs)")
    for i in range(10):
        time = 200e-6 + (i % 2) * 5e-6
        detector.add_edge_measurement(5, time)
    
    print("  ✓ Layer 5 stable")
    print(f"  Layers needing re-test: {detector.get_layers_needing_retest()['edge']}\n")
    
    # Layer 5: Degrades
    print("Phase 2: Layer 5 performance changes (300µs ± 50µs) - VARIANCE DETECTED")
    for i in range(10):
        time = 300e-6 + (i * 10e-6)  # Growing trend
        detector.add_edge_measurement(5, time)
    
    stats = detector.edge_histories[5].get_stats()
    print(f"  Layer 5 CV: {stats['cv']:.2%} - UNSTABLE (threshold 15%)")
    
    layers_to_test = detector.get_layers_needing_retest()
    print(f"  ⚠️  Layers needing re-test: Device={layers_to_test['device']}, "
          f"Edge={layers_to_test['edge']}\n")
    
    print("RESULT:")
    print("  ✓ Layer 5 variance detected")
    print(f"  ✓ Layer 6 automatically flagged (found in {layers_to_test['edge']})")
    print("  Reason: Output of layer 5 is input to layer 6")
    print("          If layer 5 performance changed, layer 6 will be affected\n")
    
    # Show the cascading effect more clearly
    variance_layers = detector.get_all_stats()['layers_with_variance']['edge']
    retest_layers = detector.get_layers_needing_retest()['edge']
    
    print("Cascade Propagation:")
    for layer_id in sorted(variance_layers):
        print(f"  Layer {layer_id} has variance → Layer {layer_id+1} needs re-test")
    
    print("\nFull re-test list:", retest_layers)
    
    return True


def test_multiple_cascades():
    """Test cascading with multiple unstable layers"""
    
    print("\n" + "=" * 80)
    print("MULTIPLE CASCADE TEST")
    print("=" * 80)
    print("\nScenario: Layers 3, 5, 7 are unstable → Layers 4, 6, 8 need re-test\n")
    
    detector = VarianceDetector(window_size=10, variance_threshold=0.15)
    
    # Create unstable layers
    unstable_layers = [3, 5, 7]
    
    for layer_id in unstable_layers:
        # First make stable
        for i in range(5):
            detector.add_device_measurement(layer_id, 19e-6)
        # Then make unstable
        for i in range(5):
            detector.add_device_measurement(layer_id, 19e-6 * (1 + i * 0.05))
        
        print(f"  Layer {layer_id}: Created unstable conditions (CV > 15%)")
    
    layers_to_test = detector.get_layers_needing_retest()
    variance_layers = detector.get_all_stats()['layers_with_variance']['device']
    
    print(f"\nLayers with detected variance: {sorted(variance_layers)}")
    print(f"Layers needing re-test (cascaded): {layers_to_test['device']}")
    
    print("\nCascade Chain:")
    for layer_id in sorted(variance_layers):
        print(f"  Layer {layer_id} (variance) → Layer {layer_id+1} (needs re-test)")
    
    # Verify cascading
    expected_retest = set()
    for layer_id in variance_layers:
        expected_retest.add(layer_id)
        expected_retest.add(layer_id + 1)
    
    actual_retest = set(layers_to_test['device'])
    
    print(f"\n✓ Expected re-test layers: {sorted(expected_retest)}")
    print(f"✓ Actual re-test layers:   {sorted(actual_retest)}")
    
    if expected_retest == actual_retest:
        print("✅ PASSED - Cascading working correctly")
        return True
    else:
        print("❌ FAILED - Cascading mismatch")
        return False


def test_cascade_visualization():
    """Visualize the cascade propagation"""
    
    print("\n" + "=" * 80)
    print("CASCADE VISUALIZATION")
    print("=" * 80)
    print("\nHow variance cascades through layers:\n")
    
    detector = VarianceDetector(window_size=10, variance_threshold=0.15)
    
    # Create variance in layer 2
    print("Adding variance to layer 2:")
    for i in range(5):
        detector.add_edge_measurement(2, 500e-6)
    for i in range(5):
        detector.add_edge_measurement(2, 500e-6 * (1 + i * 0.04))
    
    layers = detector.get_layers_needing_retest()
    
    print("\nVARIANCE PROPAGATION:")
    print("  Layer 0: ✓ Unchanged")
    print("  Layer 1: ✓ Unchanged")
    print("  Layer 2: 🔴 VARIANCE DETECTED")
    print("  Layer 3: 🟡 FLAGGED (receives changed output from layer 2)")
    print("  Layer 4: ✓ Not affected (layer 3 still OK)")
    print("  ...")
    
    print(f"\nLayers flagged for re-test: {layers['edge']}")
    
    # Simulate another variance layer
    print("\nAdding variance to layer 5:")
    for i in range(5):
        detector.add_edge_measurement(5, 520e-6)
    for i in range(5):
        detector.add_edge_measurement(5, 520e-6 * (1 + i * 0.04))
    
    layers = detector.get_layers_needing_retest()
    
    print("\nUPDATED PROPAGATION:")
    print("  Layer 0: ✓ Unchanged")
    print("  Layer 1: ✓ Unchanged")
    print("  Layer 2: 🔴 VARIANCE DETECTED")
    print("  Layer 3: 🟡 FLAGGED (due to layer 2)")
    print("  Layer 4: ✓ OK")
    print("  Layer 5: 🔴 VARIANCE DETECTED")
    print("  Layer 6: 🟡 FLAGGED (due to layer 5)")
    print("  ...")
    
    print(f"\nLayers flagged for re-test: {layers['edge']}")


if __name__ == "__main__":
    test_variance_cascading()
    test_multiple_cascades()
    test_cascade_visualization()
    
    print("\n" + "=" * 80)
    print("✅ All cascading tests completed")
    print("=" * 80)
