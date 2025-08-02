
import copy
import json
from robot_functions import RobotFunctions

initial_prompt = """
    You are controlling a robot that has a camera. You can see the world through the robot's camera.
    You will be asked to find objects the robot sees and return their bounding boxes.
    You will be provided with two functions, one to detect objects seen by the robot and another to turn the robot's camera.
    Call the detect_object function with the name of the object the user is looking for (call this argument "label").
    If the object is found, it will return the name of the object and its bounding box:
        label: The name of the object found
        box: The bounding box
        message: 'Object found' or 'Object not found'
        success: True if the object was found, False otherwise
    Return this as your response.
    If the object is not found, call the turn_robot_camera function with the following arguments:
    - turn_angle: The number of degrees to turn the camera (use 30 degrees).
    - direction: The direction to turn the camera (use 'counterclockwise').
    - current_angle: The current amount the camera has turned. Start at 0 for the first iteration
      and pass the result of the previous turn_robot_camera to the next iteration.
    It will provide a new current angle for the robot and set at_end_angle to True if turning the robot brings it to the ending angle.
    You must remember the current angle and pass it as an argument to the next turn_robot_camera call.
    If at_end is True, indicate that the object is not found and do not turn the robot camera further.
    Return bounding boxes as a JSON array with the following format:
    - label: The name of the object. "
    - bbox: The bounding box coordinates in the format [ymin, xmin, ymax, xmax].
    - success: True if the object was found, False otherwise
    """

class RobotController():
    def __init__(self, logger, aihelper, mock_unity_dir = None, mock_yolo = False):
        self.logger = logger
        self.aihelper = aihelper
        self.robot = RobotFunctions(mock_unity_dir, mock_yolo)      
        self.function_info = None
        aihelper.set_initial_prompt(initial_prompt)
        aihelper.set_tools(self.robot.get_function_list())
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
            message: The status of the command or an error message
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
            if "message" in response and "ERROR" in response["message"]:
                result["message"] = response["message"]
                return result       
            if function_info:
                self.function_info = function_info
                args = copy.deepcopy(response["args"])
                result = self.process_function_call(response["function_name"], args)
                if "error" in result["message"]:
                    return result
                if "image" in result:
                    image = result.pop("image")
                    function_info["function_output"] = copy.deepcopy(result)
                    result["image"] = image
                else:
                    function_info["function_output"] = result
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
            message: The status of the command or an error message
            success: True if the function call was successful, False otherwise
            action: The action to take (e.g., "resubmit" if the command needs to be reprocessed)
            image: The image data as a base64 encoded string
            object_name: The name of the object found in the image
            bbox: The bounding box coordinates of the object in the image   
        """
        result = { "action": None }
        print("Function to call: " + function_name)
        if function_name == "turn_robot_camera":
            function_result = self.robot.turn_robot_camera(args)
            result.update(function_result)     
            if "error" in result["message"]:
                return result
            result["action"] = "resubmit"
        elif function_name == "detect_object":
            function_result = self.robot.detect_object(args)
            result.update(function_result)
        else:
            result["message"] = "error: no function called for " + function_name
        return result
        
    def process_bounding_box(self, text, result):
        text = text[8:]
        if text[0] == '[':
            text = text[:text.rfind(']') + 1]
        elif text[0] == '{':
            text = text[:text.rfind('}') + 1]
        try:
            response_dict = json.loads(text)
            if response_dict:
                if isinstance(response_dict, (list, tuple)) and len(response_dict) > 0:
                    response_dict = response_dict[0]
                result['label'] = response_dict['label']
                if "bbox" in response_dict:
                    result["bbox"] = response_dict['bbox']
                    result["success"] = True
                elif "box" in response_dict:
                    result["bbox"] = response_dict["box"]
                    result["success"] = True
        except json.JSONDecodeError as e:
            result["message"] = "Failed to parse LLM response."
            result["success"] = False
            result["action"] = None
            self.logger.debug("Failed to parse LLM response " + str(e.msg))
    




