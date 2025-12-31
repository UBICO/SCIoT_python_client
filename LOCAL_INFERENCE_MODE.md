# Local Inference Mode - Reference

## Overview

Local Inference Mode allows the edge server to periodically force the device to run all inference layers locally (no offloading) to refresh and validate device inference times. This is useful for:

1. **Regular time refreshing** - Ensures device times don't become stale
2. **Variance mitigation** - Provides fresh measurements when variance is detected
3. **System monitoring** - Verifies device performance hasn't degraded

## Configuration

### Enabling Local Inference Mode

**In `src/server/settings.yaml`:**
```yaml
local_inference_mode:
  enabled: true                # Enable the feature
  probability: 0.1            # 10% of requests force local inference
```

**In client configs** (`http_config.yaml`, `websocket_config.yaml`):
```yaml
local_inference_mode:
  enabled: true
  probability: 0.1
```

### Parameters

- **`enabled`** (boolean)
  - `true`: Feature is active
  - `false`: Feature is disabled (no local inference forcing)

- **`probability`** (float, 0.0 - 1.0)
  - Probability of forcing local inference on each request
  - `0.0`: Never force local (0% of requests)
  - `0.1`: Force local ~10% of requests (1 in 10)
  - `0.5`: Force local ~50% of requests (1 in 2)
  - `1.0`: Always force local (100% of requests)

## How It Works

```
Request arrives
     ↓
Check: Should force local inference?
     ↓
   [Random(0,1) < probability]
     ↓
     ├─ YES (e.g., random=0.07, probability=0.1)
     │  └─→ Force offloading_layer = -1
     │      (all layers run on device)
     │      └─→ Device refreshes all layer times
     │          └─→ Times sent back to edge
     │
     └─ NO (e.g., random=0.15, probability=0.1)
        └─→ Use normal offloading algorithm
            └─→ Split at calculated optimal layer
                └─→ Some layers on device, some on edge
```

## Use Cases

### 1. Periodic Time Refresh

**Configuration:**
```yaml
local_inference_mode:
  enabled: true
  probability: 0.05  # ~5% = once every ~20 requests
```

**Benefit:** Device times stay fresh and accurate for offloading decisions

### 2. Variance Response

When variance is detected (CV > 15%):
- System logs warning about variance
- Next requests have chance to force local inference
- Provides fresh measurements to validate variance

**Configuration:**
```yaml
local_inference_mode:
  enabled: true
  probability: 0.2   # 20% to force local more often
```

### 3. System Validation

Run periodically to verify device performance hasn't degraded:

**Configuration:**
```yaml
local_inference_mode:
  enabled: true
  probability: 0.1   # Daily validation (~10% of requests)
```

### 4. Testing/Debugging

Force all requests to run locally temporarily:

**Configuration:**
```yaml
local_inference_mode:
  enabled: true
  probability: 1.0   # 100% - always local (testing only!)
```

## Implementation Details

### RequestHandler Changes

```python
class RequestHandler:
    def __init__(self):
        # Load local inference configuration
        local_config = load_local_inference_config()
        self.local_inference_enabled = local_config.get('enabled', False)
        self.local_inference_probability = local_config.get('probability', 0.0)
    
    def should_force_local_inference(self) -> bool:
        """
        Randomly decide whether to force local-only inference
        
        Returns:
            True if random < probability, False otherwise
        """
        if not self.local_inference_enabled:
            return False
        
        should_force = random.random() < self.local_inference_probability
        
        if should_force:
            logger.info("Forcing local-only inference to refresh device times")
        
        return should_force
    
    def handle_device_inference_result(self, ...):
        # ... track variance, etc ...
        
        # Check if we should force local-only inference
        if self.should_force_local_inference():
            # Force all layers on device (no offloading)
            best_offloading_layer = -1
            logger.info("Forcing all layers on device for time refresh")
        else:
            # Use normal offloading algorithm
            best_offloading_layer = offloading_algo.static_offloading()
        
        return best_offloading_layer
```

### Offloading Layer Value

- **`-1`**: Force all layers on device (no edge processing)
- **`0-57`**: Normal split points (layer 0-57 on device, 58+ on edge)
- **`58+`**: Force all on edge (less common)

## Monitoring

### Logging

When local inference is forced:
```
2025-12-31 12:00:00 - INFO - Local inference mode enabled with probability 10%
2025-12-31 12:00:15 - INFO - Forcing local-only inference to refresh device times
2025-12-31 12:00:15 - INFO - Forcing all layers on device for time refresh
```

### Tracking

The system logs:
1. Mode enabled message (on startup)
2. Force decision (when triggered)
3. All layer inference times (normal measurement tracking)

### Analysis

Access variance detector to see impact:
```python
from server.communication.request_handler import RequestHandler

stats = RequestHandler.variance_detector.get_all_stats()
print(f"Device layers with data: {len(stats['device'])}")
print(f"Edge layers with data: {len(stats['edge'])}")
```

## Example Scenarios

### Scenario 1: Normal Operation (disabled)
```yaml
enabled: false
probability: 0.0
```
- All requests use calculated offloading point
- Device times accumulate via EMA smoothing
- No forced local inference

### Scenario 2: Conservative Refresh (5%)
```yaml
enabled: true
probability: 0.05
```
- 5 out of 100 requests force local inference
- Device gets fresh measurements regularly
- Minimal performance impact (~5% overhead)

### Scenario 3: Aggressive Refresh (25%)
```yaml
enabled: true
probability: 0.25
```
- 25 out of 100 requests force local inference
- Frequent time refreshing
- More network traffic from device
- Useful during development/tuning

### Scenario 4: Variance Recovery (50%)
```yaml
enabled: true
probability: 0.5
```
- Half of requests force local inference
- Rapidly refresh all device times
- Used temporarily after detecting high variance
- Disable after variance settles

## Integration with Variance Detection

**Workflow:**
```
1. Variance detector identifies layer with CV > 15%
   └─→ Logs warning: "Layer 5 variance detected"
   └─→ Also flags layer 6 (cascade)

2. With local inference mode enabled:
   └─→ Next requests have chance to force local inference
   └─→ Device runs all layers, providing fresh times
   └─→ Fresh times included in variance calculation
   └─→ If CV drops below 15%, layer is re-stabilized
   └─→ Cascade flag for layer 6 remains useful

3. Normal operation resumes
   └─→ Offloading algorithm works with validated times
```

## Best Practices

1. **Start with disabled** - Use only when variance is detected
2. **Use low probability** - 5-10% for continuous operation
3. **Monitor the logs** - Check if forcing happens as expected
4. **During debugging** - Use 100% probability to force all local
5. **With variance** - Increase probability to 20-30% temporarily
6. **After fixing issues** - Return to 5-10% probability

## Configuration Template

```yaml
# For production (normal conditions)
local_inference_mode:
  enabled: true
  probability: 0.05      # Gentle refresh, ~5% local

# For variance response
local_inference_mode:
  enabled: true
  probability: 0.25      # More aggressive, ~25% local

# For testing
local_inference_mode:
  enabled: true
  probability: 1.0       # Force all local (testing only!)

# Disabled
local_inference_mode:
  enabled: false
  probability: 0.0       # No forcing
```

## Troubleshooting

### Issue: Device times not refreshing
**Check:**
- Is `enabled: true`?
- Is `probability > 0`?
- Check logs for "Forcing local-only inference" messages

### Issue: Too much local inference happening
**Solution:**
- Reduce probability (e.g., 0.5 → 0.1)
- Or set `enabled: false` temporarily

### Issue: Device times becoming stale again
**Solution:**
- Increase probability (e.g., 0.05 → 0.1)
- Or temporarily set to 0.25 to refresh faster

## Summary

Local Inference Mode provides:

✅ **Periodic device time refresh** - Prevents stale measurements  
✅ **Variance response** - Fresh times to validate changes  
✅ **System validation** - Periodic local-only runs for verification  
✅ **Probabilistic control** - No performance impact when disabled  
✅ **Simple configuration** - Just two parameters  
✅ **Integrated monitoring** - Works with variance detection system  

Use in combination with variance detection to maintain optimal offloading decisions over time.
