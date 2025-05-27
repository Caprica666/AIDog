import numpy as np
from PIL import Image
from mcp.server.fastmcp import FastMCP
from flask import Flask, request, jsonify
from yolo_connection import ObjectDetector
from unity_connection import UnityConnection
import logging

UNITY_APP_URL = "http://localhost:5000"

yolo = ObjectDetector(model_name="yoloe-11l-seg.pt")
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("RobotMCPServer")
logger.setLevel(logging.DEBUG)
mcp = FastMCP("Robot MCP Server")
unity = UnityConnection(UNITY_APP_URL, logger)

#
# Description of the function to turn the robot camera
# This function is called by the LLM when it needs to turn the robot camera.
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
            "end_angle": {
                "type": "integer",
                "description": "The ending angle beyond which the camera should not turn."
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
# Description of the function to detect an object the robot sees
# This function is called by the LLM when it needs to find the bounding box of an object.
#
detect_object_function = {
    "name": "detect_object",
    "description": "Look for a designated object visible to the robot's camera.",
    "parameters": {
        "type": "object",
        "properties": {
            "label": {
                "type": "string",
                "description": "The name of the object to look for."
            },
        },
        "required": [ "label" ]
    }
}

@mcp.tool()
def turn_robot_camera(amount_to_turn, current_angle, direction):
    """
    Turn the robot camera a specific number of degrees.
    
    Args:
        turn_angle: The number of degrees to turn the camera.
        current_angle: The current angle of the camera before this turn.
        direction: The direction to turn the camera ("clockwise" or "counterclockwise").
        
    Returns:
        at_end_angle: True if camera has been turned to the stendart angle, False otherwise.
        current_angle: The current angle of the camera after the turn.
        image: The image from the robot camera after the turn.
        error: error message if an error occurs
    """
    if amount_to_turn == None or direction == None:
        result["status"] = "Missing required arguments for turn_robot_camera function."
        logger.debug("Missing required arguments for turn_robot_camera function.")
    result = unity.turn_robot_camera( {
                                       "amount_to_turn": amount_to_turn,
                                       "current_angle": current_angle,
                                       "direction": direction,
                                       "end_angle": 360 })  
    if "error" in result:
        return result
    result["action"] = "resubmit"
    return jsonify(result)

@mcp.tool()
def detect_objects(label):
    """
    Determine if the robot can currently see a designated and return its bounding box.
    
    Args:
        label: name of the object to find
        
    Returns: dictionary with object name and bounds (if the object is found)
        label: name of object found
        bbox: bounding box of object in format [ x, y, w, h ]
        error: error message if an error occurs  
    """
    if label is None:
        result = { "status": "Missing label for detect_objects function." }
        logger.debug("Missing label for detect_objects function.")
        return jsonify(result)
    image_data = unity.image_from_unity()
    if image_data is None:
        result = { "status": "No image available from Unity." }
        logger.debug("No image available from Unity.")
        return jsonify(result)
    yolo.set_classes([ label ])
    image = Image.open(image_data)
    image_array = np.array(image)
    if image_array.shape[-1] == 3:
        image_array = image_array[..., ::-1]
    result = { "status": "Object not found" }
    response = yolo.detect_objects(image_array)
    if response and isinstance(response, (list, tuple)) and len(response) > 0:
        firstbox = response[0]
        result = firstbox
        if "label" in firstbox and "box" in firstbox:
            result["status"] = "Object found"
            result["label"] = firstbox["label"]
            result["box"] = firstbox["box"]
    return jsonify(result)

if __name__ == "__main__":
    mcp.run(transport="stdio")


