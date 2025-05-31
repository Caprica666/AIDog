import requests
import io
import numpy as np
from PIL import Image
import base64
import copy
import json

class RobotMCPClient:
    def __init__(self, logger, aihelper, unity, mcp_url="http://localhost:5100/mcp"):
        self.logger = logger
        self.aihelper = aihelper
        self.unity = unity
        self.mcp_url = mcp_url
        self.turn_params = {"end_angle": 360, "current_angle": 0}
        self.current_angle = 0
        self.at_end_angle = True
        self.function_info = None
        aihelper.set_initial_prompt(self.initial_prompt())

    def initial_prompt(self):
        return (
            "You are controlling a robot that has a camera. You can see the world through the robot's camera. "
            "You will be asked to find objects the robot sees and return their bounding boxes. "
            "You have two tools: turn_robot_camera and detect_object. "
            "Call detect_object with the name of the object to look for. "
            "If the object is not found, call turn_robot_camera with amount_to_turn and direction. "
            "If at_end_angle is True, indicate that the object is not found and do not turn the robot camera further. "
            "Return bounding boxes as a JSON array with the following format: label, bbox."
        )

    def turn_robot_camera(self, amount_to_turn, direction):
        url = f"{self.mcp_url}/turn_robot_camera"
        payload = {
            "amount_to_turn": amount_to_turn,
            "direction": direction
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            self.current_angle = data.get("current_angle", 0)
            self.at_end_angle = data.get("at_end_angle", True)
            return data
        else:
            return {"error": f"Failed to turn camera: {response.text}"}

    def detect_object(self, label, image_data):
        url = f"{self.mcp_url}/detect_objects"
        files = {
            'label': (None, label),
            'image': ('image.png', image_data, 'image/png')
        }
        response = requests.post(url, files=files)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to detect object: {response.text}"}

    @staticmethod
    def image_bytes_from_pil(image):
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        buf.seek(0)
        return buf

    def process_command(self, command):
        """
        Use the LLM to decide which MCP tool to use, then call the MCP server for execution.
        Returns a dict with status, action, image, label, bbox, etc. for the web UI.
        """
        result = {"action": None}
        image_data = self.unity.current_image
        while True:
            # Let the LLM decide which tool to use and with what arguments
            response, function_info = self.aihelper.call_with_functions(
                command,
                [
                    {"name": "turn_robot_camera", "description": "Turn the robot camera the specific number of degrees.", "parameters": {"type": "object", "properties": {"amount_to_turn": {"type": "integer"}, "direction": {"type": "string", "enum": ["clockwise", "counterclockwise"]}}, "required": ["amount_to_turn", "direction"]}},
                    {"name": "detect_object", "description": "Look for a designated object visible to the robot's camera.", "parameters": {"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"]}}
                ],
                self.function_info
            )
            self.logger.debug("LLM response: %s", response)
            if "status" in response and "ERROR" in response["status"]:
                result["status"] = response["status"]
                return result
            if function_info:
                self.function_info = function_info
                args = copy.deepcopy(response["args"])
                if response["function_name"] == "turn_robot_camera":
                    mcp_result = self.turn_robot_camera(args["amount_to_turn"], args["direction"])
                    result.update(mcp_result)
                    result["action"] = "resubmit"
                elif response["function_name"] == "detect_object":
                    if image_data is None:
                        result["status"] = "No image data available."
                        return result
                    label = args["label"]
                    mcp_result = self.detect_object(label, image_data)
                    if isinstance(mcp_result, list) and len(mcp_result) > 0:
                        firstbox = mcp_result[0]
                        result["status"] = "Object found"
                        result["label"] = firstbox.get("label")
                        result["bbox"] = firstbox.get("bbox")
                        result["image"] = image_data
                        return result
                    else:
                        result["status"] = "Object not found"
                        result["action"] = None
                        return result
                else:
                    result["status"] = "Unknown function requested by LLM."
                    return result
            else:
                self.function_info = None
                if "text" in response:
                    if "json" in response["text"][:8]:
                        self.process_bounding_box(response["text"], result)
                        return result
            if result["action"] == "resubmit":
                # After turning, get a new image from Unity and try again
                image_data = self.unity.current_image
                continue
            return result

    def process_bounding_box(self, text, result):
        text = text[8:]
        text = text[:text.rfind(']') + 1]
        try:
            response_dict = json.loads(text)
            self.logger.debug("Python dict: %s", response_dict)
            if response_dict:
                first_entry = response_dict[0]
                result['label'] = first_entry['label']
                result['bbox'] = first_entry['bbox']
        except json.JSONDecodeError as e:
            result["status"] = "Failed to parse LLM response."
            result["action"] = None
            self.logger.debug("Failed to parse LLM response: %s", e.msg)
