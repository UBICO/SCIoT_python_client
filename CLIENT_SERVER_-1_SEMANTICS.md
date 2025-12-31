# Client-Server "-1" Semantics for Local Inference Mode

## Overview

The local inference mode feature uses a special value `-1` for `offloading_layer` to signal "run all layers locally." This document explains how both the server and client handle this special value.

## Problem Statement

When local inference mode is enabled on the edge server and probabilistically forces all device-local inference:

1. **Server-side**: Needs a way to signal "ignore the normal offloading algorithm, force all layers on device"
2. **Client-side**: Needs to understand that `-1` is a special signal, not an invalid layer index

## Solution

### Server-Side: Sending -1

**File**: [src/server/communication/request_handler.py](src/server/communication/request_handler.py)

When local inference mode forces local execution:

```python
def handle_device_inference_result(self, body, received_timestamp):
    # ... variance tracking ...
    
    # Check if we should force local-only inference for refreshing times
    if self.should_force_local_inference():
        # Force all layers on device (offloading layer = -1)
        best_offloading_layer = -1
        logger.info("Forcing all layers on device for time refresh (local inference mode)")
    else:
        # Normal offloading algorithm
        offloading_algo = OffloadingAlgo(...)
        best_offloading_layer = offloading_algo.static_offloading()
    
    return best_offloading_layer
```

**Key points**:
- Server returns `-1` when `should_force_local_inference()` is True
- Only happens when:
  - `local_inference_mode.enabled = true` in config
  - `random() < local_inference_mode.probability`

### Client-Side: Interpreting -1

**File**: [server_client_light/client/http_client.py](server_client_light/client/http_client.py)

The client's `run_split_inference()` function interprets `-1`:

```python
def run_split_inference(image, tflite_dir, stop_layer):
    input_data = image
    inference_times = []
    
    # Handle -1 as "run all layers until the end"
    if stop_layer == -1:
        stop_layer = LAST_OFFLOADING_LAYER  # Convert to 58 for 59-layer model
        print(f"Offloading layer -1: Running all {stop_layer + 1} layers locally")
    
    for i in range(stop_layer + 1):
        # ... normal inference loop runs all layers 0 to stop_layer ...
```

**Key points**:
- Client checks if received value is `-1`
- If true, converts to `LAST_OFFLOADING_LAYER` (58)
- Proceeds with normal inference loop
- Loop runs from layer 0 to `stop_layer` (inclusive)

## Semantics Reference Table

| Value | Meaning | Behavior | Use Case |
|-------|---------|----------|----------|
| `-1` | Force all local | Device runs all 59 layers (0-58) | Local inference mode forcing |
| `0` | Edge after layer 0 | Device layer 0, edge layers 1-58 | Heavy edge offloading |
| `10` | Edge after layer 10 | Device layers 0-10, edge layers 11-58 | Moderate split |
| `29` | Edge after layer 29 | Device layers 0-29, edge layers 30-58 | Balanced split |
| `58` | All device | Device all 59 layers (0-58) | No offloading (normal) |

## Mathematical Correspondence

For any valid `offloading_layer` value `L`:

**On client side:**
```
if offloading_layer == -1:
    effective_layer = LAST_OFFLOADING_LAYER = 58
else:
    effective_layer = offloading_layer

layers_to_run = range(0, effective_layer + 1)
num_layers = effective_layer + 1
```

**Examples:**
- `-1` → effective_layer = 58 → layers 0-58 (59 layers)
- `0` → effective_layer = 0 → layers 0-0 (1 layer)
- `10` → effective_layer = 10 → layers 0-10 (11 layers)
- `58` → effective_layer = 58 → layers 0-58 (59 layers)

## Complete Flow: Local Inference Mode

```
┌─────────────────────────────────────────────────────────────┐
│ 1. REQUEST ARRIVES AT EDGE SERVER                          │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. SERVER PROCESSES DEVICE INFERENCE RESULT                 │
│    - Track device inference times (EMA)                     │
│    - Track variance in times (CV > 15%)                     │
│    - Check: should_force_local_inference()?                │
└─────────────────────────────────────────────────────────────┘
                         ↓
            ┌────────────┴────────────┐
            ↓                         ↓
        YES (forced)             NO (normal)
            ↓                         ↓
    ┌──────────────┐         ┌──────────────┐
    │ Return -1    │         │ Run offloading
    │ (all local)  │         │ algorithm
    └──────────────┘         └──────────────┘
            ↓                         ↓
    ┌──────────────────────────────────────┐
    │ 3. CLIENT RECEIVES OFFLOADING_LAYER  │
    └──────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────┐
    │ 4. CLIENT INTERPRETS VALUE           │
    │    If -1: convert to 58              │
    │    Else: use as-is                   │
    └──────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────┐
    │ 5. CLIENT RUNS INFERENCE             │
    │    Loop i from 0 to stop_layer       │
    │    (includes forced -1 → 58)         │
    └──────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────┐
    │ 6. DEVICE TIMES COLLECTED            │
    │    All inference times captured      │
    │    Including forced local inference  │
    └──────────────────────────────────────┘
                         ↓
    ┌──────────────────────────────────────┐
    │ 7. TIMES SENT BACK TO EDGE SERVER    │
    │    Updated EMA for all layers        │
    │    Variance detector validates       │
    └──────────────────────────────────────┘
```

## Configuration

Local inference mode is controlled by two parameters in YAML config:

```yaml
local_inference_mode:
  enabled: false              # Enable/disable feature
  probability: 0.1            # P(return -1) on each request
```

**Default behavior** (`enabled: false`):
- Never returns `-1`
- Normal offloading algorithm always used

**Active behavior** (`enabled: true, probability: 0.1`):
- ~10% of requests get `-1`
- Refreshes all device layer times
- Enables variance detection to validate measurements

## Files Involved

### Server-Side
- **[src/server/communication/request_handler.py](src/server/communication/request_handler.py)**
  - `should_force_local_inference()`: Decides whether to return -1
  - `handle_device_inference_result()`: Returns -1 when forced
- **[src/server/settings.yaml](src/server/settings.yaml)**
  - Configuration parameters (enabled, probability)

### Client-Side
- **[server_client_light/client/http_client.py](server_client_light/client/http_client.py)**
  - `run_split_inference()`: Interprets -1 and converts to LAST_OFFLOADING_LAYER
- **[server_client_light/client/http_config.yaml](server_client_light/client/http_config.yaml)**
  - Configuration parameters (same as server)

## Testing & Verification

### Server-Side Test
```python
# Server returns -1 when:
probability = 0.1  # 10%
for request in requests:
    if random.random() < probability:
        return -1  # Force local
    else:
        return calculated_offloading_layer  # Normal
```

### Client-Side Test
```python
# Client interprets -1 correctly
LAST_OFFLOADING_LAYER = 58

for stop_layer in [-1, 0, 10, 58]:
    if stop_layer == -1:
        stop_layer = LAST_OFFLOADING_LAYER
    
    layers_run = list(range(0, stop_layer + 1))
    # -1 → [0..58] (59 layers)
    # 0  → [0] (1 layer)
    # 10 → [0..10] (11 layers)
    # 58 → [0..58] (59 layers)
```

### Integration Test
✅ Server sends -1 correctly  
✅ Client receives and interprets -1 correctly  
✅ Client runs all 59 layers when -1 is received  
✅ Device inference times collected for all layers  
✅ Times sent back to server for EMA update  

## Summary

- **-1 is a special signal** for "force all layers locally"
- **Server sends -1** via probabilistic local inference mode
- **Client interprets -1** by converting to LAST_OFFLOADING_LAYER (58)
- **Loop handles -1 correctly** via `range(stop_layer + 1)`
- **Enables time refresh** for variance detection and system validation

This design ensures the local inference mode transparently forces device-local execution while the client seamlessly handles the special value.

---

**Last Updated**: December 31, 2025  
**Status**: ✅ Complete and Verified  
**Integration**: Fully integrated with local inference mode feature
