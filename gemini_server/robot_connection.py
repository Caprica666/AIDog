import httpx
import json
from flask import jsonify
import os
import io

class RobotConnection:
    def __init__(self, robot_url, logger):
        self.logger = logger
        self.robot_get_url = robot_url
        self.robot_post_url = robot_url
        self.image_size = 256
        self.current_image = None

    def ping(self):
        """A simple ping endpoint to check server status."""
        return jsonify({"message": "pong"}), 200
  
    def image_from_robot(self):
        """Fetch an image from Unity and convert it to a PNG encoded byte array."""
        url = f"{self.robot_get_url}/aidog_get_camera_image"
        response = httpx.get(url)
        self.logger.debug(f"aidog_get_camera_image response {response.status_code}")

        if response.status_code == 200:
            image_data = response.content  # Extract binary data from the response
            if (response.headers.get('Content-Type') == 'image/png' or
                response.headers.get('Content-Type') == 'application/octet-stream'):
                self.current_image = io.BytesIO(image_data)
                return self.current_image
        else:
            return None


    def set_robot_yangle(self, params):
        """Set the robot camera's angle about the Y axis to the specified number of degrees.
         Args:
            A dictionary containing the following parameter:
            current_angle: The current Y angle of the camera in degrees.
            angular_velocity: The angular velocity of the turn. (degrees per second)
        """
        if "current_angle" not in params or "angular_velocity" not in params:
            return { "message": "error: aidog_rotatezaxis_absolute is missing required parameter", "success": False }

        url = f"{self.robot_get_url}/aidog_rotatezaxis_absolute"
        json_params = json.dumps(params)  # Convert params to a JSON string
        response_dict = { "success": False }
        try:
            response = httpx.post(url, data=json_params, headers={"Content-Type": "application/json"}, timeout=20)
            if response.status_code == 200:
                if response.headers.get('Content-Type') == 'application/json':
                    response_dict = response.json()
                elif response.headers.get('Content-Type') == 'text/plain':
                    # If the response is plain text, parse it as JSON
                    response_dict = json.loads(response.text)
                else:
                    response_dict["message"] = "error: aidog_rotatezaxis_absolute Unexpected content type"
                    self.logger.debug("Unexpected content type")
                    return response_dict
            else:
                if response.headers.get('Content-Type') == 'application/json':
                    response_dict = response.json()
                    if "message" not in response_dict:
                        response_dict["message"] = "error: set_robot_yangle Failed to set angle"
                else:
                    response_dict["message"] = "error: aidog_rotatezaxis_absolute Failed to set angle"
                self.logger.error(response_dict["message"])               
        except httpx.RequestError as e:
            self.logger.error(f"Request failed: {e}")
            response_dict["message"] = "error: aidog_rotatezaxis_absolute " + str(e)
        return response_dict
                
    def turn_robot_camera(self, params):
        """Turn the camera in Unity by a specified number of degrees.

        Args:
            A dictionary containing the following parameters:
            turn_angle: The number of degrees to turn the camera.
            angular_velocity: The angular velocity of the turn. (degrees per second)
            current_angle: The current angle of the camera before the turn.
            end_angle: The starting angle of the camera.

        Returns:
            A JSON response indicating whether the camera is at the start angle after the turn.
            at_end: True if the camera is at the start angle, False otherwise.
            last_angle: The current angle of the camera after the turn.
            success: True if the turn was successful, False otherwise.
            message: An error message if the request fails.
        """
        if "turn_angle" not in params or "current_angle" not in params or "end_angle" not in params:
            return { "message": "error: aidog_rotatezaxis_relative is missing required parameters", "success": False }
        url = f"{self.robot_get_url}/aidog_rotatezaxis_relative"
        json_params = json.dumps(params)  # Convert params to a JSON string
        response_dict = { }
        try:
            response = httpx.post(url, data=json_params, headers={"Content-Type": "application/json"})
            if response.status_code == 200:
                if response.headers.get('Content-Type') == 'application/json':
                    self.logger.debug("turn_robot_camera response: " + response.text)
                    response_dict = response.json()
                elif response.headers.get('Content-Type') == 'text/plain':
                    # If the response is plain text, parse it as JSON
                    response_dict = json.loads(response.text)
                else:
                    response_dict["message"] = "error: turn_robot_camera Unexpected content type"
                    response_dict["success"] = False
                    self.logger.debug("Unexpected content type")
                    return response_dict
            else:
                if response.headers.get('Content-Type') == 'application/json':
                    response_dict = response.json()
                    if "message" not in response_dict:
                        response_dict["message"] = "error: failed to turn robot"
                        response_dict["success"] = False
                else:
                    response_dict["message"] = "error: failed to turn robot"
                    response_dict["success"] = False
                self.logger.error(response_dict["status"])               
        except httpx.RequestError as e:
            self.logger.error(f"Request failed: {e}")
            response_dict["message"] = "error: " + str(e)
            response_dict["success"] = False
        return response_dict

