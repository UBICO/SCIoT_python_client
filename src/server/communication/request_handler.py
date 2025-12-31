import json
import yaml
import random
from pathlib import Path
import numpy as np
from PIL import Image

from server.edge.edge_initialization import Edge
from server.offloading_algo.offloading_algo import OffloadingAlgo

from server.commons import OffloadingDataFiles
from server.commons import EvaluationFiles
from server.commons import InputDataFiles

from server.logger.log import logger

from server.communication.message_data import MessageData

from server.models.model_input_converter import ModelInputConverter
from server.delay_simulator import DelaySimulator
from server.variance_detector import VarianceDetector

import struct


def load_network_delay_config():
    """Load network delay configuration from settings.yaml"""
    settings_path = Path(__file__).parent.parent / "settings.yaml"
    try:
        with open(settings_path, 'r') as f:
            settings = yaml.safe_load(f)
            return settings.get('delay_simulation', {}).get('network')
    except Exception as e:
        logger.warning(f"Could not load network delay config: {e}")
        return None


def load_local_inference_config():
    """Load local inference mode configuration from settings.yaml"""
    settings_path = Path(__file__).parent.parent / "settings.yaml"
    try:
        with open(settings_path, 'r') as f:
            settings = yaml.safe_load(f)
            return settings.get('local_inference_mode', {})
    except Exception as e:
        logger.warning(f"Could not load local inference config: {e}")
        return {'enabled': False, 'probability': 0.0}


class RequestHandler():
    # Class-level variance detector (shared across all requests)
    variance_detector = VarianceDetector(window_size=10, variance_threshold=0.15)
    
    def __init__(self):
        # Load network delay configuration
        network_delay_config = load_network_delay_config()
        self.network_delay = DelaySimulator(network_delay_config)
        if self.network_delay.enabled:
            logger.info(f"Network delay simulation enabled: {self.network_delay.get_delay_info()}")
        
        # Load local inference mode configuration
        local_config = load_local_inference_config()
        self.local_inference_enabled = local_config.get('enabled', False)
        self.local_inference_probability = local_config.get('probability', 0.0)
        if self.local_inference_enabled:
            logger.info(f"Local inference mode enabled with probability {self.local_inference_probability:.0%}")
    
    def should_force_local_inference(self) -> bool:
        """
        Determine if this request should force local-only inference (no offloading).
        Used to refresh/retest device inference times periodically.
        
        Returns:
            True if local inference should be forced, False otherwise
        """
        if not self.local_inference_enabled:
            return False
        
        # Randomly decide based on probability
        should_force = random.random() < self.local_inference_probability
        
        if should_force:
            logger.info("Forcing local-only inference to refresh device times")
        
        return should_force
    
    def handle_registration(self, client_id):
        # Apply network delay before responding
        if self.network_delay.enabled:
            delay = self.network_delay.apply_delay()
            logger.debug(f"Applied network delay: {delay*1000:.2f}ms")
        return client_id

    def handle_device_input(self, rgb565_image, height, width, client_id=None):
        # Apply network delay after receiving input
        if self.network_delay.enabled:
            delay = self.network_delay.apply_delay()
            logger.debug(f"Applied network delay: {delay*1000:.2f}ms")
        
        image_array = ModelInputConverter.convert_rgb565_to_nparray(rgb565_image, height, width)
        image = Image.fromarray(image_array, 'RGB')
        image.save(InputDataFiles.input_data_file_path)
        return
    
    def handle_device_inference_result(self, body, received_timestamp, client_id=None):
        message_data = RequestHandler._from_raw('device_inference_result', body)
        message_data = RequestHandler._extend_message_data(message_data, received_timestamp, body)
        
        if client_id:
            logger.debug(f"Processing inference result from client {client_id}")
        
        with open(OffloadingDataFiles.data_file_path_device, 'r') as f:
            device_inference_times = json.load(f)
        
        # Update device inference times with exponential moving average (alpha=0.2)
        alpha = 0.2  # Weight for new measurement
        for l_id, inference_time in enumerate(message_data.device_layers_inference_time):
            layer_key = f"layer_{l_id}"
            if layer_key in device_inference_times:
                # Smooth the time with existing history
                device_inference_times[layer_key] = alpha * inference_time + (1 - alpha) * device_inference_times[layer_key]
            else:
                device_inference_times[layer_key] = inference_time
            
            # Track variance for this layer
            RequestHandler.variance_detector.add_device_measurement(l_id, inference_time)
        
        with open(OffloadingDataFiles.data_file_path_device, 'w') as f:
            json.dump(device_inference_times, f, indent=4)
        
        # Finish inference on edge (only if device didn't complete all layers)
        # When offloading_layer_index is -1 or LAST_LAYER, all inference was done on device
        if message_data.offloading_layer_index == -1 or message_data.offloading_layer_index >= 58:
            # All layers completed on device, no edge inference needed
            prediction = np.array(message_data.layer_output, dtype=np.float32)
            logger.debug(f"All layers completed on device (layer_index={message_data.offloading_layer_index})")
        else:
            # Continue inference on edge from where device stopped
            prediction = Edge.run_inference(message_data.offloading_layer_index, np.array(message_data.layer_output, dtype=np.float32))
        
        logger.debug(f"Prediction: {prediction.tolist()}")
        MessageData.save_to_file(EvaluationFiles.evaluation_file_path, message_data.to_dict())
        
        # Apply network delay before responding
        if self.network_delay.enabled:
            delay = self.network_delay.apply_delay()
            logger.debug(f"Applied network delay before response: {delay*1000:.2f}ms")
        
        # run offloading algorithm
        device_inference_times, edge_inference_times, layers_sizes = RequestHandler._load_stats()
        logger.debug(f"Loaded stats data")
        
        # Check if variance detected - potentially need to re-test offloading
        if RequestHandler.variance_detector.should_retest_offloading():
            logger.warning("Offloading algorithm may need re-evaluation due to inference time variance")
        
        # Check if we should force local-only inference for refreshing times
        if self.should_force_local_inference():
            # Force all layers on device (offloading layer = -1 means no offloading)
            best_offloading_layer = -1
            logger.info("Forcing all layers on device for time refresh (local inference mode)")
        else:
            offloading_algo = OffloadingAlgo(
                avg_speed=message_data.avg_speed,
                num_layers=len(layers_sizes),
                layers_sizes=list(layers_sizes),
                inference_time_device=list(device_inference_times),
                inference_time_edge=list(edge_inference_times)
            )
            best_offloading_layer = offloading_algo.static_offloading()
        
        return best_offloading_layer
    
    def handle_offloading_layer(self, best_offloading_layer, client_id=None):
        if client_id:
            logger.debug(f"Offloading decision for client {client_id}: layer {best_offloading_layer}")
        return best_offloading_layer

    @staticmethod
    def _load_stats():
        """ Loads the offloading stats from the JSON files """
        with open(OffloadingDataFiles.data_file_path_device, 'r') as file:
            device_inference_times = json.load(file)
            device_inference_times = list({k: v for k, v in device_inference_times.items()}.values())

        with open(OffloadingDataFiles.data_file_path_edge, 'r') as file:
            edge_inference_times = json.load(file)
            edge_inference_times = list({k: v for k, v in edge_inference_times.items()}.values())

        with open(OffloadingDataFiles.data_file_path_sizes, 'r') as file:
            layers_sizes = json.load(file)
            layers_sizes = list({k: v for k, v in layers_sizes.items()}.values())
        
        return device_inference_times, edge_inference_times, layers_sizes

    @staticmethod
    def _from_raw(topic: str, payload: bytes):
        """Parse the raw message payload into a MessageData instance."""
        try:
            message_data = {}
            message_content = {}

            # decode the payload from bytes to values and parse as JSON
            message_data["timestamp"] = struct.unpack('d', payload[:8])[0]
            offset = 8
            message_data["device_id"] = payload[offset:offset+9].decode()
            offset += 9
            message_data["message_id"] = payload[offset:offset+4].decode()
            offset += 4
            message_content["offloading_layer_index"] = struct.unpack('i', payload[offset:offset+4])[0]
            offset += 4
            layer_output_size = struct.unpack('I', payload[offset:offset+4])[0]
            offset += 4
            message_content["layer_output"] = struct.unpack(f'<{int(layer_output_size/4)}f', payload[offset:offset+layer_output_size])
            offset += layer_output_size
            layers_inference_time_size = struct.unpack('i', payload[offset:offset+4])[0]
            offset += 4
            message_content["layers_inference_time"] = struct.unpack(f'<{int(layers_inference_time_size/4)}f', payload[offset:offset+layers_inference_time_size])
            message_data["message_content"] = message_content

            decoded_payload = json.dumps(message_data)

            message_content = message_data["message_content"]
            # return an instance of MessageData with extracted fields
            return MessageData(
                topic=topic,
                payload=decoded_payload,
                device_id=message_data["device_id"],
                message_id=message_data["message_id"],
                message_content=message_content,
                timestamp=message_data["timestamp"],
            )
        except json.JSONDecodeError:
            # handles payload that cannot be parsed as JSON
            raise

    @staticmethod
    def _extend_message_data(message_data: MessageData, received_timestamp: float, payload) -> MessageData:
        """Extend the message data with additional information.

        Args:
            message_data (MessageData): The message data to extend.
            received_timestamp (float): The timestamp of the message reception.

        Returns:
            MessageData: The extended message data.
        """
        # update stats info
        message_data.received_timestamp = received_timestamp
        message_data.payload_size = MessageData.get_bytes_size(payload)
        message_data.synthetic_latency = MessageData.get_synthetic_latency()
        message_data.latency = MessageData.get_latency(message_data.timestamp, message_data.received_timestamp)
        message_data.avg_speed = MessageData.get_avg_speed(
            message_data.payload_size,
            message_data.latency,
            message_data.synthetic_latency
        )
        # update offloading info
        (
            message_data.offloading_layer_index,
            message_data.layer_output,
            message_data.device_layers_inference_time
        ) = MessageData.get_offloading_info(message_data.message_content)
        return message_data