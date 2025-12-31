# Configuration Files

This directory contains configuration files for the SCIoT clients.

## Files

### `http_config.yaml`
Configuration for the HTTP client:
- **client.device_id**: Device identifier
- **http.server_host**: Server hostname/IP
- **http.server_port**: Server port
- **http.endpoints**: API endpoints
- **model**: Model configuration (dimensions, image names, TFLite directory)

### `websocket_config.yaml`
Configuration for the WebSocket client:
- **client.device_id**: Device identifier  
- **websocket.server_host**: WebSocket server hostname
- **websocket.server_port**: WebSocket server port
- **websocket.endpoint**: WebSocket endpoint path
- **ntp.server**: NTP server for time synchronization
- **model**: Model configuration (image name, dimensions)

## Usage

Both clients automatically load their respective configuration files from the same directory as the script. To change settings, simply edit the YAML files.

### Running HTTP Client
```bash
cd server_client_light/client
python http_client.py
```

### Running WebSocket Client
```bash
cd server_client_light/client
python websocket_client.py
```

Or from the root directory:
```bash
python server_client_light/client/http_client.py
python server_client_light/client/websocket_client.py
```
