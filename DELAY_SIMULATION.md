# Artificial Delay Simulation

The SCIoT system includes artificial delay simulation capabilities to test and evaluate system behavior under different network and computation conditions.

## Overview

Both the **client** (device) and **server** (edge) support two types of artificial delays:

1. **Computation Delay**: Simulates slower computation (device CPU or edge server processing)
2. **Network Delay**: Simulates network latency

## Delay Distribution Types

Each delay can be configured with different statistical distributions:

### 1. Static Delay
Fixed delay value for every operation.

```yaml
type: "static"
value: 0.002  # 2ms constant delay
```

### 2. Gaussian (Normal) Distribution
Delay follows a normal distribution with specified mean and standard deviation.

```yaml
type: "gaussian"
mean: 0.002      # 2ms average
std_dev: 0.0005  # 0.5ms standard deviation
```

### 3. Uniform Distribution
Delay is uniformly distributed between min and max values.

```yaml
type: "uniform"
min: 0.001  # 1ms minimum
max: 0.003  # 3ms maximum
```

### 4. Exponential Distribution
Delay follows an exponential distribution (models random arrival times).

```yaml
type: "exponential"
mean: 0.002  # 2ms average (1/λ)
```

## Configuration

### Client Configuration

Edit `server_client_light/client/http_config.yaml` or `websocket_config.yaml`:

```yaml
delay_simulation:
  # Computation delay (simulates slower device)
  computation:
    enabled: true      # Set to true to enable
    type: "gaussian"   # Choose: none, static, gaussian, uniform, exponential
    mean: 0.002        # 2ms
    std_dev: 0.0005    # 0.5ms
  
  # Network delay (simulates slower network on client side)
  network:
    enabled: true
    type: "static"
    value: 0.020       # 20ms fixed delay
```

### Server Configuration

Edit `src/server/settings.yaml`:

```yaml
delay_simulation:
  # Computation delay (simulates slower edge server)
  computation:
    enabled: true
    type: "gaussian"
    mean: 0.001        # 1ms average
    std_dev: 0.0002    # 0.2ms standard deviation
  
  # Network delay (simulates slower network on server side)
  network:
    enabled: true
    type: "uniform"
    min: 0.005         # 5ms minimum
    max: 0.015         # 15ms maximum
```

## Usage Examples

### Example 1: Simulate High Latency Network

Client: 50ms ± 10ms network delay
Server: 40ms ± 8ms network delay
Total round-trip: ~180ms

```yaml
# Client config
delay_simulation:
  network:
    enabled: true
    type: "gaussian"
    mean: 0.050
    std_dev: 0.010

# Server config
delay_simulation:
  network:
    enabled: true
    type: "gaussian"
    mean: 0.040
    std_dev: 0.008
```

### Example 2: Simulate Slower Device

Device is 5-10x slower than normal:

```yaml
# Client config
delay_simulation:
  computation:
    enabled: true
    type: "uniform"
    min: 0.010   # 10ms minimum per layer
    max: 0.020   # 20ms maximum per layer
```

### Example 3: Realistic 4G Network

Exponential delay with 30ms mean (typical 4G latency):

```yaml
# Client and Server config
delay_simulation:
  network:
    enabled: true
    type: "exponential"
    mean: 0.030  # 30ms average
```

## Implementation Details

### Where Delays Are Applied

**Client Side:**
- **Computation delay**: Applied after each layer inference, before timing measurement
- **Network delay**: Applied before HTTP/WebSocket requests to server

**Server Side:**
- **Computation delay**: Applied in `ModelManager.predict_single_layer()` before inference
- **Network delay**: Applied before sending responses to client

### Impact on Measurements

Artificial delays **are included** in the measured inference times, so:
- Statistics reflect the delayed performance
- Offloading algorithm adapts to simulated conditions
- Real-time EMA updates account for delays

### Logging

When delays are enabled, you'll see log messages:

```
Computation delay enabled: Gaussian delay: μ=2.00ms, σ=0.50ms
Applied computation delay: 2.34ms
Applied network delay: 18.76ms
```

## Testing Strategy

1. **Baseline**: Run without delays to establish baseline performance
2. **Network Only**: Enable network delays to test communication impact
3. **Computation Only**: Enable computation delays to test offloading decisions
4. **Combined**: Enable both to test realistic scenarios
5. **Extreme**: Use high delays to test system robustness

## Disabling Delays

To disable delays, set `enabled: false` or `type: "none"`:

```yaml
delay_simulation:
  computation:
    enabled: false  # Disabled
  network:
    enabled: false  # Disabled
```

## Notes

- All delay values are in **seconds** (e.g., 0.001 = 1ms)
- Gaussian delays are clipped to non-negative values
- Delays are applied per-layer for computation, per-request for network
- Statistics files reflect performance including artificial delays
