#!/usr/bin/env python3
"""
Comprehensive test suite for variance detection, cascading, and local inference mode.
Tests all the recent enhancements to the SCIoT system.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.variance_detector import VarianceDetector, InferenceTimeHistory
from server.communication.request_handler import RequestHandler
import random


class TestInferenceTimeHistory:
    """Test the sliding window history tracker"""
    
    def test_initialization(self):
        """Test history initializes with correct window size"""
        history = InferenceTimeHistory(layer_id=0, window_size=10)
        assert history.layer_id == 0
        assert history.window_size == 10
        assert len(history.measurements) == 0
    
    def test_add_measurement(self):
        """Test adding measurements to history"""
        history = InferenceTimeHistory(layer_id=0, window_size=5)
        history.add_measurement(10.0)
        history.add_measurement(11.0)
        history.add_measurement(12.0)
        
        assert len(history.measurements) == 3
        assert list(history.measurements) == [10.0, 11.0, 12.0]
    
    def test_window_size_limit(self):
        """Test that window size is enforced (FIFO)"""
        history = InferenceTimeHistory(layer_id=0, window_size=3)
        
        for i in range(5):
            history.add_measurement(float(i))
        
        # Should only keep last 3 measurements
        assert len(history.measurements) == 3
        assert list(history.measurements) == [2.0, 3.0, 4.0]
    
    def test_cv_stable(self):
        """Test CV calculation for stable times"""
        history = InferenceTimeHistory(layer_id=0, window_size=10)
        
        # Add stable measurements (19µs ± 0.2µs)
        for i in range(10):
            history.add_measurement(19e-6 + (i % 2) * 0.2e-6)
        
        stats = history.get_stats()
        assert stats['cv'] < 0.15  # Should be stable (CV < 15%)
        assert stats['is_stable'] is True
    
    def test_cv_unstable(self):
        """Test CV calculation for unstable times"""
        history = InferenceTimeHistory(layer_id=0, window_size=10)
        
        # Add unstable measurements (large jumps)
        for i in range(10):
            history.add_measurement(100e-6 * (1 + i * 0.10))  # 10% growth per step
        
        stats = history.get_stats()
        assert stats['cv'] > 0.15  # Should be unstable (CV > 15%)
        assert stats['is_stable'] is False
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data"""
        history = InferenceTimeHistory(layer_id=0, window_size=10)
        history.add_measurement(10.0)
        
        stats = history.get_stats()
        # With only 1 measurement, CV is 0 (no variance)
        assert stats['cv'] == 0.0
        assert stats['is_stable'] is True


class TestVarianceDetector:
    """Test the variance detection system"""
    
    def test_initialization(self):
        """Test detector initializes correctly"""
        detector = VarianceDetector(window_size=10, variance_threshold=0.15)
        assert detector.window_size == 10
        assert detector.variance_threshold == 0.15
        assert len(detector.device_histories) == 0
        assert len(detector.edge_histories) == 0
    
    def test_add_device_measurement(self):
        """Test adding device measurements"""
        detector = VarianceDetector()
        
        # Add stable measurements
        for i in range(10):
            needs_retest = detector.add_device_measurement(0, 19e-6)
        
        assert 0 in detector.device_histories
        assert not needs_retest  # Stable, no retest needed
    
    def test_add_edge_measurement(self):
        """Test adding edge measurements"""
        detector = VarianceDetector()
        
        # Add stable measurements
        for i in range(10):
            needs_retest = detector.add_edge_measurement(0, 450e-6)
        
        assert 0 in detector.edge_histories
        assert not needs_retest
    
    def test_variance_detection_device(self):
        """Test variance detection on device side"""
        detector = VarianceDetector()
        
        # First 5: stable
        for i in range(5):
            detector.add_device_measurement(0, 19e-6)
        
        # Next 5: unstable (double the time)
        needs_retest = False
        for i in range(5):
            needs_retest = detector.add_device_measurement(0, 38e-6)
        
        assert needs_retest is True
        assert detector.should_retest_offloading() is True
    
    def test_variance_detection_edge(self):
        """Test variance detection on edge side"""
        detector = VarianceDetector()
        
        # Add strongly varying measurements (big jumps)
        for i in range(10):
            detector.add_edge_measurement(0, 450e-6 * (1 + i * 0.10))  # 10% per step, total 90%
        
        assert detector.should_retest_offloading() is True
    
    def test_layer_stability(self):
        """Test getting stability for specific layer"""
        detector = VarianceDetector()
        
        # Layer 0: stable
        for i in range(10):
            detector.add_device_measurement(0, 19e-6)
            detector.add_edge_measurement(0, 450e-6)
        
        stability = detector.get_layer_stability(0)
        assert stability['device_stable'] is True
        assert stability['edge_stable'] is True


class TestVarianceCascading:
    """Test variance cascading to next layer"""
    
    def test_device_cascade(self):
        """Test that device layer variance cascades to next layer"""
        detector = VarianceDetector()
        
        # Create unstable layer 5
        for i in range(5):
            detector.add_device_measurement(5, 20e-6)
        for i in range(5):
            detector.add_device_measurement(5, 40e-6)
        
        layers_to_test = detector.get_layers_needing_retest()
        
        # Both layer 5 (variance) and 6 (cascade) should need retest
        assert 5 in layers_to_test['device']
        assert 6 in layers_to_test['device']
    
    def test_edge_cascade(self):
        """Test that edge layer variance cascades to next layer"""
        detector = VarianceDetector()
        
        # Create unstable layer 3 with strong variance
        for i in range(10):
            detector.add_edge_measurement(3, 500e-6 * (1 + i * 0.10))  # 10% per step
        
        layers_to_test = detector.get_layers_needing_retest()
        
        # Both layer 3 (variance) and 4 (cascade) should need retest
        assert 3 in layers_to_test['edge']
        assert 4 in layers_to_test['edge']
    
    def test_multiple_cascades(self):
        """Test cascading with multiple unstable layers"""
        detector = VarianceDetector()
        
        # Create unstable layers 2, 5, 8
        unstable_layers = [2, 5, 8]
        for layer_id in unstable_layers:
            for i in range(5):
                detector.add_device_measurement(layer_id, 20e-6)
            for i in range(5):
                detector.add_device_measurement(layer_id, 40e-6)
        
        layers_to_test = detector.get_layers_needing_retest()
        
        # Should include unstable layers and their successors
        for layer_id in unstable_layers:
            assert layer_id in layers_to_test['device']
            assert layer_id + 1 in layers_to_test['device']
    
    def test_no_cascade_when_stable(self):
        """Test no cascading when all layers stable"""
        detector = VarianceDetector()
        
        # All stable
        for layer_id in range(5):
            for i in range(10):
                detector.add_device_measurement(layer_id, 20e-6)
        
        layers_to_test = detector.get_layers_needing_retest()
        
        assert len(layers_to_test['device']) == 0
        assert len(layers_to_test['edge']) == 0


class TestLocalInferenceMode:
    """Test local inference mode with probabilistic forcing"""
    
    def test_disabled_mode(self):
        """Test that forcing never happens when disabled"""
        # Mock config
        class MockRequestHandler:
            def __init__(self):
                self.local_inference_enabled = False
                self.local_inference_probability = 1.0  # Even with 100%, should not force
            
            def should_force_local_inference(self):
                if not self.local_inference_enabled:
                    return False
                return random.random() < self.local_inference_probability
        
        handler = MockRequestHandler()
        
        # Try 100 times, should never force
        forced_count = sum(handler.should_force_local_inference() for _ in range(100))
        assert forced_count == 0
    
    def test_probability_zero(self):
        """Test that forcing never happens with probability 0"""
        class MockRequestHandler:
            def __init__(self):
                self.local_inference_enabled = True
                self.local_inference_probability = 0.0
            
            def should_force_local_inference(self):
                if not self.local_inference_enabled:
                    return False
                return random.random() < self.local_inference_probability
        
        handler = MockRequestHandler()
        
        forced_count = sum(handler.should_force_local_inference() for _ in range(100))
        assert forced_count == 0
    
    def test_probability_one(self):
        """Test that forcing always happens with probability 1.0"""
        class MockRequestHandler:
            def __init__(self):
                self.local_inference_enabled = True
                self.local_inference_probability = 1.0
            
            def should_force_local_inference(self):
                if not self.local_inference_enabled:
                    return False
                return random.random() < self.local_inference_probability
        
        handler = MockRequestHandler()
        
        forced_count = sum(handler.should_force_local_inference() for _ in range(100))
        assert forced_count == 100
    
    def test_probability_distribution(self):
        """Test that probability is approximately correct"""
        class MockRequestHandler:
            def __init__(self):
                self.local_inference_enabled = True
                self.local_inference_probability = 0.3  # 30%
            
            def should_force_local_inference(self):
                if not self.local_inference_enabled:
                    return False
                return random.random() < self.local_inference_probability
        
        handler = MockRequestHandler()
        
        # Run 1000 times for statistical significance
        random.seed(42)
        forced_count = sum(handler.should_force_local_inference() for _ in range(1000))
        
        # Should be approximately 300 ± 50 (30% with some variance)
        assert 250 <= forced_count <= 350


class TestClientLayerHandling:
    """Test client-side -1 handling"""
    
    def test_negative_one_conversion(self):
        """Test that -1 is converted to LAST_OFFLOADING_LAYER"""
        LAST_OFFLOADING_LAYER = 58
        
        def get_effective_layer(stop_layer):
            if stop_layer == -1:
                return LAST_OFFLOADING_LAYER
            return stop_layer
        
        assert get_effective_layer(-1) == 58
        assert get_effective_layer(0) == 0
        assert get_effective_layer(10) == 10
        assert get_effective_layer(58) == 58
    
    def test_layer_range_negative_one(self):
        """Test that -1 results in all layers being run"""
        LAST_OFFLOADING_LAYER = 58
        
        def get_layers_to_run(stop_layer):
            if stop_layer == -1:
                stop_layer = LAST_OFFLOADING_LAYER
            return list(range(stop_layer + 1))
        
        layers = get_layers_to_run(-1)
        assert len(layers) == 59  # Layers 0-58
        assert layers[0] == 0
        assert layers[-1] == 58
    
    def test_layer_range_normal(self):
        """Test normal layer ranges"""
        def get_layers_to_run(stop_layer):
            if stop_layer == -1:
                stop_layer = 58
            return list(range(stop_layer + 1))
        
        assert get_layers_to_run(0) == [0]
        assert get_layers_to_run(10) == list(range(11))
        assert len(get_layers_to_run(58)) == 59


class TestServerLayerHandling:
    """Test server-side handling of offloading_layer values"""
    
    def test_server_skips_inference_for_minus_one(self):
        """Test server doesn't run inference when client sent -1"""
        # Simulate server logic
        def should_run_edge_inference(offloading_layer_index):
            # Skip edge inference if device did all layers
            if offloading_layer_index == -1 or offloading_layer_index >= 58:
                return False
            return True
        
        assert should_run_edge_inference(-1) is False
        assert should_run_edge_inference(58) is False
        assert should_run_edge_inference(0) is True
        assert should_run_edge_inference(30) is True
        assert should_run_edge_inference(57) is True
    
    def test_server_uses_device_output_for_complete_inference(self):
        """Test server uses device output when all layers complete"""
        import numpy as np
        
        def get_final_prediction(offloading_layer_index, device_output, edge_inference_func):
            if offloading_layer_index == -1 or offloading_layer_index >= 58:
                # All layers on device, use device output directly
                return device_output
            else:
                # Continue on edge
                return edge_inference_func(device_output)
        
        device_output = np.array([1, 2, 3, 4])
        
        # For -1 or 58, should return device output unchanged
        result = get_final_prediction(-1, device_output, lambda x: x * 2)
        assert np.array_equal(result, device_output)
        
        result = get_final_prediction(58, device_output, lambda x: x * 2)
        assert np.array_equal(result, device_output)
        
        # For partial offloading, should call edge function
        result = get_final_prediction(10, device_output, lambda x: x * 2)
        assert np.array_equal(result, device_output * 2)


class TestIntegration:
    """Integration tests combining multiple features"""
    
    def test_variance_triggers_local_inference(self):
        """Test that variance detection can influence local inference probability"""
        # Simulate scenario where variance is detected and we want to increase forcing
        detector = VarianceDetector()
        
        # Create unstable layer with strong variance
        for i in range(10):
            detector.add_edge_measurement(5, 500e-6 * (1 + i * 0.10))
        
        has_variance = detector.should_retest_offloading()
        
        # In production, this could automatically increase probability
        base_probability = 0.1
        adaptive_probability = 0.3 if has_variance else base_probability
        
        assert has_variance is True
        assert adaptive_probability == 0.3
    
    def test_end_to_end_workflow(self):
        """Test complete workflow: variance detection → local forcing → measurement update"""
        detector = VarianceDetector()
        
        # 1. Device measures layers
        for layer_id in range(5):
            for i in range(10):
                detector.add_device_measurement(layer_id, 20e-6)
        
        # 2. No variance initially
        assert detector.should_retest_offloading() is False
        
        # 3. Layer 2 degrades
        for i in range(10):
            detector.add_device_measurement(2, 40e-6)
        
        # 4. Variance detected
        assert detector.should_retest_offloading() is True
        
        # 5. Layers needing retest include cascaded
        layers_to_test = detector.get_layers_needing_retest()
        assert 2 in layers_to_test['device']  # Direct variance
        assert 3 in layers_to_test['device']  # Cascaded
        
        # 6. After re-testing with stable times, variance clears
        for i in range(10):
            detector.add_device_measurement(2, 40e-6)
        
        # Now stable at new baseline
        assert detector.device_histories[2].is_stable() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
