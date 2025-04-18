import httpx
import flask
from flask import Flask, request, jsonify
import numpy as np
from PIL import Image
import io

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("UnityConnection")
app = Flask(__name__)

# URL of the MCP agent
UNITY_APP_URL = "http://localhost:5000"
UNITY_CONNECT_PORT = 5001

# Let Unity know we are running
@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"message": "Unity connection is alive"}), 200

def image_from_unity(object_name):
    """Fetch an image from Unity for the specified object and convert it to a 2D array."""
    if not object_name:
        return None

    url = f"{UNITY_APP_URL}/image_from_unity?object_name={object_name}"
    response = httpx.get(url)
    logger.debug("image_from_unity response ", response.status_code)

    if response.status_code == 200 and response.headers.get('Content-Type') == 'application/octet-stream':
        image_data = response.content  # Extract binary data from the response
        raw_pixels = io.BytesIO(image_data).getvalue()    
        return raw_pixels
    else:
        return None


# Post the bounds for an object to Unity
@app.route('/bounds_to_unity', methods=['POST'])
def bounds_to_unity():
    # Extract data from the request JSON
    data = request.json
    object_name = data.get('object_name')
    bbox = data.get('bounding_box')

    if not object_name or not bbox:
        return jsonify({"error": "Object name and bounding box are required"}), 400

    url = f"{UNITY_APP_URL}/bounds_to_unity"
    payload = {"object_name": object_name, "bounding_box": bbox}
    response = httpx.post(url, json=payload)

    if response.status_code == 200:
        return jsonify({"message": "Bounding box sent successfully"}), 200
    else:
        return jsonify({"error": "Failed to send bounding box to Unity"}), response.status_code

def start_server():
    """Start the Flask server for Unity connection."""
    print("Waiting for debugger to attach...")
    # debugpy.wait_for_client()
    app.run(port=UNITY_CONNECT_PORT, use_reloader=False, debug=False)