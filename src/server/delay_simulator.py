"""
Delay Simulator for SCIoT
Simulates artificial delays for computation and network to test system behavior
under different conditions.
"""

import time
import random
from typing import Optional, Dict, Any
from enum import Enum


class DelayType(Enum):
    """Types of delay distributions."""
    NONE = "none"
    STATIC = "static"
    GAUSSIAN = "gaussian"
    UNIFORM = "uniform"
    EXPONENTIAL = "exponential"


class DelaySimulator:
    """
    Simulates artificial delays for computation and network operations.
    
    Supports multiple delay types:
    - static: Fixed delay
    - gaussian: Normal distribution with mean and std dev
    - uniform: Uniform distribution between min and max
    - exponential: Exponential distribution with mean
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize delay simulator with configuration.
        
        Args:
            config: Dictionary with delay configuration
                {
                    'type': 'static' | 'gaussian' | 'uniform' | 'exponential' | 'none',
                    'value': float (for static),
                    'mean': float (for gaussian/exponential),
                    'std_dev': float (for gaussian),
                    'min': float (for uniform),
                    'max': float (for uniform)
                }
        """
        self.config = config or {}
        self.enabled = config is not None and config.get('enabled', False)
        self.delay_type = DelayType(config.get('type', 'none')) if self.enabled else DelayType.NONE
    
    def apply_delay(self) -> float:
        """
        Apply the configured delay.
        
        Returns:
            The actual delay applied in seconds
        """
        if not self.enabled or self.delay_type == DelayType.NONE:
            return 0.0
        
        delay = self._calculate_delay()
        if delay > 0:
            time.sleep(delay)
        return delay
    
    def _calculate_delay(self) -> float:
        """Calculate delay based on configuration."""
        if self.delay_type == DelayType.STATIC:
            return self.config.get('value', 0.0)
        
        elif self.delay_type == DelayType.GAUSSIAN:
            mean = self.config.get('mean', 0.0)
            std_dev = self.config.get('std_dev', 0.0)
            # Ensure non-negative delay
            delay = random.gauss(mean, std_dev)
            return max(0.0, delay)
        
        elif self.delay_type == DelayType.UNIFORM:
            min_val = self.config.get('min', 0.0)
            max_val = self.config.get('max', 0.0)
            return random.uniform(min_val, max_val)
        
        elif self.delay_type == DelayType.EXPONENTIAL:
            mean = self.config.get('mean', 0.0)
            if mean > 0:
                return random.expovariate(1.0 / mean)
            return 0.0
        
        return 0.0
    
    def get_delay_info(self) -> str:
        """Get human-readable description of delay configuration."""
        if not self.enabled or self.delay_type == DelayType.NONE:
            return "No delay"
        
        if self.delay_type == DelayType.STATIC:
            return f"Static delay: {self.config.get('value', 0.0)*1000:.2f}ms"
        
        elif self.delay_type == DelayType.GAUSSIAN:
            mean = self.config.get('mean', 0.0)
            std_dev = self.config.get('std_dev', 0.0)
            return f"Gaussian delay: μ={mean*1000:.2f}ms, σ={std_dev*1000:.2f}ms"
        
        elif self.delay_type == DelayType.UNIFORM:
            min_val = self.config.get('min', 0.0)
            max_val = self.config.get('max', 0.0)
            return f"Uniform delay: [{min_val*1000:.2f}ms, {max_val*1000:.2f}ms]"
        
        elif self.delay_type == DelayType.EXPONENTIAL:
            mean = self.config.get('mean', 0.0)
            return f"Exponential delay: λ={1.0/mean if mean > 0 else 0:.2f}, μ={mean*1000:.2f}ms"
        
        return "Unknown delay type"


def create_delay_simulator(config: Optional[Dict[str, Any]]) -> DelaySimulator:
    """Factory function to create delay simulator from config."""
    return DelaySimulator(config)
