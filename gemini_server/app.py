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
import json
import flask
import io
import os
from gemini_connection import GeminiClient
from unity_connection import UnityConnection
from flask import Flask, render_template, request, url_for
import logging


UNITY_APP_URL = "http://localhost:5000"
UNITY_CONNECT_PORT = 5001
USE_GEMINI = False  # Set to False to disable Gemini usage
USE_PNG_FILE = True  # Set to True to use a PNG file instead of bas64 image data
INDEX_HTML = "index.html"
INDEX_HTML_PNG = "index_png.html"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("UserInterface")
logger.setLevel(logging.DEBUG)

if USE_GEMINI:
    gemini = GeminiClient(logger)
app = Flask(__name__)
static_dir = os.path.join(app.root_path, 'static')
unity = UnityConnection(app, UNITY_APP_URL, logger)

@app.route("/", methods=["GET", "POST"])
def show_startup_page():
    """Display the startup page and handle form submissions."""
    logger.debug("displaying index.html")
    return render_template(INDEX_HTML)

@app.route("/submit_command", methods=["POST"])
def submit_command():
    """Handle form submission and process the command."""
    command = request.form.get("command")
    if command:
        response = on_command_received(command)
        return response
    return render_template(INDEX_HTML, status_line="No command provided.")

#
# Called when the user enters a command and submits the form.
# The server should ask the Unity application for a new image.    
def on_command_received(command):
    """Handle the command received from the user."""
    logger.debug("on_command_received  ", command)
    # if the image cannot be obtained, show the error in the status line
    image = unity.image_from_unity()
    if image is None:
        status_line = "Failed to get image from Unity."
        return status_line
    if USE_PNG_FILE:
        filename = None
        if USE_GEMINI:
            # Ask Gemini to generate a filename based on the prompt
            filename = gemini.convert_prompt_to_filename(command)
        if filename is None:
            filename = command.replace(" ", "_")
        filename = filename + ".png"      
        # Save the image to disk
        fullpath = os.path.join(static_dir, filename)
        with open(fullpath, "wb") as fd:
            fd.write(image)
    # Use Gemini to find the object in the image
    # Parse the response from Gemini and convert it to a dictionary
    try:
        if USE_GEMINI:
            response = gemini.find_objects_in_image(command, image)    
            response_dict = json.loads(response)
            # Check if the response contains bounding boxes
            if response_dict:
                first_entry = response_dict[0]
                object_name = first_entry['label']
                gemini_bbox = first_entry['box_2d']
                object_name = first_entry['label']
            else:
                status_line = "No objects found."
        else:
            gemini_bbox = [469, 638, 585, 765]
            object_name = "test_object"
        # gemini returns the bounding box ymin, xmin, ymax, xmax in a 1000x1000 coordinate system
        # convert it xmin, ymin, width, heigth in a 512x512 coordinate system
        bbox = [0, 0, 0, 0]
        bbox[0] = gemini_bbox[1]  # xmin
        bbox[1] = gemini_bbox[0]  # ymin   
        bbox[3] = gemini_bbox[2] - gemini_bbox[0]  # ymax - ymin
        bbox[2] = gemini_bbox[3] - gemini_bbox[1]  # xmax - xmin
        bbox = [int((coord * 512) / 1000) for coord in bbox]

        # Send the bounding box to Unity
        unity.bounds_to_unity(object_name, bbox)
        status_line = f"Found object: {object_name} {bbox}"
        if USE_PNG_FILE:
            return draw_image_and_box_file(filename, bbox)
        else: 
            return draw_image_and_box_data(image, bbox)
    except json.JSONDecodeError as e:
        status_line = "Failed to parse Gemini response. {e}"
    return status_line 
    
def draw_image_and_box_data(image_png_data, bbox):
    """
    Draw the bounding box on the image.
    
    Args:
        image_png_data: The image data as a PNG encoded byte array
        bbox: The bounding box coordinates (x, y, width, height)   
    """
    # Convert the image to a format suitable for display in HTML
    image_memory_file = io.BytesIO(image_png_data)
    image_data = image_memory_file.getvalue()
    imageb64 = base64.b64encode(image_data).decode('utf-8')
    return render_template(INDEX_HTML, bbox_x=bbox[0], bbox_y=bbox[1],
                           bbox_width=bbox[2], bbox_height=bbox[3], image_data=imageb64)

def draw_image_and_box_file(filename, bbox):
    """
    Draw the bounding box on the image.
    
    Args:
        filename: The name of the PNG file to display
        bbox: The bounding box coordinates (x, y, width, height)
    """
    return render_template(INDEX_HTML_PNG, bbox_x=bbox[0], bbox_y=bbox[1],
                           bbox_width=bbox[2], bbox_height=bbox[3], image_png=url_for('static', filename=filename))


def main():
    logger.debug("running web server")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    app.run(port=UNITY_CONNECT_PORT, use_reloader=False, debug=True)
    
if __name__ == "__main__":
    main()



