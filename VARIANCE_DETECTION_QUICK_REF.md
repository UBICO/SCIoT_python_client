# Variance Detection - Quick Reference Guide

## What It Does

The variance detection system **automatically monitors** whether inference times for each layer are stable or changing significantly. When times change beyond a threshold, it flags the layer for investigation **and automatically flags the next layer** since the output of layer i becomes the input to layer i+1.

## Key Concepts

### Coefficient of Variation (CV)

A statistical measure of how much times vary relative to their average:

```
CV = (Standard Deviation) / (Mean)
```

**What it means:**
- **CV = 0.70%** → Extremely stable (19.03µs ± 0.13µs)
- **CV = 5%** → Very stable (normal variation due to measurement noise)
- **CV = 15%** → **THRESHOLD** - borderline unstable
- **CV = 20%** → Unstable (clear performance change)
- **CV = 50%** → Highly unstable (severe variance)

### Why Coefficient of Variation?

✅ **Scale-independent**: Works for both device (19µs) and edge (500µs)  
✅ **Normalized**: Compare across all 59 layers on same metric  
✅ **Statistically proven**: Standard QC metric in manufacturing  

### Window Size = 10

- Tracks **last 10 measurements** per layer
- Need at least 3 measurements to calculate variance
- Window fills up within ~10 inferences from each device

## How It Works

```
┌─────────────────────────────────────┐
│ Device Sends Inference Result       │
│ (Times for layers 0-N)              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ RequestHandler Updates EMA Times    │
│ (Smooth with 80% historical weight) │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ VarianceDetector Tracks Variance    │
│ (Add to 10-measurement history)     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Calculate CV for Last 10 Measurements
│ IF CV > 15% → LOG WARNING           │
│ ALSO FLAG LAYER i+1 (cascade)       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Check All Layers for Variance       │
│ IF ANY UNSTABLE → Flag for Re-test  │
│ Include cascaded layers in retest   │
└─────────────────────────────────────┘
```

**Key Addition**: Layer Cascading
- If layer i has variance → automatically flag layer i+1
- Reason: Output of layer i = Input to layer i+1
- If layer i changes, layer i+1's behavior may change too

## Interpreting Results

### Example 1: Stable Layer
```
Layer 0 (Device): mean=19.03µs, stdev=0.13µs, CV=0.70%
Status: 🟢 STABLE
Interpretation: Very consistent, no action needed
```

### Example 2: Slightly Variable Layer
```
Layer 5 (Edge): mean=520µs, stdev=30µs, CV=5.8%
Status: 🟢 STABLE
Interpretation: Normal measurement noise, still reliable
```

### 3. Unstable Layer (Variance Detected)
```
Layer 15 (Edge): mean=650µs, stdev=120µs, CV=18.5%
Status: 🔴 UNSTABLE
Interpretation: Performance changing, investigate:
  - Is system under load?
  - Are thermal conditions changing?
  - Is network congestion affecting times?
Cascading: Layer 16 edge will also be flagged for re-test
  (since layer 15's output is layer 16's input)
```

### Example 4: Highly Variable Layer (Urgent)
```
Layer 25 (Device): mean=21µs, stdev=8µs, CV=38%
Status: 🔴 HIGHLY UNSTABLE
Interpretation: Major performance changes:
  - Device may be throttling (thermal/power)
  - System resources very constrained
  - Consider immediate re-evaluation of offloading
```

## What To Do When Variance Is Detected

### 1. Check the Logs
```bash
grep "variance detected" logs/*.log
grep "re-evaluation" logs/*.log
```

### 2. Analyze the System State
```python
# See which layers are unstable
from variance_analysis import analyze_current_variance
analyze_current_variance()
```

### 3. Investigate Root Cause

**Device Times Increasing?**
- ❌ Device thermal throttling
- ❌ Device CPU under load
- ❌ Power saving mode active
- ✅ Solution: Check device resource usage

**Edge Times Increasing?**
- ❌ Server under load
- ❌ Network congestion
- ❌ System swap/memory pressure
- ✅ Solution: Check server CPU/memory

**Both Increasing?**
- ❌ Network slowdown
- ❌ System-wide performance degradation
- ✅ Solution: Check network and both systems

### 4. Consider Re-testing

Once the root cause is addressed:
```python
# Re-run the offloading algorithm
from server.offloading_algo.offloading_algo import OffloadingAlgo

# The algorithm will automatically flag when re-test is recommended
# Current implementation: logs warning
# Future: could trigger automatic re-evaluation
```

## Configuration

### Current Settings

Located in `src/server/settings.yaml`:

```yaml
# Default configuration
window_size: 10          # Track last 10 measurements
variance_threshold: 0.15  # 15% CV = unstable
```

### Adjusting Thresholds

**For stable environments (e.g., lab):**
```yaml
variance_threshold: 0.10  # 10% - more sensitive
```

**For variable environments (e.g., production with load):**
```yaml
variance_threshold: 0.20  # 20% - less sensitive
```

**For long-term monitoring (e.g., detecting degradation):**
```yaml
window_size: 20  # Track last 20 measurements
```

## Common Patterns

### Pattern 0: Layer Cascading

When variance is detected in multiple layers:

```
Layer 0: Stable
Layer 1: Stable  
Layer 2: 🔴 VARIANCE (CV > 15%)  ← Detected
  → Layer 3 automatically flagged (cascade)
Layer 4: Stable
Layer 5: 🔴 VARIANCE (CV > 15%)  ← Detected
  → Layer 6 automatically flagged (cascade)
Layer 7+: Stable

Layers needing re-test: [2, 3, 5, 6]
Reason: If layer i changes, its output (input to i+1) changes
```

### Pattern 1: Startup Variance
```
Measurements 1-3: High variance (system initializing)
Measurements 4-10: Stabilizes (system reaches equilibrium)
Status: Normal, expected behavior
```

### Pattern 2: Gradual Degradation
```
Measurements 1-5: CV = 3% (stable)
Measurements 6-10: CV = 8% (slightly increasing)
Next batch: CV = 15% (unstable)
Interpretation: Performance gradually degrading
Action: Investigate and consider re-testing
```

### Pattern 3: Sudden Change
```
Measurements 1-9: CV = 2% (stable)
Measurement 10: 2x previous value
Result: CV jumps to 22%
Interpretation: Sudden performance change
Action: Immediate investigation needed
```

### Pattern 4: Periodic Variability
```
Measurements: [500, 500, 500, 600, 600, 600, 500, 500, 500, 600]
Mean: 550µs, StDev: 48µs, CV = 8.7%
Interpretation: Periodic load pattern, but within tolerance
Action: Monitor for trends
```

## Monitoring Dashboard

To create a simple monitoring view:

```python
from variance_analysis import analyze_current_variance

# Run every 5 minutes
import schedule
schedule.every(5).minutes.do(analyze_current_variance)

# This will show:
# - Layer stability status
# - System health score
# - Unstable layers list
# - Re-test recommendations
```

## Integration with Offloading Algorithm

Current flow:
```
1. Device measurements tracked → CV calculated
2. Edge measurements tracked → CV calculated
3. If variance detected:
   - Log warning identifying layer and cascaded layer
   - Get list of layers needing re-test with get_layers_needing_retest()
4. Continue with existing offloading decision
5. (Future: Could trigger re-evaluation of affected layers only)
```

Example log output:
```
WARNING: Edge layer 15 variance detected: CV=18.5% (threshold=15.00%)
         Layer 16 should also be re-tested
         
INFO: Offloading re-test needed due to inference time variance. 
      Device layers: [2, 3], Edge: [15, 16]
```

Future enhancement:
```
1. Same as above
2. If variance detected → Flag for re-evaluation
3. Automatically run OffloadingAlgo.static_offloading()
4. Update split point if needed
5. Apply new split point to next request
```

## Troubleshooting

### Q: I see variance detected warnings. What should I do?

**A:** Follow these steps:
1. Run `python variance_analysis.py` to see which layers are unstable
2. Check if this coincides with system load changes
3. If transient (disappears), no action needed
4. If persistent, investigate the root cause (thermal, load, etc.)
5. Consider triggering offloading re-test after fixing the issue

### Q: Can I disable variance detection?

**A:** Yes, but not recommended. Currently it:
- Tracks automatically (no performance impact)
- Logs warnings (can be redirected)
- Doesn't affect current offloading decisions

To prevent logging:
```python
# In settings.yaml, set to very high threshold
variance_threshold: 1.0  # Only flag at >100% CV (essentially never)
```

### Q: How often should I review variance data?

**A:** 
- **Normal operation**: Weekly or monthly
- **Investigating issues**: Real-time
- **Performance optimization**: Before and after changes

### Q: Does this work with no offloading?

**A:** Yes! If all layers run on device (no offloading), device variance is still tracked. If all on edge, edge variance is tracked. The system works for any offloading strategy.

## Advanced Analysis

### Finding Optimal Split Point

Compare device vs edge cumulative times:

```
Layer | Device(µs) | Edge(µs) | Cumulative
      |            |          | Dev  Edge
    0 |     19.1   |  520     |  19   520
    1 |     19.0   |  530     |  38  1050
    2 |     18.9   |  510     |  57  1560
    ...
   20 |     19.2   |  540     | 384  1540  ← SPLIT POINT
   21 |     19.1   |  550     | 403  2090
```

When variance is detected, offloading should be re-evaluated to ensure split point is still optimal.

### Stability Scoring

```
Stable layers:     50/59 = 84.7%
System Health:     🟡 GOOD (>80%)
Recommendation:    Monitor, investigate if drops below 80%
```

## Next Steps

1. ✅ **Understand the system** - You're reading this!
2. ✅ **Run tests** - `python test_variance_detection.py`
3. ✅ **Check current state** - `python variance_analysis.py`
4. ⏳ **Monitor during operation** - Review logs periodically
5. ⏳ **Implement enhancement** - Trigger automatic re-testing (future)

---

**Quick Links:**
- Full documentation: [VARIANCE_DETECTION.md](VARIANCE_DETECTION.md)
- Implementation details: [VARIANCE_DETECTION_IMPLEMENTATION.md](VARIANCE_DETECTION_IMPLEMENTATION.md)
- Source code: [src/server/variance_detector.py](src/server/variance_detector.py)
- Analysis tool: [variance_analysis.py](variance_analysis.py)
- Test suite: [test_variance_detection.py](test_variance_detection.py)
