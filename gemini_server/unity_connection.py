import httpx
import json
from flask import jsonify
import io
import numpy as np

class UnityConnection:
    def __init__(self, unity_app_url, logger):
        #self.app = app
        self.logger = logger
        self.unity_app_url = unity_app_url
        #self.app.add_url_rule('/bounds_to_unity', 'bounds_to_unity', self.bounds_to_unity, methods=['POST'])
        #self.app.add_url_rule('/ping', 'ping', self.ping, methods=['GET'])
        self.image_size = 256
        self.current_image = self.image_from_unity()


    def ping(self):
        """A simple ping endpoint to check server status."""
        return jsonify({"message": "pong"}), 200

    
    def image_from_unity(self):
        """Fetch an image from Unity and convert it to a PNG encoded byte array."""

        url = f"{self.unity_app_url}/image_from_unity"
        response = httpx.get(url)
        self.logger.debug(f"image_from_unity response {response.status_code}")

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
        """
        if "current_angle" not in params:
            return { "status": "error: set_robot_yangle is missing required parameter" }

        url = f"{self.unity_app_url}/set_robot_yangle"
        json_params = json.dumps(params)  # Convert params to a JSON string
        response_dict = { }
        try:
            response = httpx.post(url, data=json_params, headers={"Content-Type": "application/json"})
            if response.status_code == 200:
                if response.headers.get('Content-Type') == 'application/json':
                    response_dict = response.json()
                elif response.headers.get('Content-Type') == 'text/plain':
                    # If the response is plain text, parse it as JSON
                    response_dict = json.loads(response.text)
                else:
                    response_dict["status"] = "error: set_robot_yangle Unexpected content type"
                    self.logger.debug("Unexpected content type")
                    return response_dict
            else:
                if response.headers.get('Content-Type') == 'application/json':
                    response_dict = response.json()
                    if "status" not in response_dict:
                        response_dict["status"] = "error: set_robot_yangle Failed to set angle"
                else:
                    response_dict["status"] = "error: set_robot_yangle Failed to set angle"
                self.logger.error(response_dict["status"])               
        except httpx.RequestError as e:
            self.logger.error(f"Request failed: {e}")
            response_dict["status"] = "error: set_robot_yangle " + str(e)
        return response_dict
        
    def turn_robot_camera(self, params):
        """Turn the camera in Unity by a specified number of degrees.

        Args:
            A dictionary containing the following parameters:
            amount_to_turn: The number of degrees to turn the camera.
            current_angle: The current angle of the camera before the turn.
            end_angle: The starting angle of the camera.
            direction: The direction to turn the camera ('left' or 'right').

        Returns:
            A dictionary with the following entries:
            at_end_angle: True if the camera is past the end angle, False otherwise.
            current_angle: The current angle of the camera after the turn.
            status: status indicating success or an error message if the request fails.
        """
        if "amount_to_turn" not in params or "current_angle" not in params or "direction" not in params or "end_angle" not in params:
            return { "status": "error: turn_robot_camera is missing required parameters" }
        if params["direction"] != "clockwise" and params["direction"] != "counterclockwise":
            return { "status": "error: turn_robot_camera direction not valid - " + params["direction"] }
        url = f"{self.unity_app_url}/turn_robot_camera"
        json_params = json.dumps(params)  # Convert params to a JSON string
        response_dict = { }
        try:
            response = httpx.post(url, data=json_params, headers={"Content-Type": "application/json"})
            if response.status_code == 200:
                if response.headers.get('Content-Type') == 'application/json':
                    response_dict = response.json()
                elif response.headers.get('Content-Type') == 'text/plain':
                    # If the response is plain text, parse it as JSON
                    response_dict = json.loads(response.text)
                else:
                    response_dict["status"] = "error: turn_robot_camera Unexpected content type"
                    self.logger.debug("Unexpected content type")
                    return response_dict
            else:
                if response.headers.get('Content-Type') == 'application/json':
                    response_dict = response.json()
                    if "status" not in response_dict:
                        response_dict["status"] = "error: turn_robot_camera Failed to turn robot"
                else:
                    response_dict["status"] = "error: turn_robot_camera Failed to turn robot"
                self.logger.error(response_dict["status"])               
        except httpx.RequestError as e:
            self.logger.error(f"Request failed: {e}")
            response_dict["status"] = "error: turn_robot_camera " + str(e)
        return response_dict

    def bounds_to_unity(self, object_name, bbox):
        """
        Send the bounding box of an object to Unity.
        Args:
            object_name: The name of the object.
            bbox: The bounding box coordinates in the format [x, y, width, height]. 
        """
        url = f"{self.unity_app_url}/bounds_to_unity"
        payload = {"object_name": object_name, "bounding_box": bbox}
        response = httpx.post(url, json=payload)

        if response.status_code == 200:
            return {"status": "Bounding box sent successfully"}
        else:
            return {"status": "Failed to send bounding box to Unity"}