'''WebSocket-based Split Computing Server & Client Skeleton
Preliminary operations:
1. Sync clocks via NTP
2. Server runs baseline inference on a random image to measure performance
   and initializes client timing data to zero.
'''

# server.py
import time
import ntplib
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from tensorflow.lite.python.interpreter import Interpreter
from PIL import Image
import numpy as np

NTP_SERVER = "pool.ntp.org"
WS_ENDPOINT = "/ws"
HOST = "0.0.0.0"
PORT = 8000
MODEL_PATH = "model.tflite"
BASELINE_IMAGE = "random.png"  # image for baseline test

app = FastAPI()

# 1. NTP synchronization
def sync_time(server: str = NTP_SERVER) -> float:
    client = ntplib.NTPClient()
    while True:
        try:
            resp = client.request(server, version=3)
            offset = resp.offset
            print(f"[Server] NTP offset: {offset:.6f} s")
            return offset
        except Exception as e:
            print(f"[Server] NTP sync failed: {e}, retrying...")
            time.sleep(1)

# 2. Baseline inference to measure performance

def baseline_inference(model_path: str, image_path: str, offset: float):
    # Load TFLite model
    interpreter = Interpreter(model_path)
    interpreter.allocate_tensors()
    # Preprocess image
    img = Image.open(image_path).convert('RGB')
    input_details = interpreter.get_input_details()[0]
    h, w = input_details['shape'][1:3]
    arr = np.array(img.resize((w, h)), dtype=np.float32) / 255.0
    arr = arr.reshape(input_details['shape'])

    # Run inference and measure time
    start = time.time() + offset
    interpreter.set_tensor(input_details['index'], arr)
    interpreter.invoke()
    end = time.time() + offset
    duration = end - start
    print(f"[Server] Baseline inference time: {duration:.4f} s")

    # Store baseline for clients
    return duration

# Startup tasks
offset = sync_time()
baseline_time = baseline_inference(MODEL_PATH, BASELINE_IMAGE, offset)

@app.websocket(WS_ENDPOINT)
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("[Server] WebSocket connection accepted")
    try:
        # Send baseline and timestamp init
        init_msg = {
            'type': 'init',
            'baseline_time': baseline_time,
            'offset': offset
        }
        await ws.send_json(init_msg)
        # After init, other messages will follow...
        while True:
            data = await ws.receive_text()
            # ... handle registration, input, inference
    except WebSocketDisconnect:
        print("[Server] Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
