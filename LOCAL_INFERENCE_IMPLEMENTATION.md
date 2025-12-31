# Local Inference Mode - Implementation Summary

## Overview

A probabilistic local inference mode has been implemented to allow the edge server to periodically force the device to run all inference layers locally (no offloading). This enables periodic refresh of device inference times and response to variance detection.

## Problem Solved

**Before:** Device inference times were updated via EMA but could become stale if no offloading occurred. System had no way to force a complete re-test of device performance.

**After:** Edge server can probabilistically force the device to run locally, refreshing all device layer times and validating performance hasn't degraded.

## Implementation

### 1. Configuration Parameters Added

Added to all configuration files:

**`src/server/settings.yaml`:**
```yaml
local_inference_mode:
  enabled: false
  probability: 0.1  # 10% of requests force local
```

**`server_client_light/client/http_config.yaml`:**
```yaml
local_inference_mode:
  enabled: false
  probability: 0.1
```

**`server_client_light/client/websocket_config.yaml`:**
```yaml
local_inference_mode:
  enabled: false
  probability: 0.1
```

### 2. RequestHandler Updates

**File:** `src/server/communication/request_handler.py`

**Added imports:**
```python
import random
```

**Added configuration loading function:**
```python
def load_local_inference_config():
    """Load local inference mode configuration from settings.yaml"""
    settings_path = Path(__file__).parent.parent / "settings.yaml"
    try:
        with open(settings_path, 'r') as f:
            settings = yaml.safe_load(f)
            return settings.get('local_inference_mode', {})
    except Exception as e:
        logger.warning(f"Could not load local inference config: {e}")
        return {'enabled': False, 'probability': 0.0}
```

**Updated RequestHandler.__init__():**
```python
def __init__(self):
    # ... existing network delay loading ...
    
    # Load local inference mode configuration
    local_config = load_local_inference_config()
    self.local_inference_enabled = local_config.get('enabled', False)
    self.local_inference_probability = local_config.get('probability', 0.0)
    if self.local_inference_enabled:
        logger.info(f"Local inference mode enabled with probability {self.local_inference_probability:.0%}")
```

**Added decision method:**
```python
def should_force_local_inference(self) -> bool:
    """
    Determine if this request should force local-only inference.
    
    Returns:
        True if random < probability, False otherwise
    """
    if not self.local_inference_enabled:
        return False
    
    should_force = random.random() < self.local_inference_probability
    
    if should_force:
        logger.info("Forcing local-only inference to refresh device times")
    
    return should_force
```

**Updated handle_device_inference_result():**
```python
def handle_device_inference_result(self, body, received_timestamp):
    # ... existing variance tracking and network delay ...
    
    # Check if variance detected
    if RequestHandler.variance_detector.should_retest_offloading():
        logger.warning("Offloading algorithm may need re-evaluation due to variance")
    
    # Check if we should force local-only inference for refreshing times
    if self.should_force_local_inference():
        # Force all layers on device (offloading layer = -1)
        best_offloading_layer = -1
        logger.info("Forcing all layers on device for time refresh (local inference mode)")
    else:
        # Use normal offloading algorithm
        offloading_algo = OffloadingAlgo(...)
        best_offloading_layer = offloading_algo.static_offloading()
    
    return best_offloading_layer
```

## How It Works

```
Request Arrives
     ↓
Track device inference times (existing)
Track variance (existing)
     ↓
Decide: Force local inference?
     ↓
  Check: enabled=true AND random(0,1) < probability
     ↓
   YES                              NO
    ↓                               ↓
Return -1                      Run offloading
(all on device)                algorithm
    ↓                               ↓
Device refreshes            Return optimal
all layer times             split point
    ↓                               ↓
Times sent to edge          Some device,
in next request             some edge
```

## Key Features

✅ **Probabilistic control** - Only forced sometimes, based on probability  
✅ **Zero overhead when disabled** - No performance impact if `enabled: false`  
✅ **Simple configuration** - Just two parameters (enabled, probability)  
✅ **Integrated with variance detection** - Works alongside variance monitoring  
✅ **Logging** - Clear info messages when forcing occurs  
✅ **Backward compatible** - No breaking changes to existing logic  

## Configuration Guide

### Disabled (Default)
```yaml
local_inference_mode:
  enabled: false
  probability: 0.0
```
- All requests use calculated offloading point
- Device times never forced to refresh

### Conservative (5% local)
```yaml
local_inference_mode:
  enabled: true
  probability: 0.05
```
- ~1 in 20 requests forces local inference
- Gentle, continuous refresh
- Minimal overhead (~5%)

### Moderate (10% local)
```yaml
local_inference_mode:
  enabled: true
  probability: 0.1
```
- ~1 in 10 requests forces local
- Regular time refresh
- Good default for production

### Aggressive (25% local)
```yaml
local_inference_mode:
  enabled: true
  probability: 0.25
```
- ~1 in 4 requests forces local
- Frequent refresh
- Use during variance issues

### Testing (100% local)
```yaml
local_inference_mode:
  enabled: true
  probability: 1.0
```
- All requests run locally
- No offloading at all
- Testing/debugging only

## Behavior Examples

### Probability = 0.1 (10%)

Request sequence (example):
```
Request  1: random=0.03 < 0.1 → Force local 🔴
Request  2: random=0.15 > 0.1 → Use algorithm 🟢
Request  3: random=0.08 < 0.1 → Force local 🔴
Request  4: random=0.25 > 0.1 → Use algorithm 🟢
Request  5: random=0.04 < 0.1 → Force local 🔴
Request  6: random=0.19 > 0.1 → Use algorithm 🟢
Request  7: random=0.12 > 0.1 → Use algorithm ��
Request  8: random=0.06 < 0.1 → Force local 🔴
Request  9: random=0.18 > 0.1 → Use algorithm 🟢
Request 10: random=0.09 < 0.1 → Force local 🔴
```

Result: 4/10 forced local (40% in this sequence, expected ~10%)

### With Variance Detection

**Scenario:** Layer 5 has variance detected
```
Log: "Edge layer 5 variance detected: CV=18.5%"
Log: "Layer 6 should also be re-tested (cascade)"
     ↓
Next request arrives
     ↓
Is it a forced local request?
     ↓
YES → All device layers run locally (including 5, 6)
      Fresh times provided to validator
      
NO  → Normal offloading algorithm runs
      Layer 6 still flagged but lower priority
```

## Integration Points

### With Variance Detection
- Variance detector flags unstable layers (CV > 15%)
- Cascade propagates to next layer
- Local inference mode provides fresh measurements
- Fresh times help validate if variance was real or transient

### With Offloading Algorithm
- Replaces algorithm's output (offloading_layer) when forced
- Returns -1 to force all layers on device
- Device collects all inference times
- Times available for next request's EMA update

### With Delay Simulation
- Independent systems
- Can run together
- Example: Simulate slow device + force local to measure real times

## Files Modified

1. **`src/server/communication/request_handler.py`**
   - Added `import random`
   - Added `load_local_inference_config()` function
   - Modified `RequestHandler.__init__()`
   - Added `should_force_local_inference()` method
   - Modified `handle_device_inference_result()`

2. **`src/server/settings.yaml`**
   - Added `local_inference_mode` section

3. **`server_client_light/client/http_config.yaml`**
   - Added `local_inference_mode` section

4. **`server_client_light/client/websocket_config.yaml`**
   - Added `local_inference_mode` section

## Files Created

1. **`LOCAL_INFERENCE_MODE.md`** (NEW)
   - Complete reference guide
   - Use cases and best practices
   - Configuration examples
   - Troubleshooting guide

2. **`LOCAL_INFERENCE_IMPLEMENTATION.md`** (NEW - this file)
   - Implementation details
   - Architecture explanation

## Testing

All components verified:

✅ Configuration files updated correctly  
✅ RequestHandler initializes with correct parameters  
✅ `should_force_local_inference()` method works  
✅ Probabilistic behavior matches configuration  
✅ Integration with variance detection intact  
✅ No breaking changes to existing code  

## Logging Output

When enabled:

```
Startup:
2025-12-31 12:00:00 - INFO - Local inference mode enabled with probability 10%

On forced request:
2025-12-31 12:00:15 - INFO - Forcing local-only inference to refresh device times
2025-12-31 12:00:15 - INFO - Forcing all layers on device for time refresh

On normal request:
(no additional logging, uses normal offloading algorithm)
```

## Performance Impact

- **When disabled**: Zero overhead
- **When enabled, probability=0.1**: ~10% of requests forced local
  - Device processes all layers (no edge)
  - Fresh inference times captured
  - Minimal impact on system (one in ten requests)

## Use Cases

1. **Continuous monitoring** - `probability: 0.05` for gentle refresh
2. **Variance response** - Increase to `0.2-0.3` when variance detected
3. **System validation** - Daily `0.1` for ongoing monitoring
4. **Debugging** - Set to `1.0` to force all local (testing)
5. **Development** - Test with various probabilities during tuning

## Future Enhancements

- **Time-based forcing** - Force local after N hours instead of probability
- **Variance-triggered forcing** - Automatic increase when variance detected
- **Multiple strategy** - Different probabilities for different scenarios
- **Reporting** - Statistics on how often forced vs normal
- **Adaptive tuning** - Adjust probability based on system health

## Summary

Local Inference Mode provides:

✅ **Periodic device time refresh** - Prevents stale measurements  
✅ **Variance validation** - Fresh times to confirm variance  
✅ **System monitoring** - Regular performance checks  
✅ **Flexible control** - Probability-based forcing  
✅ **Zero overhead** - When disabled  
✅ **Simple to use** - Just enable and set probability  

The system now has three complementary mechanisms:

1. **EMA Smoothing** - Continuous time tracking (existing)
2. **Variance Detection** - Identifies changes (added previously)
3. **Local Inference** - Forces time refresh (added now)

Together, these ensure the offloading algorithm always has accurate, validated inference times.

---

**Implementation Date**: December 31, 2025  
**Status**: ✅ Complete and Tested  
**Integration**: Seamless with existing systems  
**Performance Impact**: Negligible when disabled, configurable when enabled  
**Backward Compatibility**: 100% - no breaking changes
