import tensorflow as tf
import numpy as np
from PIL import Image
import struct
import requests
import time
import random
import os

SERVER = "http://0.0.0.0:8000"
DEVICE_ID = "device_01"
TFLITE_DIR = "./tflite"

# Funzione per generare un message ID randomico
def generate_message_id():
    return ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=4))

# ---------------------
#  Registration
# ---------------------
def register_device():
    url = f"{SERVER}/api/registration"
    payload = {"device_id": DEVICE_ID}
    r = requests.post(url, json=payload)
    print("Registrazione:", r.status_code, r.text)

# ----------------------------------------------
#  Convert image in RGB565 abd send to server
# ----------------------------------------------
def send_image():
    url = f"{SERVER}/api/device_input"
    img = Image.open("img.png").resize((96, 96)).convert("RGB")
    data = np.array(img)
    rgb565 = []
    for y in range(96):
        for x in range(96):
            r, g, b = data[y, x]
            rgb = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
            rgb565.append(rgb)
    rgb565_bytes = struct.pack(f">{len(rgb565)}H", *rgb565)
    r = requests.post(url, data=rgb565_bytes, headers={"Content-Type": "application/octet-stream"})
    print("Immagine inviata:", r.status_code)

# ----------------------------
#  Request Best Offloading Layer
# ----------------------------
def get_offloading_layer():
    url = f"{SERVER}/api/offloading_layer"
    r = requests.get(url)
    if r.status_code == 200:
        best_layer = r.json().get("offloading_layer_index", 58)
        print("Best layer ricevuto:", best_layer)
        return best_layer
    else:
        print("Errore richiesta layer:", r.status_code)
        return 58

# TEST: Simulare cambio best offloading layer randomico
def get_offloading_layer2():
    url = f"{SERVER}/api/offloading_layer"
    r = requests.get(url)
    if r.status_code == 200:
        best_layer = r.json().get("offloading_layer_index", 58)
        print("Best layer ricevuto:", best_layer)
        return random.randint(0, 58)
        #return best_layer
    else:
        print("Errore richiesta layer:", r.status_code)
        return 58


# ----------------------
# Send output 
# ---------------------
def load_image_rgb(path):
    img = Image.open(path).resize((96, 96)).convert("RGB")
    img_np = np.asarray(img).astype(np.float32) / 255.0
    img_np = np.expand_dims(img_np, axis=0)  # [1,96,96,3]
    return img_np

def run_split_inference(image, tflite_dir, stop_layer):
    input_data = image
    inference_times = []
    for i in range(stop_layer + 1):
        model_path = os.path.join(tflite_dir, f"submodel_{i}.tflite")
        interpreter = tf.lite.Interpreter(model_path=model_path)
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        input_data = input_data.astype(input_details[0]['dtype'])
        interpreter.set_tensor(input_details[0]['index'], input_data)

        t0 = time.time()
        interpreter.invoke()
        t1 = time.time()
        inference_times.append(t1 - t0)
        # Aumentare inference time con tempo random -> simulare un client più lento
        #t = ((t1-t0) + random.uniform(0,0.02))
        #inference_times.append(t)
        input_data = interpreter.get_tensor(output_details[0]['index'])
        print(f"Layer {i} OK → output shape: {input_data.shape}")
    return input_data, inference_times

def send_inference_result(output_data, inference_times, layer_index, message_id):
    url = f"{SERVER}/api/device_inference_result"
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

    r = requests.post(url, data=buffer, headers={"Content-Type": "application/octet-stream"})
    print("Output inviato:", r.status_code)

# ---------------------
# MAIN
# ---------------------
def main():
    register_device()
    while True:
        send_image()
        #best_layer = get_offloading_layer() 
        best_layer = get_offloading_layer2()
        time.sleep(1)  # garantiamo che il server abbia elaborato
        message_id = generate_message_id()
        image = load_image_rgb("img.png")
        output_data, inference_times = run_split_inference(image, TFLITE_DIR, best_layer)
        send_inference_result(output_data, inference_times, best_layer, message_id)

main()

