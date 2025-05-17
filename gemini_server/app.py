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
from flask import Flask, render_template, request
import logging


UNITY_APP_URL = "http://localhost:5000"
UNITY_CONNECT_PORT = 5001
USE_GEMINI = True  # Set to False to disable Gemini usage
USE_PNG_FILE = False  # Set to True to use a PNG file instead of bas64 image data
INDEX_HTML = "index.html"
INDEX_HTML_PNG = "index_png.html"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("UserInterface")
logger.setLevel(logging.DEBUG)

if USE_GEMINI:
    gemini = GeminiClient(logger, "gemini-2.0-flash")
app = Flask(__name__)
static_dir = os.path.join(app.root_path, 'static')
unity = UnityConnection(app, UNITY_APP_URL, logger)

turn_params = { "start_angle" : 360, "current_angle" : 0 }

#
# Description of the function to turn the robot camera
# This function is called by Gemini when it needs to turn the robot camera.
#
turn_robot_camera_function = {
    "name": "turn_robot_camera",
    "description": "Turn the robot camera the specific number of degrees.",
    "parameters": {
        "type": "object",
        "properties": {
            "amount_to_turn": {
                "type": "integer",
                "description": "The number of degrees to turn the camera."
            },
            "start_angle": {
                "type": "integer",
                "description": "The starting angle of the camera before a series of turns."
            },
            "current_angle": {
                "type": "integer",
                "description": "The current angle of the camera before turning."
            },
            "direction": {
                "type": "string",
                "enum": ["clockwise", "counterclockwise"],
                "description": "The direction to turn the camera."
            }
        },
        "required": [ "amount_to_turn", "direction"]
    }
} 

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
    result = process_command(command)
    if "object_name" in result and "bbox" in result:
        object_name = result["object_name"]
        bbox = result["bbox"]
        result["status"] = f"Found object: {object_name} {bbox}"     
    return result 

def process_command(command):
    """
    Process the command given by the user to the robot.
    Currently this is a request to find objects in the image.
    The current image from the robot's camera is provided along with a function to turn the camera.
    If the command successfully finds an object, its name and bounding box are returned.
    If the LLM indicates the object is not found and requests to turn the camera,
    the camera is turned and another image is captured. In this case, the
    "action" field is set to "resubmit" indicating the caller should display the new image
    and submit the command again.
    Args:
        command: The command to the robot. 
    Returns:
        A JSON response indicating the status of the command and the bounding box coordinates.
        status: The status of the command or an error message
        action: The action to take (e.g., "resubmit" if the command needs to be reprocessed)
        image: The image data as a base64 encoded string
        object_name: The name of the object found in the image
        bbox: The bounding box coordinates of the object in the image   
    """
    # Use the LLM to find the object in the image
    # Provide the LLM with a function to turn the robot camera
    result = { "action": None }
    response = gemini.call_with_functions(command, unity.current_image, [turn_robot_camera_function])
    logger.debug("LLM response: ", response)
    if "status" in response and "ERROR" in response["status"]:
        result["status"] = response["status"]
        return result
    # If the LLM indicates the object is not found, check if it wants to turn the camera   
    # If the response contains a function call, execute the function
    # and pass the result back to the LLM        
    if "function_call" in response:
        function_call = response["function_call"]
        args = response["args"]
        print("Function to call: " + response["function_name"])
        if (response["function_name"] == "turn_robot_camera"):
            # capture the image from the robot camera
            # and pass the image data to the LLM as a PNG encoded byte array
            if "amount_to_turn" not in args or "direction" not in args:
                result["status"] = "Missing required arguments for turn_robot_camera function."
                logger.debug("Missing required arguments for turn_robot_camera function.")
                return result
            turn_params["amount_to_turn"] = args["amount_to_turn"]
            turn_params["direction"] = args["direction"]
            func_response = turn_robot_camera(turn_params)             
            if "error" in func_response:
                result["status"] = func_response["error"]
                return result
            turn_params["current_angle"] = func_response["current_angle"]
            result = { "action": "resubmit" }
            # if the function provided a result, call Gemini with the function result
            response = gemini.call_with_function_response(function_call, func_response, unity.current_image)
    # If the response contains a bounding box, include it in the result
    if "text" in response:
        if "json" in response["text"][:8]:
            result = process_bounding_box(response["text"], result)
        else:
            result["status"] = response["text"]
            result["action"] = None
    # If we have captured an image from the robot camera, include it in the result
    if unity.current_image:
        result["image"] = process_image(unity.current_image)
    return result
        
def process_bounding_box(response, result):
    """
    Process the bounding box returned from the LLM.
    Strip off the first 8 characters (the "json" prefix) and parse the JSON string.
    The coordinate system is 1000x1000, so convert it to the size of captured images..
    Args:
        response: The response from the LLM containing the bounding box information.
        result: The result dictionary to update with the bounding box information.
        
    Returns:
        A JSON response indicating the status of the command and the bounding box coordinates.  
        status: The status of the command or an error message
        action: The action to take (e.g., "resubmit" if the command needs to be reprocessed)
        object_name: The name of the object found in the image
        bbox: The bounding box coordinates of the object in the image     
    """
    text = response[8:]
    text = text[:text.rfind(']') + 1]
    bbox = [ 0, 0, 0, 0 ]
    try:
        response_dict = json.loads(text)
        logger.debug("Python dict: ", response_dict)
        if response_dict:
            first_entry = response_dict[0]
            object_name = first_entry['label']           
            if "bbox" in first_entry:
                gemini_bbox = first_entry['bbox']
            else:
                return { "status": "No objects found", "action": "resubmit"}
            # The LLM returns the bounding box ymin, xmin, ymax, xmax in a 1000x1000 coordinate system
            # convert it xmin, ymin, width, heigth in the coordinate system of the image
            gemini_bbox = [int((coord * unity.image_size) / 1000) for coord in gemini_bbox]
            bbox[0] = gemini_bbox[1]
            bbox[1] = gemini_bbox[0]
            bbox[2] = gemini_bbox[3] - gemini_bbox[1]
            bbox[3] = gemini_bbox[2] - gemini_bbox[0]
            result["bbox"] = bbox
            result["object_name"] = object_name
            result["status"] = f"Found object: {object_name} {bbox}"
            # Send the bounding box to Unity
            unity.bounds_to_unity(object_name, bbox)
    except json.JSONDecodeError as e:
        result["status"] = "Failed to parse LLM response."
        result["action"] = None
        logger.debug("Failed to parse LLM response", e.msg)
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
    image_memory_file = io.BytesIO(image_png_data)
    image_data = image_memory_file.getvalue()
    imageb64 = base64.b64encode(image_data).decode('utf-8')
    return "data:image/png;base64," + imageb64

def turn_robot_camera(args):
    """
    Turn the robot camera a specific number of degrees.
    
    Args: dictionary with the following arguments:
        turn_angle: The number of degrees to turn the camera.
        start_angle: The starting angle of the camera before a series of turns.
        current_angle" The current angle of the camera before this turn.
        direction: The direction to turn the camera ("clockwise" or "counterclockwise").
        
    Returns:
        at_start_angle: True if camera has been turned to the start angle, False otherwise.
        current_angle: The current angle of the camera after the turn.
        image: The image from the robot camera after the turn as a PNG encoded byte array.
    """
    return unity.turn_robot_camera(args)
    
def main():
    logger.debug("running web server")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    app.run(port=UNITY_CONNECT_PORT, use_reloader=False, debug=True)
    
if __name__ == "__main__":
    main()



