import time
import uuid
import requests
import json
import numpy as np
import tensorflow as tf
from datetime import datetime

# Config
NUM_LAYERS = 58
DEVICE_ID = "device_01"
SERVER = "http://<ip>:<port>"
MODEL_PATHS = [f"layers/layer_{i}.tflite" for i in range(NUM_LAYERS)]
INPUT_SHAPE = (1, 96, 96, 3)  # esempio

# State
device_registered = False
input_buffer = None
output_message = None
best_offloading_layer_index = NUM_LAYERS - 1
last_multi_output_layer_data = None  # solo per FOMO

def get_current_timestamp():
    return time.time()

def get_uuid():
    return str(uuid.uuid4())[:4]

def register_device():
    global device_registered
    url = f"{SERVER}/api/registration"
    payload = {"device_id": DEVICE_ID}
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            device_registered = True
            print("Device registered")
        else:
            print(f"Registration failed: {r.text}")
    except Exception as e:
        print(f"Registration error: {e}")

def get_offloading_layer():
    global best_offloading_layer_index
    try:
        r = requests.get(f"{SERVER}/api/offloading_layer")
        if r.status_code == 200:
            data = r.json()
            best_offloading_layer_index = data["offloading_layer_index"]
            print(f"Best offloading layer: {best_offloading_layer_index}")
    except Exception as e:
        print(f"Error fetching offloading layer: {e}")

def load_model(layer_index):
    model_path = MODEL_PATHS[layer_index]
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    return interpreter

def run_layers(input_data, max_layer):
    inference_times = []
    for i in range(max_layer + 1):
        start = time.time()
        interpreter = load_model(i)
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        interpreter.set_tensor(input_details[0]['index'], input_data.astype(np.float32))
        interpreter.invoke()
        output_data = interpreter.get_tensor(output_details[0]['index'])

        inference_time = time.time() - start
        inference_times.append(inference_time)
        input_data = output_data  # per il layer successivo
    return output_data, inference_times

def post_inference_result(output_data, inference_times):
    timestamp = get_current_timestamp()
    msg_uuid = get_uuid()
    
    # Invia come JSON o binario
    payload = {
        "timestamp": timestamp,
        "device_id": DEVICE_ID,
        "message_id": msg_uuid,
        "offloading_layer_index": best_offloading_layer_index,
        "output": output_data.tolist(),
        "inference_times": inference_times
    }

    try:
        url = f"{SERVER}/api/device_inference_result"
        r = requests.post(url, json=payload)
        print("Inference result sent")
    except Exception as e:
        print(f"Failed to send inference result: {e}")
