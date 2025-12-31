import numpy as np
import struct
import requests
import time
import random
import os
import csv


def offloading_algo(edge_times, device_times, network_times):
    edge = np.asarray(edge_times, dtype=float)
    dev  = np.asarray(device_times, dtype=float)
    net  = np.asarray(network_times, dtype=float)

    N = len(dev)
    if len(edge) != N:
        raise ValueError(f"edge_times e device_times devono avere la stessa lunghezza. "
                         f"Got {len(edge)} e {N}.")

    # Normalizza network_times a lunghezza N+1 (k = 0..N)
    if net.ndim == 0:  # scalare
        net = np.full(N + 1, float(net))
    elif len(net) == N + 1:
        pass  # già perfetto
    elif len(net) == N:
        # Riutilizza l'ultimo valore per k = N (invio del risultato)
        net = np.append(net, net[-1])
    elif len(net) == 1:
        net = np.full(N + 1, float(net[0]))
    else:
        raise ValueError(f"network_times deve avere lunghezza 1, N o N+1 (N={N}). "
                         f"Ora è {len(net)}.")

    # Prefissi/suffissi per sommare velocemente
    dev_prefix  = np.concatenate([[0.0], np.cumsum(dev)])           # sum dei primi k layer (k=0..N)
    edge_suffix = np.concatenate([np.cumsum(edge[::-1])[::-1], [0]])# sum dei layer k..N-1 + 0

    totals = dev_prefix[:N+1] + net[:N+1] + edge_suffix[:N+1]
    best_k = int(np.argmin(totals))

    best_components = {
        "dev_prefix":  float(dev_prefix[best_k]),
        "edge_suffix": float(edge_suffix[best_k]),
        "network_time": float(net[best_k]),
    }
    
    return best_k, best_components



def compute_network_times(layers_size, network_speed, network_stability):
    network_times = []
    for layer in layers_size:
        layer_corrected_size = (layer * 4) / 1024
        network_time = layer_corrected_size / (network_speed*network_stability)
        network_times.append(network_time)
    return network_times

def edge_inference():
    inference_times = []
    time_layer_0 = 0.012
    time_layer_1 = 0.004
    time_layer_6 = 0.001
    base_time = 0.001 # tempo di tutti gli altri layer
    for i in range(0,58):
        if i == 0:
            t = time_layer_0 + random.uniform(0,base_time)
        elif i == 1:
            t = time_layer_1 + random.uniform(0,base_time)
        else:
            t = base_time + random.uniform(0,base_time)

        t *= np.random.normal(1,0.1)
        inference_times.append(t)
        #print(f"Layer {i}, simulated edge inference time: {t}")
    return inference_times

def edge_inference_with_speedup(speedup):
    inference_times = []
    time_layer_0 = 0.012
    time_layer_1 = 0.004
    time_layer_6 = 0.001
    base_time = 0.001 # tempo di tutti gli altri layer
    for i in range(0,58):
        if i == 0:
            t = (time_layer_0 + random.uniform(0,base_time)) / speedup
        elif i == 1:
            t = (time_layer_1 + random.uniform(0,base_time)) / speedup
        else:
            t = (base_time + random.uniform(0,base_time)) / speedup

        t *= np.random.normal(1,0.1)
        inference_times.append(t)
        #print(f"Layer {i}, simulated edge inference time: {t}")
    return inference_times

def device_inference(server_speedup):
    inference_times = []
    time_layer_0 = 0.012
    time_layer_1 = 0.004
    time_layer_6 = 0.001
    base_time = 0.001 # tempo di tutti gli altri layer
    for i in range(0,58):
        if i == 0:
            t = (time_layer_0 + random.uniform(0,base_time)) * server_speedup
        elif i == 1:
            t = (time_layer_1 + random.uniform(0,base_time)) * server_speedup
        else:
            t = (base_time + random.uniform(0,base_time)) * server_speedup
        t *= np.random.normal(1,0.1)
        inference_times.append(t)
        #print(f"Layer {i}, simulated device inference time: {t}")
    return inference_times


def save_data_csv(network_stability, network_speed, server_speedup, best_layer, best_components, filename="simulated_results.csv"):
    server_speedup_dict = {1: "x1", 2: "x2", 5:"x5", 10: "x10",25: "x25", 50:"x50", 100: "x100"}
    network_speed_dict = {25000: "good", 5000: "mid", 1000: "bad"}
            
    file_exists = os.path.isfile(filename)
    with open(filename, mode="a", newline="") as f:
        writer = csv.writer(f)
        # Scrivi intestazione se il file è nuovo
        if not file_exists:
            writer.writerow(["server_speedup_label","server_speedup","network_speed_label", "network_speed","network_stability", "split_layer", "device_inference_time", "edge_inference_time", "network_time"])
        
        # Scrivi i valori (qui metti quelli che già calcoli nei log)
        writer.writerow([
            server_speedup_dict[server_speedup],              # scenario
            server_speedup,                 # server speedup
            network_speed_dict[network_speed],
            network_speed,             # network speed
            network_stability,
            best_layer,         # split scelto
            best_components["dev_prefix"],
            best_components["edge_suffix"],
            best_components["network_time"]
        ])


def simulated_scenario_server_slowdowns(stability, speed, layers_size, time_interval = 100):
    for i in range(time_interval):
        network_stability = np.random.normal(1, stability)
        if network_stability < 0:
            network_stability = 1

        network_times = compute_network_times(layers_size, speed, network_stability)
        #edge_times = edge_inference()
        device_times = device_inference(1)
        
        if i <= 10:
            speedup = 100
        elif i > 10 and i <= 25:
            speedup = 10
        elif i > 25 and i <= 30:
            speedup = 100
        elif i > 30 and i <= 35:
            speedup = 10
        elif i > 25 and i <= 60:
            speedup = 1
        elif i > 60 and i <= 75:
            speedup = 10
        elif i > 75 and i <= 90:
            speedup = 2
        else:
            speedup = 100
        
        edge_times = edge_inference_with_speedup(speedup)
        #device_times = device_inference(speedup)
        print(f"SERVER SPEEDUP {speedup} - ITERATION {i}")
        
        best_layer, best_components = offloading_algo(edge_times, device_times, network_times)
        print(f"\tBest layer {best_layer} - times = {best_components}")

        save_data_csv(stability, speed, speedup, best_layer, best_components, filename="server_slowdowns.csv")


def variable_speedup(network_stabilities, network_speeds, server_speedups, layers_size):
    for stability in network_stabilities:
        for speed in network_speeds:
            for i in range(0,1000):
                speedup = random.choice(server_speedups)
                print(f"NETWORK STABILITY: {stability} - NETWORK SPEED {speed} - SERVER SPEEDUP {speedup} - ITERATION {i}")
                network_stability = np.random.normal(1, stability)
                if network_stability < 0:
                    network_stability = 1

                network_times = compute_network_times(layers_size, speed, network_stability)
                #print(f"network len: {len(network_times)}")
                edge_times = edge_inference_with_speedup(speedup)
                #print(f"edge len: {len(edge_times)}")
                device_times = device_inference(1)
                #print(f"dev len: {len(device_times)}")
                
                best_layer, best_components = offloading_algo(edge_times, device_times, network_times)
                print(f"\tBest layer {best_layer} - times = {best_components}")

                save_data_csv(stability, speed, speedup, best_layer, best_components, filename="simulated_results_variable_speedup.csv")

# ---------------------
# MAIN
# ---------------------
def main():
    server_speedups = [1,2,5,10,25,50,100]
    server_slowdowns = [1,2,5,10,25,50,100]
    network_speeds = [25000, 5000, 1000]
    network_stabilities = [0.05, 0.1, 0.15, 0.2, 0.35, 0.5]

    with open("layer_size.csv", encoding="utf-8") as f:
        layers_size = [float(line) for line in f if line.strip()]

    variable_speedup(network_stabilities, network_speeds, server_speedups, layers_size)   
    simulated_scenario_server_slowdowns(network_stabilities[0], network_speeds[0], layers_size)
    
    for stability in network_stabilities:
        for speed in network_speeds:
            for speedup in server_speedups:
                for i in range(0,100):
                    print(f"NETWORK STABILITY: {stability} - NETWORK SPEED {speed} - SERVER SPEEDUP {speedup} - ITERATION {i}")
                    network_stability = np.random.normal(1, stability)
                    if network_stability < 0:
                        network_stability = 1

                    network_times = compute_network_times(layers_size, speed, network_stability)
                    #print(f"network len: {len(network_times)}")
                    #edge_times = edge_inference()
                    edge_times = edge_inference_with_speedup(speedup)
                    #print(f"edge len: {len(edge_times)}")
                    #device_times = device_inference(speedup)
                    device_times = device_inference(1)
                    #print(f"dev len: {len(device_times)}")
                    
                    best_layer, best_components = offloading_algo(edge_times, device_times, network_times)
                    print(f"\tBest layer {best_layer} - times = {best_components}")

                    save_data_csv(stability, speed, speedup, best_layer, best_components, filename="simulated_results_server_speedup.csv")
    
main()


