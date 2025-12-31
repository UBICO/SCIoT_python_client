import json
import time
from functools import wraps

import tensorflow as tf

from server.commons import OffloadingDataFiles
from server.commons import ModelFiles
from server.logger.log import logger
from server.models.model_manager_config import ModelManagerConfig
from server.delay_simulator import DelaySimulator
from server.variance_detector import VarianceDetector


def track_inference_time(func):
    """
    This decorator is used to track the execution time of a function.
    :param func: the function to be decorated
    :return: the decorated function
    """

    @wraps(func)
    def wrapper(self, layer_id: int, layer_offset: int, *args, **kwargs) -> object:
        # Start the timer
        start_time = time.perf_counter()
        # Execute the original function (predict_single_layer)
        result = func(self, layer_id, layer_offset, *args, **kwargs)
        # Calculate the elapsed time
        elapsed_time = time.perf_counter() - start_time
        
        layer_key = str(layer_id - layer_offset)
        # Use exponential moving average to smooth times (alpha=0.2 gives 80% weight to history)
        if layer_key in self.inference_times:
            alpha = 0.2  # Weight for new measurement
            self.inference_times[layer_key] = alpha * elapsed_time + (1 - alpha) * self.inference_times[layer_key]
        else:
            self.inference_times[layer_key] = elapsed_time
        
        logger.debug(f"Edge Inference for layer [{layer_id - layer_offset}] took {elapsed_time:.4f} seconds (smoothed: {self.inference_times[layer_key]:.4f}s)")
        
        # Track variance for edge inference times
        if hasattr(self, 'variance_detector') and self.variance_detector:
            self.variance_detector.add_edge_measurement(int(layer_key), elapsed_time)
        
        # Save inference times in real-time after each layer
        self.save_inference_times()
        
        return result

    return wrapper


class ModelManager:
    """This class is used to manage the model and its layers.

    Args:
        save_path: The path to save the model.
        model_path: The path to the model.

    Attributes:
        save_path: The path to save the model.
        model_path: The path to the model.
        num_layers: The number of layers in the model.
        model: The model.
        inference_times: A dictionary to store the inference times for each layer.
    """

    def __init__(self, save_path: str = ModelManagerConfig.SAVE_PATH, model_path: str = ModelManagerConfig.MODEL_PATH,
                 inference_times: dict = {}, computation_delay_config: dict = None, variance_detector: VarianceDetector = None):
        self.save_path = save_path
        self.model_path = model_path
        self.num_layers = None
        self.model = None
        # dictionary to store inference times for each layer
        self.inference_times = inference_times
        # cache for TFLite interpreters to avoid recreation overhead
        self._interpreter_cache = {}
        # delay simulator for computation
        self.computation_delay = DelaySimulator(computation_delay_config)
        if self.computation_delay.enabled:
            logger.info(f"Computation delay simulation enabled: {self.computation_delay.get_delay_info()}")
        # variance detector for tracking inference time stability
        self.variance_detector = variance_detector

    def load_model(self, model_path: str = ModelManagerConfig.MODEL_PATH):
        """Load the model from the given path.
        Args:
            model_path: The path to the model.
        Returns:
            None
        """
        logger.debug(f"Loading model from path: {model_path}")
        try:
            self.model_path = model_path
            self.model = tf.keras.models.load_model(f'{ModelFiles.model_save_path}/test/{model_path}')
            self.num_layers = len(self.model.layers)
        except Exception as e:
            print(f"Error loading model: {e}")
            logger.error(f"Failed to load model: {e}")

    def get_model_layer(self, layer_id: int) -> tf.keras.layers.Layer:
        """Get the layer with the given id from the model.
        Args:
            layer_id: The id of the layer.
        Returns:
            The layer with the given id.
        """
        return self.model.layers[layer_id]

    @staticmethod
    def get_layer_size_in_bytes(layer: tf.keras.layers.Layer, layer_output: tf.Tensor) -> int:
        """Calculate the size of a Keras layer's weights in bytes.
        Args:
            layer: A Keras layer.
            layer_output: The output of the layer.
        Returns:
            The size of the layer in bytes.
        """

        """
        total_size_in_bytes = 0
        # Iterate through the weights of the layer
        for weight in layer.weights:
            # Get the shape of the weight tensor
            weight_shape = weight.shape
            # Get the dtype of the weights (as a string, like 'float32')
            dtype = weight.dtype
            # Use np.dtype directly since dtype is a string (e.g., 'float32')
            size_per_element = np.dtype(dtype).itemsize
            # Calculate the total number of elements
            num_elements = np.prod(weight_shape)
            # Total size in bytes for this weight
            size_in_bytes = num_elements * size_per_element
            total_size_in_bytes += size_in_bytes
        """
        # get the dtype of the output tensor
        dtype = layer_output.dtype
        # calculate the size in size_in_bytes and convert to Python scalar
        size_in_bytes = tf.reduce_prod(layer_output.shape) * tf.constant(dtype.itemsize)
        size_in_bytes = size_in_bytes.numpy()
        return size_in_bytes

    @track_inference_time
    def predict_single_layer(self, layer_id: int, layer_offset: int, layer_input_data: object) -> object:
        """Predict the output of a single layer.
        Args:
            layer_id: The id of the layer.
            layer_input_data: The input data to the layer.
        Returns:
            The output of the layer.
        """
        logger.debug(f"Making a prediction for layer [{layer_id - layer_offset}]")

        layer_key = layer_id - layer_offset
        
        # Apply artificial computation delay if configured
        if self.computation_delay.enabled:
            delay = self.computation_delay.apply_delay()
            logger.debug(f"Applied artificial computation delay: {delay*1000:.2f}ms")
        
        # Check if interpreter is already cached
        if layer_key not in self._interpreter_cache:
            # Initialize interpreter with layer tflite model
            interpreter = tf.lite.Interpreter(
                model_path=f'{ModelFiles.model_save_path}/test/{ModelManagerConfig.MODEL_DIR_PATH}/layers/tflite/submodel_{layer_key}.tflite')
            interpreter.allocate_tensors()
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()
            # Cache the interpreter and its details
            self._interpreter_cache[layer_key] = {
                'interpreter': interpreter,
                'input_details': input_details,
                'output_details': output_details
            }
        else:
            # Retrieve cached interpreter
            cached = self._interpreter_cache[layer_key]
            interpreter = cached['interpreter']
            input_details = cached['input_details']
            output_details = cached['output_details']

        # set input tensor
        for i, input_detail in enumerate(input_details):
            interpreter.set_tensor(input_detail['index'], layer_input_data[i].reshape(input_detail['shape']))

        # run inference
        interpreter.invoke()

        # return prediction
        return interpreter.get_tensor(output_details[0]['index'])

    def save_inference_times(self, save_path: str | None = None):
        """Save the inference times to a JSON file.
        Args:
            save_path: The path to save the inference times.
        Returns:
            None
        """
        if save_path is not None:
            self.save_path = save_path
        self.save_path = self.save_path[:-1] if self.save_path[-1] == "/" else self.save_path
        inference_times = self.inference_times
        try:
            with open(OffloadingDataFiles.data_file_path_edge, "w") as f:
                json.dump(inference_times, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save inference times: {e}")
