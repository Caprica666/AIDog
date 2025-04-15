
import httpx
import flask
from flask import Flask, request, jsonify

app = Flask(__name__)

# URL of the MCP agent
UNITY_SERVER_URL = "http://localhost:5000"

# Make a request to the Unity connection for a new image 
@app.route('/image_from_unity', methods=['GET'])
def image_from_unity():
    data = request.json
    object_name = data.get('object_name')

    if not object_name:
        return jsonify({"error": "Object name is required"}), 400
    url = f"http://{UNITY_SERVER_URL}/image_from_unity?object_name={object_name}"
    response = httpx.get(url)
    return response.status_code == 200

# Post the bounds for an object to Unity
@app.route('/bounds_to_unity', methods=['POST'])
def bounds_to_unity(object_name, bbox):
    # Send the bounding box to Unity
    url = f"http://{UNITY_SERVER_URL}/bounds_to_unity"
    payload = {"object_name": object_name, "bounding_box": bbox}
    response = httpx.post(url, json=payload)
    return response.status_code == 200

if __name__ == '__main__':
    app.run(port=8000)