import tensorflow as tf

interpreter = tf.lite.Interpreter(model_path="tflite/submodel_0.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("Input shape:", input_details[0]['shape'])
print("Output shape:", output_details[0]['shape'])

