
import numpy as np
from PIL import Image
import copy
import json
from yolo_connection import ObjectDetector
from unity_connection import UnityConnection

UNITY_APP_URL = "http://localhost:5000"
UNITY_CONNECT_PORT = 5001

initial_prompt = """
    You are controlling a robot that has a camera. You can see the world through the robot's camera.
    You will be asked to find objects the robot sees and return their bounding boxes.
    You will be provided with two functions, one to detect objects seen by the robot and another to turn the robot's camera.
    Call the detect_object function with the name of the object the user is looking for (call this argument "label").
    If the object is found, it will return the name of the object and its bounding box:
        label: The name of the object found
        bbox: The bounding box
        status: 'Object found' or 'Object not found'
    Return this as your response.
    If the object is not found, call the turn_robot_camera function with the following arguments:
    - amount_to_turn: The number of degrees to turn the camera (use 30 degrees).
    - direction: The direction to turn the camera (use 'counterclockwise').
    It will provide a new current angle for the robot and set at_end_angle to True if turning the robot brings it to the ending angle.
    If at_end_angle is True, indicate that the object is not found and do not turn the robot camera further.
    Return bounding boxes as a JSON array with the following format:
    - label: The name of the object. "
    - bbox: The bounding box coordinates in the format [ymin, xmin, ymax, xmax].
    """
            
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
        "required": [ "amount_to_turn", "direction", "current_angle" ]
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

class RobotController():
    def __init__(self, logger, aihelper):
        self.logger = logger
        self.aihelper = aihelper       
        self.unity = UnityConnection(UNITY_APP_URL, logger)
        self.yolo = ObjectDetector(model_name = "yoloe-11l-seg.pt")
        self.turn_params = { "end_angle" : 360, "current_angle" : 0 }
        self.function_info = None
        aihelper.set_initial_prompt(initial_prompt)
        aihelper.set_tools([turn_robot_camera_function, detect_object_function])
        aihelper.start_client()
        
    def process_command(self, command):
        """
        Process the command given by the user to the robot.
        Currently this is a request to find objects in the image.
        The current image from the robot's camera is provided along with a function to turn the camera.
        If the command successfully finds an object, its name and bounding box are returned.
        If the object is not found andthe LLM requests to turn the camera,
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
        # Provide the LLM with functions to turn the robot camera and detect objects
        result = { "action": None }
        while True:
            response, function_info = self.aihelper.call_llm(command, self.function_info)
            self.logger.debug("LLM response: ", response)
            if "status" in response and "ERROR" in response["status"]:
                result["status"] = response["status"]
                return result       
            if function_info:
                self.function_info = function_info
                args = copy.deepcopy(response["args"])
                result, image = self.process_function_call(response["function_name"], args)
                function_info["function_output"] = copy.deepcopy(result)
                if image:
                    result["image"] = image
            else:
                self.function_info = None
                if "text" in response:
                    if "json" in response["text"][:8]:
                        self.process_bounding_box(response["text"], result)
                        return result
            if result["action"] == "resubmit":
                return result

    def process_function_call(self, function_name, args):
        """
        Process the function call indicated by the LLM.
        If the function finds an object, its name and bounding box are returned.
        If the object is not found and the LLM requests to turn the camera,
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
        result = { "action": None }
        print("Function to call: " + function_name)
        if function_name == "turn_robot_camera":
            # capture the image from the robot camera
            # and pass the image data to the LLM as a PNG encoded byte array
            if "amount_to_turn" not in args or "direction" not in args:
                result["status"] = "Missing required arguments for turn_robot_camera function."
                self.logger.debug("Missing required arguments for turn_robot_camera function.")
                return result
            self.turn_params["amount_to_turn"] = args["amount_to_turn"]
            self.turn_params["direction"] = args["direction"]
            self.function_result = self.turn_robot_camera(self.turn_params)     
            if "error" in self.function_result:
                result["status"] = self.func_result["error"]
                return result
            self.turn_params["current_angle"] = self.function_result["current_angle"]
            result = { "action": "resubmit" }
        elif function_name == "detect_object":
            # look for the object designated by the user
            args["image_data"] = self.unity.current_image
            self.function_result = self.detect_object(args)
            if self.function_result and isinstance(self.function_result, (list, tuple)) and len(self.function_result) > 0:
                firstbox = self.function_result[0]
                self.function_result = firstbox
                if "label" in firstbox and "box" in firstbox:
                    result["status"] = "Object found"
                    result["label"] = firstbox["label"]
                    result["box"] = firstbox["box"]
                    self.function_result["status"] = "Object found"                  
            else:
                result["status"] = "Object not found"
                self.function_result = { "status": "Object not found" }
        else:
            self.function_result = None
            self.function_name = None
        return result, self.unity.current_image
        
    def process_bounding_box(self, text, result):
        text = text[8:]
        if text[0] == '[':
            text = text[:text.rfind(']') + 1]
        try:
            response_dict = json.loads(text)
            self.logger.debug("Python dict: ", response_dict)
            if response_dict:
                first_entry = response_dict[0]
                result['label'] = first_entry['label']
                result['bbox'] = first_entry['bbox']
        except json.JSONDecodeError as e:
            result["status"] = "Failed to parse LLM response."
            result["action"] = None
            self.logger.debug("Failed to parse LLM response", e.msg)
               
    def turn_robot_camera(self, args):
        """
        Turn the robot camera a specific number of degrees.
        
        Args: dictionary with the following arguments:
            turn_angle: The number of degrees to turn the camera.
            end_angle: The ending angle beyond which the camera should not turn.
            current_angle" The current angle of the camera before this turn.
            direction: The direction to turn the camera ("clockwise" or "counterclockwise").
            
        Returns:
            at_end_angle: True if camera has been turned to the end angle, False otherwise.
            current_angle: The current angle of the camera after the turn.
            image: The image from the robot camera after the turn.
            error: error message if an error occurs
        """
        return self.unity.turn_robot_camera(args)

    def detect_object(self, args):
        """
        Determine if the robot can currently see a designated and return its bounding box.
        
        Args:
            label: name of the object to find
            image_data: bytes of the image to look in
            
        Returns: dictionary with object name and bounds (if the object is found)
            label: name of object found
            bbox: bounding box of object in format [ x, y, w, h ]
            error: error message if an error occurs  
        """
        if "label" in args and "image_data" in args:
            self.yolo.set_classes([ args["label"] ])
            image_data = args["image_data"]
            image = Image.open(image_data)
            image_array = np.array(image)
            if image_array.shape[-1] == 3:
                image_array = image_array[..., ::-1]
            response = self.yolo.detect_objects(image_array)
        else:
            response = { "error" : "Missing arguments for detect_object"}
        return response
    




