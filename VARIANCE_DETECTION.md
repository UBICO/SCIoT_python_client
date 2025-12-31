# Inference Time Variance Detection System

## Overview

The variance detection system monitors inference time stability across layers and detects significant performance changes. When times change considerably, it triggers re-evaluation of the offloading algorithm to ensure optimal split decisions.

## Problem Statement

Previously, inference times were computed at runtime using exponential moving average (EMA), but there was no mechanism to detect when times changed significantly. This meant:

- If no offload was performed, measurements were never regenerated
- Constant layers didn't need algorithm re-testing
- Significantly changing layers required immediate re-evaluation
- The offloading split point might become suboptimal over time

## Solution Architecture

### Core Components

#### 1. **InferenceTimeHistory** Class
Tracks measurement history for a single layer using a sliding window.

**Features:**
- Maintains last 10 measurements per layer (configurable)
- Calculates coefficient of variation (CV) to assess stability
- CV = (standard deviation / mean) - normalized measure independent of absolute scale
- Threshold: 15% CV (0.15) - values above trigger re-test notification

**Methods:**
```python
# Add a measurement and check for variance
needs_retest = history.add_measurement(time=0.5e-3)

# Get stability status
is_stable = history.is_stable()

# Get detailed statistics
stats = history.get_stats()
# Returns: {
#   'layer_id': 0,
#   'measurements': 10,
#   'mean': 0.00052,
#   'stdev': 0.00008,
#   'cv': 0.154,  # 15.4% - just above threshold
#   'is_stable': False,
#   'min': 0.00045,
#   'max': 0.00068
# }
```

#### 2. **VarianceDetector** Class
Central monitoring system for device and edge inference times.

**Features:**
- Separate tracking for device and edge inference times
- Per-layer history management
- Automatic re-test flagging when variance exceeds threshold
- **Layer cascading**: Automatically flags next layer when variance detected
- Shared across all requests (class-level instance)

**Methods:**
```python
# Add device measurement (called from request handler)
needs_retest = variance_detector.add_device_measurement(layer_id=5, time=0.000019)

# Add edge measurement (called from model manager during inference)
needs_retest = variance_detector.add_edge_measurement(layer_id=5, time=0.000512)

# Check if offloading algorithm should be re-evaluated
should_retest = variance_detector.should_retest_offloading()

# Get layers that need re-testing (includes cascaded layers)
layers_to_test = variance_detector.get_layers_needing_retest()
# Returns: {'device': [2, 3, 5, 6], 'edge': [7, 8]}
# Layer 3 in device list because layer 2 has variance (cascade)
# Layer 8 in edge list because layer 7 has variance (cascade)

# Get stability status for a specific layer
stability = variance_detector.get_layer_stability(layer_id=5)
# Returns: {'device_stable': True, 'edge_stable': False}

# Get all statistics for monitoring/analysis
all_stats = variance_detector.get_all_stats()
# Returns dict with stats, variance layers, and layers needing re-test
```

### Integration Points

#### 1. **Request Handler** (src/server/communication/request_handler.py)

**Added class-level variance detector:**
```python
class RequestHandler:
    variance_detector = VarianceDetector(window_size=10, variance_threshold=0.15)
```

**In `handle_device_inference_result()`:**
```python
# Track each device inference time
for l_id, inference_time in enumerate(message_data.device_layers_inference_time):
    # ... existing EMA smoothing code ...
    
    # NEW: Track variance for this layer
    RequestHandler.variance_detector.add_device_measurement(l_id, inference_time)

# NEW: Check if variance detected
if RequestHandler.variance_detector.should_retest_offloading():
    logger.warning("Offloading algorithm may need re-evaluation due to inference time variance")

# Proceed with existing offloading algorithm
offloading_algo = OffloadingAlgo(...)
```

#### 2. **Model Manager** (src/server/models/model_manager.py)

**Added variance detector parameter:**
```python
def __init__(self, ..., variance_detector: VarianceDetector = None):
    self.variance_detector = variance_detector
```

**In `track_inference_time` decorator:**
```python
# NEW: Track variance for edge inference times
if hasattr(self, 'variance_detector') and self.variance_detector:
    self.variance_detector.add_edge_measurement(int(layer_key), elapsed_time)
```

#### 3. **Edge Initialization** (src/server/edge/edge_initialization.py)

**Added class-level variance detector:**
```python
class Edge:
    variance_detector = VarianceDetector(window_size=10, variance_threshold=0.15)
```

**Pass to ModelManager instances:**
```python
model_manager = ModelManager(
    ...,
    variance_detector=Edge.variance_detector
)
```

## Statistical Foundation

### Coefficient of Variation (CV)

CV is used to detect instability because:

1. **Scale-independent**: Works for both device (µs scale) and edge (100s of µs scale) times
2. **Normalized**: Directly comparable across layers
3. **Intuitive**: Low CV = stable, high CV = changing

**Example:**

```
Device Layer 0:
  Measurements: [19µs, 18µs, 19.5µs, 20µs, 18.5µs]
  Mean: 19.0µs
  StDev: 0.84µs
  CV: 0.84/19 = 4.4% → STABLE ✓

Edge Layer 0:
  Measurements: [520µs, 450µs, 380µs, 520µs, 460µs]
  Mean: 466µs
  StDev: 55.6µs
  CV: 55.6/466 = 11.9% → STABLE ✓

Edge Layer 15 (changing conditions):
  Measurements: [450µs, 480µs, 520µs, 580µs, 600µs]
  Mean: 526µs
  StDev: 60.8µs
  CV: 60.8/526 = 11.6% → STABLE at sample size 5
  
  Continue monitoring with next 5:
  [650µs, 680µs, 700µs, 720µs, 750µs]
  Mean: 700µs
  StDev: 36.1µs
  CV: 36.1/700 = 5.2% → but mean increased by 33%! → VARIANCE DETECTED ✗
```

### Window Size (10 measurements)

- Large enough for statistical significance (n≥10)
- Small enough for responsive detection (changes within ~10 inferences)
- Memory efficient
- Good balance between noise filtering and recency

### Threshold (15%)

- Conservative: Tolerates normal measurement noise
- Below 15%: Confident layer is stable
- Above 15%: Evidence of real performance change
- Configurable per deployment needs

## Workflow

```
Device Inference → Update Device Times (EMA) → Track Variance
                                                     ↓
                                            Check: CV > 15%?
                                                     ↓
                                        YES → Flag: device_needs_retest
                                             Flag: layer i+1 (cascade)
                                                     ↓
                                        NO → Continue

Edge Inference → Update Edge Times (EMA) → Track Variance
                                                ↓
                                        Check: CV > 15%?
                                                ↓
                                      YES → Flag: edge_needs_retest
                                           Flag: layer i+1 (cascade)
                                                ↓
                                      NO → Continue

After Device Inference:
  should_retest = variance_detector.should_retest_offloading()
  
  if should_retest:
    layers_to_test = variance_detector.get_layers_needing_retest()
    # layers_to_test['device'] and ['edge'] include cascaded layers
    
    # Currently: Log warning with affected layers
    # Future: Could trigger background re-evaluation task with only affected layers
    logger.warning(f"Offloading may need re-evaluation. Device: {layers_to_test['device']}, Edge: {layers_to_test['edge']}")
```

### Layer Cascading

When layer `i` has significant variance in inference times, layer `i+1` is automatically flagged for re-testing because:

1. **Output becomes input**: The output of layer `i` is the input to layer `i+1`
2. **Changed characteristics**: If layer `i` performance changes, its output characteristics may change
3. **Downstream effects**: Layer `i+1` may behave differently with the new input characteristics

**Example:**
```
Layer 5 (Edge): Inference time increases from 500µs to 700µs
  ↓
  CV calculated: 18% > 15% (threshold) → VARIANCE DETECTED
  ↓
  Flags layer 5 for re-testing
  Automatically flags layer 6 for re-testing (cascade)
  
Reason: Layer 6 receives different outputs from layer 5
        This may affect layer 6's inference behavior and performance
```

## Usage Examples

### 1. Checking Layer Stability

```python
from server.communication.request_handler import RequestHandler

# Check if a specific layer is stable
stability = RequestHandler.variance_detector.get_layer_stability(layer_id=10)

if stability['device_stable'] and stability['edge_stable']:
    print("Layer 10 is stable - no re-evaluation needed")
elif not stability['device_stable']:
    print("Layer 10 device times are changing")
elif not stability['edge_stable']:
    print("Layer 10 edge times are changing")
```

### 2. Monitoring Overall System Health

```python
# Get comprehensive statistics
stats = RequestHandler.variance_detector.get_all_stats()

# Analyze device stability
for layer_id, layer_stats in stats['device'].items():
    if not layer_stats['is_stable']:
        print(f"Device Layer {layer_id}: CV={layer_stats['cv']:.2%}")

# Analyze edge stability
for layer_id, layer_stats in stats['edge'].items():
    if not layer_stats['is_stable']:
        print(f"Edge Layer {layer_id}: CV={layer_stats['cv']:.2%}")

# Check if re-test needed
if stats['needs_retest']:
    print("System detected inference time variance")
```

### 3. Custom Threshold Configuration

```python
from server.variance_detector import VarianceDetector

# Tighter threshold for stable systems
detector = VarianceDetector(window_size=10, variance_threshold=0.10)  # 10% CV

# Looser threshold for variable environments
detector = VarianceDetector(window_size=10, variance_threshold=0.25)  # 25% CV
```

## Future Enhancements

### Possible Improvements

1. **Adaptive Re-testing**
   - Current: Only logs warning
   - Future: Could trigger background task to re-evaluate offloading algorithm

2. **Time-based History**
   - Current: Last 10 measurements (any time span)
   - Future: Last N seconds of measurements (more relevant to recent conditions)

3. **Multi-layer Correlation**
   - Detect if multiple consecutive layers are changing together
   - Might indicate system-wide load vs. layer-specific issues

4. **Predictive Variance**
   - Use trend analysis to predict future variance
   - Trigger re-evaluation before performance degrades

5. **Performance Metrics Dashboard**
   - Real-time visualization of CV per layer
   - Alert when thresholds exceeded

## Debugging and Monitoring

### Log Messages

```
# When variance detected (WARNING level)
Edge layer 15 variance detected: CV=18.5% (threshold=15.0%)

# When re-test recommended (WARNING level)
Offloading algorithm may need re-evaluation due to inference time variance

# When enabling delay simulation (INFO level)
Computation delay simulation enabled: static 200ms
```

### Access Variance Data

```python
from server.communication.request_handler import RequestHandler

detector = RequestHandler.variance_detector

# Get all statistics as dictionary
stats = detector.get_all_stats()

# Check specific layer
device_layer_10 = stats['device'].get(10)
if device_layer_10:
    print(f"Layer 10 Device: mean={device_layer_10['mean']:.2e}s, CV={device_layer_10['cv']:.2%}")

# Check if re-test triggered
if stats['needs_retest']:
    print("Re-test flag is active")
```

## Summary

The variance detection system provides:

✅ **Automatic monitoring** of inference time stability  
✅ **Scale-independent metric** (CV) for comparison  
✅ **Per-layer history** tracking recent 10 measurements  
✅ **Intelligent flagging** when performance changes significantly  
✅ **Integration with existing systems** (no disruption to current flow)  
✅ **Extensible architecture** for future enhancements  

This enables the system to detect when offloading decisions might become suboptimal and signal when re-evaluation is needed.
