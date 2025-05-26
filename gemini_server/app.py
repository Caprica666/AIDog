#
# Web server to find objects in a Unity 3D scene.
# This server accepts commands to find named objects in the scene.
# The images of the scene are obtained by requesting them from the Unity application.
# The Unity application is running on a different port and is responsible for rendering the scene.
# 3D scene, capturing images from the scene's camera and sending them to this server.
# The server uses Google Gemini to find the objects in the images returned from Unity.
#
# The server should display an input form for the user to enter the command.
# When a command is submitted, the server asks the Unity application for a new image.
# The image is sent to Gemini, along with the command.
# If the object is found in the image, its bounding box is sent back to the Unity application.
#
# The server should display an HTML page with an input form for the user to enter the command.
# Below the command, it should display the current image returned from Unity.
# If a bounding box is found, it should be displayed on the image.
# The server should display a status line showing the text returned from Gemini
# and the bounding box coordinates, if any.
#

#
# Display the HTML page with the input form and an area for the current image.
# The page should also display the text returned from Gemini and the bounding box coordinates.
#

import base64
import numpy as np
import os
from PIL import Image
from gemini_connection import GeminiClient
from openai_connection import OpenAIClient
from unity_connection import UnityConnection
from robot_controller import RobotController
from flask import Flask, render_template, request
import logging

UNITY_APP_URL = "http://localhost:5000"
UNITY_CONNECT_PORT = 5001
AI_PLATFORM = "openai"  # Accepts "openai" or "gemini"
INDEX_HTML = "index.html"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("UserInterface")
logger.setLevel(logging.DEBUG)
            
if AI_PLATFORM == "gemini":
    aihelper = GeminiClient(logger, model_name = "gemini-2.0-flash")
elif AI_PLATFORM == "openai":
    aihelper = OpenAIClient(logger, model_name = "gpt-4o-mini")
else:
    raise ValueError("AI_PLATFORM must be either 'gemini' or 'openai'.")
app = Flask(__name__)
static_dir = os.path.join(app.root_path, 'static')
unity = UnityConnection(app, UNITY_APP_URL, logger)
robot = RobotController(logger, aihelper, unity)

#
# Display the startup HTML page
#
@app.route("/", methods=["GET", "POST"])
def show_startup_page():
    """Display the startup page and handle form submissions."""
    logger.debug("displaying index.html")
    return render_template(INDEX_HTML)

#
# Called when a command is submitted to the robot.
# 

@app.route("/submit_command", methods=["POST"])
def submit_command():
    """
    Handle form submission and process the command.
    
    Args:
        request: The Flask request object containing the command to the robot.
    Returns:
        A JSON response indicating the status of the command and the bounding box coordinates.
        status: The status of the command or an error message
        action: The action to take (e.g., "resubmit" if the command needs to be reprocessed)
        image: The image data as a base64 encoded string
        object_name: The name of the object found in the image
        bbox: The bounding box coordinates of the object in the image
    """
    command = request.form.get("command")
    if command:
        result = on_command_received(command)
    else:
        result = { "status": "No command provided.", "action": None }
    return result

#
# Called when the user enters a command and submits the form.
# The server should ask the Unity application for a new image.    
def on_command_received(command):
    """
    Handles the command received from the user and processes it.
    
    Args:
        command: The command to the robot.
        
    Returns:
        A JSON response indicating the status of the command and the bounding box coordinates.
        status: The status of the command or an error message
        action: The action to take (e.g., "resubmit" if the command needs to be reprocessed)
        image: The image data as a base64 encoded string
        object_name: The name of the object found in the image
        bbox: The bounding box coordinates of the object in the image in the format [x, y, width, height]
    """
    logger.debug("on_command_received  ", command)
    result = robot.process_command(command)
    if "label" in result and "bbox" in result:
        object_name = result["label"]
        bbox = result["bbox"]
        result["status"] = f"Found object: {object_name} {bbox}"
    if "image" in result:
        result["image"] = process_image(result["image"])   
    return result 
    
def process_image(image_png_data):
    """
    Convert the image data to a format suitable for display in HTML.
    
    Args:
        image_png_data: The image data as a PNG encoded byte array
    Returns:
        A base64 encoded string representing the image data.
    """
    # Convert the image to a format suitable for display in HTML
    image_data = image_png_data.getvalue()
    imageb64 = base64.b64encode(image_data).decode('utf-8')
    return "data:image/png;base64," + imageb64
       
def main():
    logger.debug("running web server")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    app.run(port=UNITY_CONNECT_PORT, use_reloader=False, debug=True)
    
if __name__ == "__main__":
    main()



