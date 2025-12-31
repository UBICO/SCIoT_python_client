# Multi-Client Architecture

## Overview

The SCIoT server now supports multiple concurrent clients with automatic model negotiation. Each client receives a unique identifier and the server assigns an appropriate model upon connection. **The client does NOT declare its model in the config file** — instead, the model is negotiated during registration.

## Client Registration Flow

### 1. Client Initialization

When a client starts, it:

1. **Generates or Loads Client ID**
   - If `client_id` in config is `null`, a random 8-character ID is generated
   - Otherwise, the configured ID is used
   - This allows both ephemeral (random) and persistent (configured) clients

2. **Does NOT declare model upfront**
   - No `model_name` in configuration file
   - Model selection deferred to server
   - Enables server-side intelligence for model assignment

3. **Sends Registration Request**
   ```python
   POST /api/registration
   {
       "client_id": "a1b2c3d4"        # or generated UUID
   }
   ```
   (No model_name - server will assign)

### 2. Server Model Assignment

Server receives registration and:

1. **Assigns an appropriate model**
   ```python
   def _assign_model_to_client(self, client_id: str) -> str:
       # Current: assign default model
       # Future: load balancing, performance-based, etc.
       return "fomo_96x96"
   ```

2. **Stores Client Mapping**
   ```python
   self.client_models[client_id] = assigned_model
   self.devices.add(client_id)
   ```

3. **Returns Assignment to Client**
   ```python
   {
       "message": "Success",
       "client_id": "a1b2c3d4",
       "model_name": "fomo_96x96"     # Server-assigned
   }
   ```

### 3. Client Receives Assignment

Client processes response:

1. **Stores assigned model**
   ```python
   MODEL_NAME = response_data.get("model_name", "fomo_96x96")
   print(f"✓ Server assigned model: {MODEL_NAME}")
   ```

2. **Uses assigned model for inference**
   - All subsequent inference uses this model
   - Matches server's expectations

3. **Handles disconnection gracefully**
   - If server unreachable at registration, uses fallback model
   - Continues operation in local-only mode

## Configuration

### Client Configuration (`http_config.yaml`)

```yaml
client:
  # Set to null for auto-generated ID, or specify a fixed ID
  # Model will be assigned by server during registration
  client_id: null
```

That's it! No `model_name` field needed.

### Examples

**Ephemeral Client (Random ID, Server-Assigned Model)**
```yaml
client:
  client_id: null              # Auto-generates 8-char ID
                               # Model assigned by server
```

**Persistent Client (Fixed ID, Server-Assigned Model)**
```yaml
client:
  client_id: "device_01"       # Always connects as "device_01"
                               # Model assigned by server
```

**Multiple Clients (Different IDs, Same Server)**
```yaml
# Config for client A (http_config.yaml)
client:
  client_id: null              # a1b2c3d4 (random)

# Config for client B (http_config.yaml)
client:
  client_id: "device_01"       # Fixed

# Config for client C (http_config.yaml)
client:
  client_id: "mobile_02"       # Fixed

# All three connect to same server, all get models assigned
```

## Multi-Model Support

The server can intelligently assign different models based on:

1. **Current Load**
   - If model A overloaded → assign model B to new client
   - Load balancing across available models

2. **Client Capabilities**
   - Check client_id or IP → assign appropriate model
   - Device-specific models

3. **Performance Preferences**
   - Latency-optimized models for time-sensitive clients
   - Accuracy-optimized models for others

4. **Server Resources**
   - Distribute load across multiple models
   - Prevent resource exhaustion

### Example Future Implementation

```python
def _assign_model_to_client(self, client_id: str) -> str:
    """Smart model assignment based on load and capabilities"""
    
    # Check current model loads
    model_counts = {}
    for model in self.client_models.values():
        model_counts[model] = model_counts.get(model, 0) + 1
    
    # Assign to least-loaded model
    if model_counts.get("fomo_96x96", 0) < model_counts.get("mobilenet_lite", 0):
        return "fomo_96x96"
    else:
        return "mobilenet_lite"
```

## Request Flow

All subsequent requests from a client include its `client_id`:

### Device Input Endpoint
```python
POST /api/device_input?client_id=a1b2c3d4
[binary image data]
```
Server knows: client a1b2c3d4 uses model "fomo_96x96"

### Offloading Decision Request
```python
GET /api/offloading_layer?client_id=a1b2c3d4
```
Returns decision for model "fomo_96x96"

### Inference Result Submission
```python
POST /api/device_inference_result?client_id=a1b2c3d4
[binary inference times and output data]
```

## Server-Side Tracking

### HTTP Server State
```python
class HttpServer:
    # Map: client_id -> model_name (assigned by server)
    self.client_models = {
        "a1b2c3d4": "fomo_96x96",
        "device_01": "fomo_96x96",
        "mobile_02": "fomo_96x96"
    }
    
    # Registered devices
    self.devices = {"a1b2c3d4", "device_01", "mobile_02"}
```

### Per-Client Request Handler
Each request includes `client_id`, enabling:

1. **Logging and Monitoring**
   ```
   [INFO] Client a1b2c3d4 (fomo_96x96): Processing inference result
   [INFO] Client device_01 (fomo_96x96): Offloading decision = layer 30
   ```

2. **Model-Specific Processing** (Future Enhancement)
   - Load model-specific statistics
   - Apply model-specific offloading algorithms
   - Track model-specific variance

3. **Debugging**
   - Identify which client caused errors
   - Monitor per-client resource usage
   - Detect client-specific issues

## Benefits

1. **Simplified Client Configuration**
   - Clients only specify ID (or none for auto-generated)
   - No need to know available models upfront
   - No model configuration needed in client

2. **Server-Side Intelligence**
   - Server decides model allocation
   - Can load balance dynamically
   - Can assign models based on client capabilities

3. **Flexibility**
   - Server can reassign models without client changes
   - Support for multiple models transparently
   - Future: dynamic model switching

4. **Scalability**
   - Server handles multiple concurrent clients
   - Each client gets personalized offloading decisions
   - Models assigned dynamically

5. **Robustness**
   - If server unavailable, client has fallback model
   - Graceful degradation with sensible defaults
   - Continues operation independently

## Implementation Details

### Client ID Generation
```python
import uuid

client_id_config = config["client"].get("client_id")
if client_id_config:
    CLIENT_ID = str(client_id_config)
else:
    CLIENT_ID = str(uuid.uuid4())[:8]  # Random 8-char ID
```

### Model Initialization (Before Connection)
```python
# Model will be assigned by server during registration
MODEL_NAME = None  # Will be set after successful registration
```

### Registration with Model Negotiation
```python
def register_device():
    global MODEL_NAME  # Will be set by server response
    url = f"{SERVER}{ENDPOINTS['registration']}"
    payload = {"client_id": CLIENT_ID}  # Just send ID
    try:
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code == 200:
            response_data = r.json()
            # Server assigns the model
            MODEL_NAME = response_data.get("model_name", "fomo_96x96")
            print(f"✓ Server assigned model: {MODEL_NAME}")
            return True
        return False
    except requests.exceptions.RequestException as e:
        print(f"⚠ Registration failed: {e}")
        return False
```

### Server Registration Endpoint
```python
@self.app.post(self.endpoints['registration'])
async def registration(data: dict):
    client_id = data.get("client_id", "unknown")
    
    # Server assigns a model to this client
    assigned_model = self._assign_model_to_client(client_id)
    
    # Register client and store model mapping
    self.client_models[client_id] = assigned_model
    self.devices.add(client_id)
    
    return {
        'message': 'Success',
        'client_id': client_id,
        'model_name': assigned_model  # Send assignment to client
    }
```

### Server Model Assignment Method
```python
def _assign_model_to_client(self, client_id: str) -> str:
    """
    Assign a model to the connecting client.
    
    Current implementation: Assign default model
    Future enhancements: 
    - Load balancing across models
    - Client-specific model selection
    - Performance-based model assignment
    """
    # For now, assign the default model (can be made configurable)
    return "fomo_96x96"
```

## Testing Multi-Client Scenarios

Run multiple client instances to test:

```bash
# Terminal 1: Client A (auto-generated ID)
python server_client_light/client/http_client.py  # Server assigns model

# Terminal 2: Client B (fixed ID)
# Edit http_config.yaml: client_id: "device_01"
python server_client_light/client/http_client.py  # Server assigns model

# Terminal 3: Client C (another fixed ID)
# Edit http_config.yaml: client_id: "device_02"
python server_client_light/client/http_client.py  # Server assigns model

# Observe server logs:
# Client a1b2c3d4 registered, assigned model: fomo_96x96
# Client device_01 registered, assigned model: fomo_96x96
# Client device_02 registered, assigned model: fomo_96x96
```

## Client Behavior with Server Unavailability

If server is unavailable during registration:

```python
# Client couldn't reach server
server_available = register_device()
if server_available:
    print(f"✓ Connected to server (model: {MODEL_NAME})")
else:
    # Fallback to default model
    if MODEL_NAME is None:
        MODEL_NAME = "fomo_96x96"
    print(f"⚠ Server unavailable - Using fallback model: {MODEL_NAME}")
    print("  Client will continue in LOCAL-ONLY mode\n")
```

## Future Enhancements

1. **Dynamic Model Rebalancing**
   - Monitor per-model load
   - Suggest model changes to existing clients
   - Automatic migration on server restart

2. **Client Capability Detection**
   - Query client specs on registration
   - Assign models based on hardware capabilities
   - Memory/CPU-optimized models

3. **Performance-Based Assignment**
   - Track per-model latency
   - Assign faster models to latency-sensitive clients
   - Assign accurate models to others

4. **Model Marketplace**
   - Client reports available models
   - Server selects from client's offerings
   - Mutual capability negotiation

5. **Persistent Model Selection**
   - Remember previous model assignment
   - Reassign same model on reconnection
   - Maintain consistency

---

**Version**: 2.0 (Negotiated Model Assignment)  
**Last Updated**: December 31, 2025  
**Status**: Implemented and tested
