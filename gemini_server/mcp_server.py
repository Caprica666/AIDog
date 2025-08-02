import numpy as np
from PIL import Image
import json
from flask import Flask, request, jsonify
from yolo_connection import ObjectDetector

app = Flask(__name__)

yolo = ObjectDetector(model_name="yoloe-11l-seg.pt")

# State for the robot camera
total_angles = 360
current_angle = 0

@app.route('/mcp/turn_robot_camera', methods=['POST'])
def turn_robot_camera():
    """
    Turn the robot camera a specific number of degrees.
    Expects JSON: {"amount_to_turn": int, "direction": "clockwise"|"counterclockwise"}
    Returns: {"current_angle": int, "at_start_angle": bool}
    """
    global current_angle
    data = request.get_json()
    amount = data.get('amount_to_turn', 0)
    direction = data.get('direction', 'clockwise')
    if direction == 'clockwise':
        current_angle = (current_angle + amount) % total_angles
    else:
        current_angle = (current_angle - amount) % total_angles
    at_start_angle = (current_angle == 0)
    return jsonify({
        "current_angle": current_angle,
        "at_start_angle": at_start_angle
    })

@app.route('/mcp/detect_objects', methods=['POST'])
def detect_objects():
    """
    Detect objects in an image using YOLO.
    Expects multipart/form-data with 'label' and 'image' (PNG file).
    Returns: list of dicts with 'label' and 'bbox'.
    """
    label = request.form.get('label')
    image_file = request.files.get('image')
    if not label or not image_file:
        return jsonify({"error": "Missing label or image"}), 400
    image = Image.open(image_file.stream)
    image_array = np.array(image)
    if image_array.shape[-1] == 3:
        image_array = image_array[..., ::-1]  # RGB to BGR
    yolo.set_classes([label])
    detections = yolo.detect_objects(image_array)
    # Ensure output is JSON serializable
    for det in detections:
        if 'bbox' in det:
            det['bbox'] = [int(x) for x in det['bbox']]
    return jsonify(detections)

if __name__ == '__main__':
    app.run(port=5100, debug=True)
