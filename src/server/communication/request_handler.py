import json
import yaml
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


class RequestHandler():
    def __init__(self):
        # Load network delay configuration
        network_delay_config = load_network_delay_config()
        self.network_delay = DelaySimulator(network_delay_config)
        if self.network_delay.enabled:
            logger.info(f"Network delay simulation enabled: {self.network_delay.get_delay_info()}")
    
    def handle_registration(self, device_id):
        # Apply network delay before responding
        if self.network_delay.enabled:
            delay = self.network_delay.apply_delay()
            logger.debug(f"Applied network delay: {delay*1000:.2f}ms")
        return device_id

    def handle_device_input(self, rgb565_image, height, width):
        # Apply network delay after receiving input
        if self.network_delay.enabled:
            delay = self.network_delay.apply_delay()
            logger.debug(f"Applied network delay: {delay*1000:.2f}ms")
        
        image_array = ModelInputConverter.convert_rgb565_to_nparray(rgb565_image, height, width)
        image = Image.fromarray(image_array, 'RGB')
        image.save(InputDataFiles.input_data_file_path)
        return
    
    def handle_device_inference_result(self, body, received_timestamp):
        message_data = RequestHandler._from_raw('device_inference_result', body)
        message_data = RequestHandler._extend_message_data(message_data, received_timestamp, body)
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
        
        with open(OffloadingDataFiles.data_file_path_device, 'w') as f:
            json.dump(device_inference_times, f, indent=4)
        # finish inference
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
        offloading_algo = OffloadingAlgo(
            avg_speed=message_data.avg_speed,
            num_layers=len(layers_sizes),
            layers_sizes=list(layers_sizes),
            inference_time_device=list(device_inference_times),
            inference_time_edge=list(edge_inference_times)
        )
        return offloading_algo.static_offloading()
    
    def handle_offloading_layer(self, best_offloading_layer):
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