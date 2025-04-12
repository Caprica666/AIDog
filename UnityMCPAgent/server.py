from flask import Flask, request, jsonify
import requests
import numpy as np
from PIL import Image
import threading
import queue

app = Flask(__name__)

# URL of the MCP agent
MCP_AGENT_URL = "http://localhost:5000"

# Queue to handle image streams
image_queue = queue.Queue()

# Dictionary to store results for each object name
results = {}

@app.route('/start_object_request', methods=['POST'])
def start_object_request():
    data = request.json
    object_name = data.get('object_name')

    if not object_name:
        return jsonify({"error": "Object name is required"}), 400

    # Initialize results for the object name
    results[object_name] = []

    # Start a thread to process the image stream
    threading.Thread(target=process_image_stream, args=(object_name,)).start()

    return jsonify({"message": "Object request started"})

@app.route('/get_bounds', methods=['GET'])
def get_bounds():
    object_name = request.args.get('object_name')

    if not object_name or object_name not in results:
        return jsonify({"error": "Invalid object name"}), 400

    return jsonify({"results": results[object_name]})

def process_image_stream(object_name):
    while True:
        try:
            # Get the next image from the queue
            queued_object_name, raw_image = image_queue.get(timeout=10)

            # Ensure the image corresponds to the current object name
            if queued_object_name != object_name:
                continue

            # Convert raw image data to a PIL image
            image = Image.fromarray(np.array(raw_image, dtype=np.uint8))

            # Send the image and object name to the MCP agent
            response = requests.post(f"{MCP_AGENT_URL}/process_image", json={
                "object_name": object_name,
                "raw_image": raw_image
            })

            if response.status_code == 200:
                bounding_box = response.json().get('bounding_box')
                results[object_name].append({"image": raw_image, "bounding_box": bounding_box})
            else:
                results[object_name].append({"image": raw_image, "error": "Failed to process image"})

        except queue.Empty:
            # Stop processing if no images are received for a while
            break

if __name__ == '__main__':
    app.run(port=8000)