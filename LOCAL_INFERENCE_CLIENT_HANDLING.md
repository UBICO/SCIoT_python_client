# Local Inference Mode - Client Handling

## Problem

When the server forces local-only inference by returning `offloading_layer = -1`, the client needs to understand this special value means "run all layers locally until the end" rather than an invalid layer index.

## Solution

The HTTP client's `run_split_inference()` function now handles `-1` as a special case:

```python
def run_split_inference(image, tflite_dir, stop_layer):
    input_data = image
    inference_times = []
    
    # Handle -1 as "run all layers until the end"
    if stop_layer == -1:
        stop_layer = LAST_OFFLOADING_LAYER
        print(f"Offloading layer -1: Running all {stop_layer + 1} layers locally")
    
    for i in range(stop_layer + 1):
        # ... normal inference loop ...
```

## Behavior

| Offloading Layer | Interpretation | Result |
|------------------|-----------------|--------|
| `-1` | Force local | Run all 59 layers (0-58) on device |
| `0` | Edge inference after layer 0 | Run layer 0 on device, rest on edge |
| `10` | Edge inference after layer 10 | Run layers 0-10 on device, rest on edge |
| `58` | All device (normal end) | Run all 59 layers (0-58) on device |

## Key Points

✅ **Special value -1** - Only used by local inference mode to force all-device inference  
✅ **No change to other values** - All normal offloading points work as before  
✅ **Clear logging** - Print statement indicates when -1 is being used  
✅ **Matches model structure** - FOMO 96x96 has 59 total layers (0-58)  

## Files Modified

- [src/server/communication/request_handler.py](src/server/communication/request_handler.py) - Server side (returns -1)
- [server_client_light/client/http_client.py](server_client_light/client/http_client.py) - Client side (handles -1)

## Testing

Verified behavior:
```
Test Case 1: Normal offloading layer 10
  → Runs layers 0-10 (11 layers total) ✓

Test Case 2: Normal offloading layer 0
  → Runs layer 0 (1 layer total) ✓

Test Case 3: Force all layers (-1)
  → Runs layers 0-58 (59 layers total) ✓

Test Case 4: Last layer offloading
  → Runs layers 0-58 (59 layers total) ✓
```

## Integration with Local Inference Mode

**Flow:**
```
Server: Local inference mode enabled with probability P
     ↓
Request arrives
     ↓
Server decides: random < P?
     ├─ YES → Return offloading_layer = -1
     └─ NO  → Return calculated offloading_layer
     ↓
Client receives offloading_layer value
     ↓
In run_split_inference():
     ├─ If value is -1 → Convert to LAST_OFFLOADING_LAYER (58)
     ├─ Otherwise     → Use value as-is
     ↓
Run inference from layer 0 to stop_layer
     ↓
Collect all device inference times
     ↓
Send times back to server
```

## Summary

The client now correctly interprets `-1` as "run all layers locally," enabling the local inference mode feature to work end-to-end. All device inference times are collected and sent back to the edge server for variance tracking and offloading algorithm optimization.
