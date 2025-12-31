import tensorflow as tf
import numpy as np
from PIL import Image
import struct
import requests
import time
import random
import os
import yaml
from pathlib import Path
from delay_simulator import DelaySimulator

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
CONFIG_PATH = SCRIPT_DIR / "http_config.yaml"

# Load configuration from YAML file
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

DEVICE_ID = config["client"]["device_id"]
SERVER_HOST = config["http"]["server_host"]
SERVER_PORT = config["http"]["server_port"]
SERVER = f"http://{SERVER_HOST}:{SERVER_PORT}"

MODEL_CONFIG = config["model"]
INPUT_HEIGHT = MODEL_CONFIG["input_height"]
INPUT_WIDTH = MODEL_CONFIG["input_width"]
LAST_OFFLOADING_LAYER = MODEL_CONFIG["last_offloading_layer"]

IMAGE_PATH = SCRIPT_DIR / MODEL_CONFIG["image_name"]
TFLITE_DIR = SCRIPT_DIR / MODEL_CONFIG["tflite_subdir"]
SUBMODEL_PREFIX = MODEL_CONFIG["submodel_prefix"]

ENDPOINTS = config["http"]["endpoints"]

# Initialize delay simulators
DELAY_CONFIG = config.get("delay_simulation", {})
computation_delay = DelaySimulator(DELAY_CONFIG.get("computation"))
network_delay = DelaySimulator(DELAY_CONFIG.get("network"))

if computation_delay.enabled:
    print(f"Computation delay enabled: {computation_delay.get_delay_info()}")
if network_delay.enabled:
    print(f"Network delay enabled: {network_delay.get_delay_info()}")

# Function to generate a random message ID
def generate_message_id():
    return ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=4))

# ---------------------
#  Registration
# ---------------------
def register_device():
    url = f"{SERVER}{ENDPOINTS['registration']}"
    payload = {"device_id": DEVICE_ID}
    try:
        r = requests.post(url, json=payload, timeout=5)
        print("Registration:", r.status_code, r.text)
        return True
    except requests.exceptions.RequestException as e:
        print(f"⚠ Registration failed (server unreachable): {e}")
        print("  → Continuing with local-only inference")
        return False

# ------------------------------------------------
#  Convert image to RGB565 and send to server
# ------------------------------------------------
def send_image():
    url = f"{SERVER}{ENDPOINTS['device_input']}"
    img = Image.open(str(IMAGE_PATH)).resize((INPUT_HEIGHT, INPUT_WIDTH)).convert("RGB")
    data = np.array(img)
    rgb565 = []
    for y in range(96):
        for x in range(96):
            r, g, b = data[y, x]
            rgb = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
            rgb565.append(rgb)
    rgb565_bytes = struct.pack(f">{len(rgb565)}H", *rgb565)
    try:
        r = requests.post(url, data=rgb565_bytes, headers={"Content-Type": "application/octet-stream"}, timeout=5)
        print("Image sent:", r.status_code)
        return True
    except requests.exceptions.RequestException as e:
        print(f"⚠ Image send failed (server unreachable): {e}")
        return False

# ----------------------------
#  Request Best Offloading Layer
# ----------------------------
def get_offloading_layer():
    url = f"{SERVER}{ENDPOINTS['offloading_layer']}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            best_layer = r.json().get("offloading_layer_index", LAST_OFFLOADING_LAYER)
            print("Best layer received:", best_layer)
            return best_layer
        else:
            print("Error requesting layer:", r.status_code)
            return LAST_OFFLOADING_LAYER
    except requests.exceptions.RequestException as e:
        print(f"⚠ Cannot reach server: {e}")
        print("  → Running all layers locally")
        return LAST_OFFLOADING_LAYER

# TEST: Simulate random best offloading layer change
def get_offloading_layer_random():
    url = f"{SERVER}{ENDPOINTS['offloading_layer']}"
    r = requests.get(url)
    if r.status_code == 200:
        best_layer = r.json().get("offloading_layer_index", LAST_OFFLOADING_LAYER)
        print("Best layer received:", best_layer)
        return random.randint(0, LAST_OFFLOADING_LAYER)
        #return best_layer
    else:
        print("Error requesting layer:", r.status_code)
        return LAST_OFFLOADING_LAYER


# ----------------------
# Send output 
# ---------------------
def load_image_rgb(path):
    img = Image.open(str(path)).resize((INPUT_HEIGHT, INPUT_WIDTH)).convert("RGB")
    img_np = np.asarray(img).astype(np.float32) / 255.0
    img_np = np.expand_dims(img_np, axis=0)  # [1,96,96,3]
    return img_np

def run_split_inference(image, tflite_dir, stop_layer):
    input_data = image
    inference_times = []
    
    # Handle -1 as "run all layers until the end"
    if stop_layer == -1:
        stop_layer = LAST_OFFLOADING_LAYER
        print(f"Offloading layer -1: Running all {stop_layer + 1} layers locally")
    
    for i in range(stop_layer + 1):
        model_path = str(tflite_dir / f"{SUBMODEL_PREFIX}_{i}.tflite")
        interpreter = tf.lite.Interpreter(model_path=model_path)
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        input_data = input_data.astype(input_details[0]['dtype'])
        interpreter.set_tensor(input_details[0]['index'], input_data)

        t0 = time.time()
        
        # Apply artificial computation delay
        if computation_delay.enabled:
            delay = computation_delay.apply_delay()
            print(f"  Layer {i} computation delay: {delay*1000:.2f}ms")
        
        interpreter.invoke()
        t1 = time.time()
        inference_times.append(t1 - t0)
        # Increase inference time with random time -> simulate a slower client
        #t = ((t1-t0) + random.uniform(0,0.02))
        #inference_times.append(t)
        input_data = interpreter.get_tensor(output_details[0]['index'])
        print(f"Layer {i} OK → output shape: {input_data.shape}")
    return input_data, inference_times

def send_inference_result(output_data, inference_times, layer_index, message_id):
    # Apply network delay before sending
    if network_delay.enabled:
        delay = network_delay.apply_delay()
        print(f"  Applied network delay: {delay*1000:.2f}ms")
    
    url = f"{SERVER}{ENDPOINTS['device_inference_result']}"
    timestamp = time.time()

    buffer = bytearray()
    buffer += struct.pack("d", timestamp)
    buffer += DEVICE_ID.encode("ascii").ljust(9, b'\x00')
    buffer += message_id.encode("ascii").ljust(4, b'\x00')
    buffer += struct.pack("i", layer_index)
    buffer += struct.pack("I", output_data.nbytes)
    buffer += output_data.tobytes()
    buffer += struct.pack("i", len(inference_times) * 4)
    buffer += np.array(inference_times, dtype=np.float32).tobytes()

    try:
        r = requests.post(url, data=buffer, headers={"Content-Type": "application/octet-stream"}, timeout=5)
        print("Output sent:", r.status_code)
        return True
    except requests.exceptions.RequestException as e:
        print(f"⚠ Cannot send result to server: {e}")
        print("  → Local inference completed, result not synchronized")
        return False

# -----
# MAIN
# -----
def main():
    print("="*60)
    print("SCIoT Client Starting")
    print(f"Server: {SERVER}")
    print(f"Device ID: {DEVICE_ID}")
    print("="*60)
    
    # Try to register, but continue even if it fails
    server_available = register_device()
    if not server_available:
        print("\n⚠ Server not available - Running in LOCAL-ONLY mode")
        print("  Client will continue and retry server connection on each request\n")
    
    while True:
        # Try to send image (optional, just for server tracking)
        send_image()
        
        # Get offloading decision (fallback to local if server unreachable)
        best_layer = get_offloading_layer()
        
        time.sleep(1)  # Ensure server has processed the request
        message_id = generate_message_id()
        image = load_image_rgb(IMAGE_PATH)
        
        # Always run inference (local or split based on best_layer)
        output_data, inference_times = run_split_inference(image, TFLITE_DIR, best_layer)
        
        # Try to send results (for variance tracking and algorithm updates)
        send_inference_result(output_data, inference_times, best_layer, message_id)
        
        print(f"✓ Inference complete (layers 0-{best_layer})\n")

main()

