# SCIoT Python Client
*Split Computing on IoT with Python Clients*

Advanced split computing implementation for TinyML on IoT devices with intelligent offloading, variance detection, and resilient client-server communication.

![Unit Tests](https://github.com/UBICO/SCIoT/actions/workflows/codecov.yml/badge.svg) [![Powered by UBICO](https://img.shields.io/badge/powered%20by-UBICO-orange.svg?style=flat&colorA=E1523D&colorB=007D8A)]()  

## Overview

The SCIoT project provides tools to use Edge Impulse models in ESP32 devices and Python clients, using split computing techniques. This repository includes advanced features for adaptive offloading and system resilience.

### Key Features

#### 🎯 Intelligent Offloading
- Dynamic layer-by-layer offloading decisions
- Exponential Moving Average (EMA) time smoothing (α=0.2)
- Network-aware split point selection
- Support for 59-layer TFLite models (FOMO 96x96)

#### 📊 Variance Detection System
- Real-time inference time monitoring
- Coefficient of Variation (CV) analysis with 15% threshold
- Sliding window history (10 measurements per layer)
- Automatic cascade propagation (layer i → layer i+1)
- Triggers re-evaluation when performance changes

#### 🔄 Local Inference Mode
- Probabilistic forcing of device-local inference
- Refreshes device measurements periodically
- Configurable probability (0.0-1.0)
- Returns special value `-1` for all-device execution
- Seamless client-server coordination

#### 🛡️ Client Resilience
- Graceful degradation to local-only mode
- Connection error handling with 5-second timeouts
- Automatic reconnection attempts
- Continues operation when server unavailable
- No crashes on network failures

#### 🔗 Multi-Client Support
- Multiple concurrent clients with unique IDs (auto-generated or configured)
- Server negotiates and assigns models upon connection
- Client doesn't need to declare model upfront
- Per-client offloading decisions
- Support for heterogeneous deployments

#### 🧪 Comprehensive Testing
- 44 automated tests (39 core + 5 MQTT)
- Interactive demonstration scripts
- Unit, integration, and system tests
- Connection resilience tests
- 100% test pass rate

## Publications

If you use this work, please consider citing:
- F. Bove, S. Colli and L. Bedogni, "Performance Evaluation of Split Computing with TinyML on IoT Devices," 2024 IEEE 21st Consumer Communications & Networking Conference (CCNC), Las Vegas, NV, USA, 2024, pp. 1-6, [DOI Link](http://dx.doi.org/10.1109/CCNC51664.2024.10454775).
- F. Bove and L. Bedogni, "Smart Split: Leveraging TinyML and Split Computing for Efficient Edge AI," 2024 IEEE/ACM Symposium on Edge Computing (SEC), Rome, Italy, 2024, pp. 456-460, [DOI Link](http://dx.doi.org/10.1109/SEC62691.2024.00052).

## Project Structure

```
SCIoT_python_client/
├── src/
│   └── server/
│       ├── edge/                    # Edge server initialization
│       ├── communication/           # HTTP, WebSocket, MQTT servers
│       │   ├── http_server.py      # FastAPI HTTP server
│       │   ├── request_handler.py  # Request processing + variance + local inference
│       │   └── websocket_server.py # WebSocket server
│       ├── models/                  # Model management and inference
│       │   └── model_manager.py    # Edge inference with variance tracking
│       ├── offloading_algo/         # Offloading decision algorithms
│       ├── device/                  # Device simulation
│       ├── statistics/              # Performance statistics
│       ├── variance_detector.py     # Variance detection system
│       ├── delay_simulator.py       # Network/computation delay simulation
│       └── settings.yaml            # Server configuration
│
├── server_client_light/
│   └── client/
│       ├── http_client.py           # Python HTTP client (main)
│       ├── websocket_client.py      # Python WebSocket client
│       ├── http_config.yaml         # HTTP client configuration
│       ├── websocket_config.yaml    # WebSocket client configuration
│       └── delay_simulator.py       # Client-side delay simulation
│
├── tests/
│   ├── test_variance_and_local_inference.py  # Core feature tests (27)
│   ├── test_client_resilience.py             # Connection handling (12)
│   ├── test_mqtt_client/                     # MQTT tests (5)
│   └── test_offloading_algo/                 # Offloading algorithm tests
│
├── test_variance_detection.py      # Interactive demo: variance detection
├── test_variance_cascading.py      # Interactive demo: cascading
│
└── Documentation/
    ├── VARIANCE_DETECTION.md
    ├── VARIANCE_DETECTION_IMPLEMENTATION.md
    ├── LOCAL_INFERENCE_MODE.md
    ├── LOCAL_INFERENCE_IMPLEMENTATION.md
    ├── CLIENT_SERVER_-1_SEMANTICS.md
    ├── DELAY_SIMULATION.md
    └── TEST_SUITE_SUMMARY.md
```

## Installation

### Prerequisites
- Python 3.11+
- TensorFlow 2.15.0
- Docker (for MQTT broker)

### Setup

Clone the repository:
```sh
git clone https://github.com/UBICO/SCIoT.git
cd SCIoT_python_client
```

Create virtual environment and install dependencies:
```sh
uv sync
```

Activate the virtual environment:
```sh
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows
```

### Model Setup
- Save your Keras model as `test_model.h5` in `src/server/models/test/test_model/`
- Save your test image as `test_image.png` in `src/server/models/test/test_model/pred_data/`
- Split the model: `python3 src/server/models/model_split.py`
- Configure paths in `src/server/commons.py`

### Configuration

#### Server Configuration (`src/server/settings.yaml`)

```yaml
communication:
  http:
    host: 0.0.0.0
    port: 8000
    endpoints:
      registration: /api/registration
      device_input: /api/device_input
      offloading_layer: /api/offloading_layer
      device_inference_result: /api/device_inference_result

delay_simulation:
  computation:
    enabled: false
    type: gaussian
    mean: 0.001
    std_dev: 0.0002
  network:
    enabled: false
    type: gaussian
    mean: 0.020
    std_dev: 0.005

local_inference_mode:
  enabled: true
  probability: 0.1  # 10% of requests force local inference
```

#### Client Configuration (`server_client_light/client/http_config.yaml`)

```yaml
client:
  device_id: "device_01"

http:
  server_host: "0.0.0.0"
  server_port: 8000

model:
  last_offloading_layer: 58
  
local_inference_mode:
  enabled: true
  probability: 0.1
```

## Usage

### Starting the Server

Activate the virtual environment:
```sh
source .venv/bin/activate
```

Start the MQTT broker (optional):
```sh
docker compose up
```

Run the edge server:
```sh
python src/server/edge/run_edge.py
```

### Running the Client

In a separate terminal:
```sh
source .venv/bin/activate
python server_client_light/client/http_client.py
```

**Client Behavior:**
- Connects to server and registers device
- Sends image data
- Receives offloading decision (or `-1` for local-only)
- Runs inference (split or local)
- Sends results back to server
- **Continues operating if server becomes unavailable** (graceful degradation to local-only mode)

### Analytics Dashboard

View real-time statistics:
```sh
streamlit run src/server/web/webpage.py
```

## Testing

### Run All Tests
```sh
pytest tests/test_variance_and_local_inference.py tests/test_client_resilience.py tests/test_mqtt_client/ tests/test_multi_client.py -v
```

**Test Coverage**: 67 tests passing
- Variance & local inference: 27 tests
- Client resilience: 12 tests  
- MQTT client: 5 tests
- Multi-client model negotiation: 23 tests

### Run Specific Test Suites
```sh
# Core features (variance, local inference, -1 handling)
pytest tests/test_variance_and_local_inference.py -v

# Connection resilience
pytest tests/test_client_resilience.py -v

# Multi-client model negotiation
pytest tests/test_multi_client.py -v

# MQTT client
pytest tests/test_mqtt_client/ -v
```

### Interactive Demos
```sh
# Variance detection demonstration
python test_variance_detection.py

# Cascade propagation demonstration
python test_variance_cascading.py
```

## Advanced Features

### Variance Detection

The system monitors inference time stability using Coefficient of Variation (CV):

```
CV = StdDev / Mean

If CV > 15% → Unstable → Trigger re-test
```

**Cascading:** When layer i shows variance, layer i+1 is automatically flagged for re-testing (since layer i's output is layer i+1's input).

See [VARIANCE_DETECTION.md](VARIANCE_DETECTION.md) for details.

### Local Inference Mode

Probabilistically forces device to run all layers locally:

- **Purpose:** Refresh device inference times periodically
- **Configuration:** `enabled` (true/false) + `probability` (0.0-1.0)
- **Mechanism:** Server returns `-1` instead of calculated offloading layer
- **Client Handling:** `-1` → converts to layer 58 (run all 59 layers locally)

See [LOCAL_INFERENCE_MODE.md](LOCAL_INFERENCE_MODE.md) for details.

### Delay Simulation

Simulate network and computation delays for testing:

```yaml
delay_simulation:
  computation:
    enabled: true
    type: gaussian  # Options: static, gaussian, uniform, exponential
    mean: 0.001     # 1ms average
    std_dev: 0.0002 # 0.2ms variation
  network:
    enabled: true
    type: gaussian
    mean: 0.020     # 20ms average
    std_dev: 0.005  # 5ms variation
```

See [DELAY_SIMULATION.md](DELAY_SIMULATION.md) for details.

### Multi-Client Support

Run multiple concurrent clients with automatic model negotiation:

1. **Client Configuration**
   - Only specify client ID (auto-generated or fixed)
   - No model declaration needed in config

2. **Server Assignment**
   - Server decides which model to assign
   - Can load balance or assign based on capabilities

3. **Example**: Run 3 clients simultaneously:
   ```bash
   # Terminal 1: Client A (auto-generated ID)
   python server_client_light/client/http_client.py
   # Server assigns: "fomo_96x96"
   
   # Terminal 2: Client B (fixed ID: device_01)
   # Edit http_config.yaml: client_id: "device_01"
   python server_client_light/client/http_client.py
   # Server assigns: "fomo_96x96"
   
   # Terminal 3: Client C (fixed ID: mobile_02)
   # Edit http_config.yaml: client_id: "mobile_02"
   python server_client_light/client/http_client.py
   # Server assigns: "fomo_96x96"
   ```

See [MULTI_CLIENT_ARCHITECTURE.md](MULTI_CLIENT_ARCHITECTURE.md) for detailed model negotiation and configuration.

## Documentation

Comprehensive documentation available:

- **[VARIANCE_DETECTION.md](VARIANCE_DETECTION.md)** - Technical documentation of variance detection
- **[VARIANCE_DETECTION_IMPLEMENTATION.md](VARIANCE_DETECTION_IMPLEMENTATION.md)** - Implementation overview
- **[LOCAL_INFERENCE_MODE.md](LOCAL_INFERENCE_MODE.md)** - Local inference mode reference
- **[LOCAL_INFERENCE_IMPLEMENTATION.md](LOCAL_INFERENCE_IMPLEMENTATION.md)** - Implementation details
- **[CLIENT_SERVER_-1_SEMANTICS.md](CLIENT_SERVER_-1_SEMANTICS.md)** - How -1 works end-to-end
- **[DELAY_SIMULATION.md](DELAY_SIMULATION.md)** - Delay simulation guide
- **[MULTI_CLIENT_ARCHITECTURE.md](MULTI_CLIENT_ARCHITECTURE.md)** - Multi-client support and configuration
- **[TEST_SUITE_SUMMARY.md](TEST_SUITE_SUMMARY.md)** - Complete test documentation

## System Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Device    │ ◄─────► │ Edge Server  │ ◄─────► │  Analytics  │
│   Client    │   HTTP  │  (FastAPI)   │         │  Dashboard  │
└─────────────┘         └──────────────┘         └─────────────┘
      │                        │
      │                        │
   Inference              Offloading
   (0 to N)              Algorithm +
                         Variance +
                         Local Mode
      │                        │
      ▼                        ▼
  Device                   Edge
  Results                Results
  (times)               (prediction)
```

**Request Flow:**

1. Client sends image → Server
2. Server returns offloading layer (or `-1`)
3. Client runs inference up to layer
4. Client sends results + times → Server
5. Server tracks variance + updates times
6. Server runs remaining layers (if needed)
7. Server returns final prediction

## Performance

- **Inference:** 59 layers (FOMO 96x96)
- **Device time:** ~19µs per layer average
- **Edge time:** ~450-540µs per layer average
- **Network:** Configurable latency simulation
- **Variance threshold:** 15% CV
- **Refresh rate:** Configurable (default 10% via local inference mode)

## Troubleshooting

### Server won't start
- Check port 8000 is not in use
- Verify TensorFlow is installed correctly
- Check model files exist in correct paths

### Client can't connect
- Verify server is running
- Check `server_host` and `server_port` in config
- **Note:** Client will continue in local-only mode if server unavailable

### Tests failing
- Ensure virtual environment is activated
- Run `uv sync` to update dependencies
- Check Python version is 3.11+

### Inference errors
- Verify model is split correctly
- Check layer dimensions match
- Review logs in `logs/` directory

## Contributing

This is a research project. For questions or collaboration:
- Open an issue on GitHub
- Contact the UBICO research group
- See publications for research context

## License

See [LICENSE](LICENSE) file for details.

---

**Last Updated:** December 31, 2025  
**Status:** ✅ All systems operational (67/67 tests passing)  
**Version:** Python 3.11.11, TensorFlow 2.15.0
