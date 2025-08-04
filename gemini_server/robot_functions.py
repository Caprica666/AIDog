import numpy as np
import base64
from PIL import Image

from yolo_connection import ObjectDetector
from mock_yolo_connection import MockObjectDetector
from unity_connection import UnityConnection
from mock_unity_connection import MockUnityConnection
import logging

logging.basicConfig(level = logging.DEBUG)

UNITY_APP_URL = "http://localhost:5000"

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
            "turn_angle": {
                "type": "float",
                "description": "The number of degrees to turn the camera."
            },
            "end_angle": {
                "type": "float",
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
        "required": [ "turn_angle", "direction"]
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

YOLO_MODEL = "yoloe-11l-seg.pt"
class RobotFunctions():
    def __init__(self, mock_unity_dir = None, mock_yolo = False):
        self.function_list = [ turn_robot_camera_function, detect_object_function ]
        self.logger = logging.getLogger("RobotFunctions")
        self.logger.setLevel(logging.DEBUG)
        if mock_unity_dir:
            self.unity = MockUnityConnection(UNITY_APP_URL, self.logger, mock_unity_dir)
            if mock_yolo:
                self.yolo = MockObjectDetector(model_name = YOLO_MODEL)
            else:
                self.yolo = ObjectDetector(model_name = YOLO_MODEL)
        else:
            self.unity = UnityConnection(UNITY_APP_URL, self.logger)
            self.yolo = ObjectDetector(model_name = YOLO_MODEL)
      
    def get_function_list(self):
        return self.function_list
           
    def turn_robot_camera(self, args):
        """
        Turn the robot camera a specific number of degrees.
        
        Args: dictionary with the following:
            turn_angle: The number of degrees to turn the camera.
            current_angle: The current angle of the camera before this turn.
            angular_velocity: The speed of the turn in degrees per second. (default is 10)
            direction: The direction to turn the camera ("clockwise" or "counterclockwise").
            
        Returns:
            at_end: True if camera has been turned to the stendart angle, False otherwise.
            last_angle: The current angle of the camera after the turn.
            message: error message if an error occurs
            success: True if the turn was successful, False otherwise
        """
        if "turn_angle" not in args or "direction" not in args or "current_angle" not in args:      
            self.logger.debug("Missing required arguments for turn_robot_camera function.")
            return { "message": "error: Missing required arguments for turn_robot_camera function.", "success": False }
        if "angular_velocity" not in args:
            args["angular_velocity"] = 10
        if args["angular_velocity"] < 0:
            self.logger.debug("Angular velocity must be a positive number.")
            return { "message": "error: Angular velocity must be a positive number.", "success": False }
        if "end_angle" not in args: 
            args["end_angle"] = 360
        if args["direction"] == "counterclockwise":
            args["turn_angle"] = -args["turn_angle"]
        result = self.unity.turn_robot_camera(args)  
        if "error" in result["message"]:
            return result
        if "last_angle" in result:
            result["current_angle"] = result["last_angle"]
        result["action"] = "resubmit"
        image_data = self.unity.image_from_unity()
        result["image"] = self.process_image(image_data)
        return result

    def detect_object(self, args):
        """
        Determine if the robot can currently see a designated and return its bounding box.
        
        Args: dictionary with the following:
            label: name of the object to find
            
        Returns: dictionary with object name and bounds (if the object is found)
            label: name of object found
            bbox: bounding box of object in format [ x, y, w, h ]
            error: error message if an error occurs
            image: PNG image from the robot's camera as a base64 string 
        """
        if "label" not in args:
            self.logger.debug("Missing label for detect_objects function.")
            return { "message": "error: Missing label for detect_objects function.", "success": False }
        image_png_data = self.unity.current_image
        if image_png_data is None:
            self.logger.debug("No image available from Unity.")
            return { "message": "error: No image available from Unity.", "success": False }
        self.yolo.set_classes([ args["label"] ])
        image = Image.open(image_png_data)  
        image_array = np.array(image)
        if image_array.shape[-1] == 3:
            image_array = image_array[..., ::-1]
        result = { "success": False, "message": "Object not found" }
        response = self.yolo.detect_objects(image_array)
        if response and isinstance(response, (list, tuple)) and len(response) > 0:
            firstbox = response[0]
            result = firstbox
            if "label" in firstbox and "box" in firstbox:
                result["message"] = "Object found"
                result["success"] = True
                result["label"] = firstbox["label"]
                result["box"] = firstbox["box"]
        result["image"] = self.process_image(image_png_data)
        return result
    
    def process_image(self, image_png_data):
        if image_png_data != None:
            image_bytes = image_png_data.getvalue() 
            imageb64 = base64.b64encode(image_bytes).decode('utf-8')
            return imageb64
        return None



