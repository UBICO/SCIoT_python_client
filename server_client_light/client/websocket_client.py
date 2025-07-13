'''
Python WebSocket Client analog to ESP32 Split-Computing
- NTP time sync
- Registration, input, inference result posting
- Uses local file 'dog.png' as image source
'''
import asyncio
import time
import uuid
import json
import struct
import ntplib
import websockets
from PIL import Image
import numpy as np

# --- Configuration ---
NTP_SERVER = "pool.ntp.org"
WS_URI = "ws://localhost:8080/ws"
DEVICE_ID = "device_01"
IMAGE_PATH = "dog.png"

# Globals
offset = 0.0
device_registered = False
best_offload_layer = None
message_uuid = ""

# 1. NTP sync
def sync_time(server: str) -> float:
    client = ntplib.NTPClient()
    while True:
        try:
            resp = client.request(server, version=3)
            print(f"[Client] NTP offset: {resp.offset:.6f} s")
            return resp.offset
        except Exception as e:
            print(f"[Client] NTP sync error: {e}, retrying...")
            time.sleep(1)

# 2. UUID generation
def generate_message_uuid() -> str:
    return str(uuid.uuid4())[:4]

# 3. Image conversion to raw RGB565 bytes
#    Simulates fb->buf content from ESP32 camera
#    Converts PNG to RGB, then to RGB565 little endian

def convert_to_rgb565_raw(path: str) -> bytes:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    rgb = np.asarray(img)
    raw = bytearray()
    for y in range(h):
        for x in range(w):
            r, g, b = rgb[y, x]
            # Pack to 5/6/5 bits
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            # little endian 16-bit
            raw.append(rgb565 & 0xFF)
            raw.append((rgb565 >> 8) & 0xFF)
    return bytes(raw)

# 4. Posting functions
async def post_registration(ws):
    global message_uuid
    message_uuid = generate_message_uuid()
    payload = {
        "device_id": DEVICE_ID,
        "message_id": message_uuid
    }
    await ws.send(json.dumps(payload))
    print(f"[Client] Registration sent: {payload}")

async def post_device_input(ws):
    raw = convert_to_rgb565_raw(IMAGE_PATH)
    print(f"[Client] Sending device input, {len(raw)} bytes")
    await ws.send(raw)

async def post_device_inference_result(ws, output_data: bytes, offlayer: int, inf_times: list):
    # Build binary message same format as ESP32
    ts = time.time() + offset
    buf = bytearray()
    buf.extend(struct.pack('<d', ts))
    buf.extend(DEVICE_ID.encode('utf-8')[:9].ljust(9, b'\x00'))
    buf.extend(message_uuid.encode('utf-8')[:4].ljust(4, b'\x00'))
    buf.extend(struct.pack('<i', offlayer))
    buf.extend(struct.pack('<I', len(output_data)))
    buf.extend(output_data)
    buf.extend(struct.pack('<i', len(inf_times)*4))  # size in bytes
    for t in inf_times:
        buf.extend(struct.pack('<f', t))
    print(f"[Client] Sending inference result, total {len(buf)} bytes")
    await ws.send(buf)

# 5. Message handler
async def handle_messages(ws):
    global device_registered, best_offload_layer
    async for message in ws:
        # Try JSON
        try:
            msg = json.loads(message)
            channel = msg.get('channel')
            if channel == 'registration':
                device_registered = True
                best_offload_layer = msg.get('offloading_layer_index')
                print(f"[Client] Registered, best layer: {best_offload_layer}")
            elif channel == 'offloading_layer':
                best_offload_layer = msg.get('offloading_layer_index')
                print(f"[Client] New offload layer: {best_offload_layer}")
        except Exception:
            # binary or non-JSON
            print(f"[Client] Received binary message of length {len(message)}")

# 6. Main
async def run_client():
    global offset
    offset = sync_time(NTP_SERVER)
    async with websockets.connect(WS_URI) as ws:
        print("[Client] WebSocket connected")
        # Send init and registration
        await post_registration(ws)
        # Launch listener
        listener = asyncio.create_task(handle_messages(ws))
        # Wait registration
        while not device_registered:
            await asyncio.sleep(0.1)
        # Send device input
        await post_device_input(ws)
        # TODO: await edge response, then post inference
        # Cleanup
        listener.cancel()

if __name__ == '__main__':
    asyncio.run(run_client())
