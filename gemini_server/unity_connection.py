import httpx
import json
from flask import jsonify
import io
import numpy as np

class UnityConnection:
    def __init__(self, app, unity_app_url, logger):
        self.app = app
        self.logger = logger
        self.unity_app_url = unity_app_url
        self.app.add_url_rule('/bounds_to_unity', 'bounds_to_unity', self.bounds_to_unity, methods=['POST'])
        self.app.add_url_rule('/ping', 'ping', self.ping, methods=['GET'])
        self.image_size = 256
        self.current_image = self.image_from_unity()


    def ping(self):
        """A simple ping endpoint to check server status."""
        return jsonify({"message": "pong"}), 200

    
    def image_from_unity(self):
        """Fetch an image from Unity and convert it to a PNG encoded byte array."""

        url = f"{self.unity_app_url}/image_from_unity"
        response = httpx.get(url)
        self.logger.debug("image_from_unity response ", response.status_code)

        if response.status_code == 200:
            image_data = response.content  # Extract binary data from the response
            if (response.headers.get('Content-Type') == 'image/png' or
                response.headers.get('Content-Type') == 'application/octet-stream'):
                self.current_image = io.BytesIO(image_data)
                return self.current_image
        else:
            return None
        
    def turn_robot_camera(self, params):
        """Turn the camera in Unity by a specified number of degrees.

        Args:
            A dictionary containing the following parameters:
            amount_to_turn: The number of degrees to turn the camera.
            current_angle: The current angle of the camera before the turn.
            start_angle: The starting angle of the camera.
            direction: The direction to turn the camera ('left' or 'right').

        Returns:
            A JSON response indicating whether the camera is at the start angle after the turn.
            at_start_angle: True if the camera is at the start angle, False otherwise.
            current_angle: The current angle of the camera after the turn.
            error: An error message if the request fails.
        """
        url = f"{self.unity_app_url}/turn_robot_camera"
        json_params = json.dumps(params)  # Convert params to a JSON string
        json_response = { }
        try:
            response = httpx.post(url, data=json_params, headers={"Content-Type": "application/json"})
            if response.status_code == 200:
                if response.headers.get('Content-Type') == 'application/json':
                    json_response = response.json()
                elif response.headers.get('Content-Type') == 'text/plain':
                    # If the response is plain text, parse it as JSON
                    json_response = json.loads(response.text)
                else:
                    json_response["error"] = "Unexpected content type"
                    self.logger.debug("Unexpected content type")
                    return json_response
                image = self.image_from_unity()
                if image is not None:
                    self.logger.debug("Successfully turned robot and captured image")
            else:
                json_response["error"] = "Failed to turn robot or capture image"
                self.logger.debug("Failed to turn robot or capture image")
        except httpx.RequestError as e:
            self.logger.error(f"Request failed: {e}")
            json_response["error"] = str(e)
        return json_response

    # Post the bounds for an object to Unity
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
            return jsonify({"message": "Bounding box sent successfully"}), 200
        else:
            return jsonify({"error": "Failed to send bounding box to Unity"}), response.status_code
