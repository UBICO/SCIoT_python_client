"""
Inference Time Variance Detector
Monitors inference time changes and detects when layer performance has changed significantly.
Triggers re-evaluation of offloading decisions when variance is detected.
"""

from collections import deque
from typing import Dict, Optional
import statistics
from server.logger.log import logger


class InferenceTimeHistory:
    """Tracks history of inference times for a single layer"""
    
    def __init__(self, layer_id: int, window_size: int = 10):
        """
        Initialize history tracker for a layer.
        
        Args:
            layer_id: Layer identifier
            window_size: Number of measurements to keep in history
        """
        self.layer_id = layer_id
        self.window_size = window_size
        self.measurements = deque(maxlen=window_size)
        self.variance_threshold = 0.15  # 15% coefficient of variation threshold
        self.last_reported_mean = None
    
    def add_measurement(self, time: float) -> bool:
        """
        Add a measurement and check for significant variance.
        
        Args:
            time: Inference time in seconds
            
        Returns:
            True if variance is significant (re-test needed), False otherwise
        """
        self.measurements.append(time)
        
        # Need at least 3 measurements for variance analysis
        if len(self.measurements) < 3:
            return False
        
        return self._has_significant_variance()
    
    def _has_significant_variance(self) -> bool:
        """
        Check if measurements show significant variance.
        Uses coefficient of variation (std_dev / mean).
        
        Returns:
            True if CV > threshold, False otherwise
        """
        if len(self.measurements) < 3:
            return False
        
        measurements_list = list(self.measurements)
        mean = statistics.mean(measurements_list)
        stdev = statistics.stdev(measurements_list)
        
        # Coefficient of Variation
        cv = stdev / mean if mean > 0 else 0
        
        return cv > self.variance_threshold
    
    def is_stable(self) -> bool:
        """
        Check if layer performance is stable (low variance).
        
        Returns:
            True if variance is low, False if changing
        """
        if len(self.measurements) < 3:
            return False
        
        measurements_list = list(self.measurements)
        mean = statistics.mean(measurements_list)
        stdev = statistics.stdev(measurements_list)
        cv = stdev / mean if mean > 0 else 0
        
        return cv <= self.variance_threshold
    
    def get_stats(self) -> Dict:
        """Get statistics about the measurements"""
        if len(self.measurements) == 0:
            return {
                'layer_id': self.layer_id,
                'measurements': 0,
                'mean': 0,
                'stdev': 0,
                'cv': 0,
                'is_stable': False
            }
        
        measurements_list = list(self.measurements)
        mean = statistics.mean(measurements_list)
        stdev = statistics.stdev(measurements_list) if len(measurements_list) > 1 else 0
        cv = stdev / mean if mean > 0 else 0
        
        return {
            'layer_id': self.layer_id,
            'measurements': len(self.measurements),
            'mean': mean,
            'stdev': stdev,
            'cv': cv,
            'is_stable': cv <= self.variance_threshold,
            'min': min(measurements_list),
            'max': max(measurements_list)
        }


class VarianceDetector:
    """
    Monitors variance in device and edge inference times.
    Detects when performance has changed significantly.
    Propagates variance detection to next layer since output of layer i
    becomes input to layer i+1.
    """
    
    def __init__(self, window_size: int = 10, variance_threshold: float = 0.15):
        """
        Initialize variance detector.
        
        Args:
            window_size: Number of measurements to track per layer
            variance_threshold: Coefficient of variation threshold (0.15 = 15%)
        """
        self.window_size = window_size
        self.variance_threshold = variance_threshold
        self.device_histories: Dict[int, InferenceTimeHistory] = {}
        self.edge_histories: Dict[int, InferenceTimeHistory] = {}
        self.device_needs_retest = False
        self.edge_needs_retest = False
        # Track which layers have variance (for propagation to next layer)
        self.device_variance_layers: set = set()  # Layers with detected variance
        self.edge_variance_layers: set = set()    # Layers with detected variance
    
    def add_device_measurement(self, layer_id: int, time: float) -> bool:
        """
        Add device inference time measurement.
        
        Args:
            layer_id: Layer identifier
            time: Inference time in seconds
            
        Returns:
            True if re-test needed, False otherwise
        """
        if layer_id not in self.device_histories:
            self.device_histories[layer_id] = InferenceTimeHistory(
                layer_id, self.window_size
            )
            self.device_histories[layer_id].variance_threshold = self.variance_threshold
        
        needs_retest = self.device_histories[layer_id].add_measurement(time)
        
        if needs_retest:
            self.device_needs_retest = True
            # Track which layer has variance
            self.device_variance_layers.add(layer_id)
            stats = self.device_histories[layer_id].get_stats()
            logger.warning(
                f"Device layer {layer_id} variance detected: "
                f"CV={stats['cv']:.2%} (threshold={self.variance_threshold:.2%}) - "
                f"Layer {layer_id+1} should also be re-tested"
            )
        
        return needs_retest
    
    def add_edge_measurement(self, layer_id: int, time: float) -> bool:
        """
        Add edge inference time measurement.
        
        Args:
            layer_id: Layer identifier
            time: Inference time in seconds
            
        Returns:
            True if re-test needed, False otherwise
        """
        if layer_id not in self.edge_histories:
            self.edge_histories[layer_id] = InferenceTimeHistory(
                layer_id, self.window_size
            )
            self.edge_histories[layer_id].variance_threshold = self.variance_threshold
        
        needs_retest = self.edge_histories[layer_id].add_measurement(time)
        
        if needs_retest:
            self.edge_needs_retest = True
            # Track which layer has variance
            self.edge_variance_layers.add(layer_id)
            stats = self.edge_histories[layer_id].get_stats()
            logger.warning(
                f"Edge layer {layer_id} variance detected: "
                f"CV={stats['cv']:.2%} (threshold={self.variance_threshold:.2%}) - "
                f"Layer {layer_id+1} should also be re-tested"
            )
        
        return needs_retest
    
    def get_layers_needing_retest(self) -> Dict[str, set]:
        """
        Get all layers that need re-testing, including propagated ones.
        If layer i has variance, layer i+1 should also be re-tested since
        the output of layer i becomes the input to layer i+1.
        
        Returns:
            Dict with 'device' and 'edge' keys, each containing set of layer IDs
        """
        # Start with directly detected variance
        device_to_retest = set(self.device_variance_layers)
        edge_to_retest = set(self.edge_variance_layers)
        
        # Propagate to next layer: if layer i has variance, test layer i+1
        for layer_id in self.device_variance_layers:
            device_to_retest.add(layer_id + 1)
        
        for layer_id in self.edge_variance_layers:
            edge_to_retest.add(layer_id + 1)
        
        return {
            'device': sorted(device_to_retest),
            'edge': sorted(edge_to_retest)
        }
    
    def should_retest_offloading(self) -> bool:
        """
        Determine if offloading algorithm should be re-evaluated.
        
        Returns:
            True if variance detected in either device or edge, False otherwise
        """
        needs_retest = self.device_needs_retest or self.edge_needs_retest
        
        if needs_retest:
            layers_to_test = self.get_layers_needing_retest()
            logger.info(
                f"Offloading re-test needed due to inference time variance. "
                f"Device layers: {layers_to_test['device']}, "
                f"Edge layers: {layers_to_test['edge']}"
            )
            # Reset flags after reporting
            self.device_needs_retest = False
            self.edge_needs_retest = False
        
        return needs_retest
    
    def get_layer_stability(self, layer_id: int) -> Dict[str, bool]:
        """
        Get stability status for a layer.
        
        Args:
            layer_id: Layer identifier
            
        Returns:
            Dict with device_stable and edge_stable booleans
        """
        return {
            'device_stable': (layer_id in self.device_histories and 
                            self.device_histories[layer_id].is_stable()),
            'edge_stable': (layer_id in self.edge_histories and 
                          self.edge_histories[layer_id].is_stable())
        }
    
    def get_all_stats(self) -> Dict:
        """Get statistics for all tracked layers"""
        layers_to_test = self.get_layers_needing_retest()
        return {
            'device': {
                layer_id: hist.get_stats() 
                for layer_id, hist in self.device_histories.items()
            },
            'edge': {
                layer_id: hist.get_stats() 
                for layer_id, hist in self.edge_histories.items()
            },
            'needs_retest': self.device_needs_retest or self.edge_needs_retest,
            'layers_with_variance': {
                'device': sorted(self.device_variance_layers),
                'edge': sorted(self.edge_variance_layers)
            },
            'layers_needing_retest': layers_to_test
        }
