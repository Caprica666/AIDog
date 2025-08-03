
import json
from flask import jsonify
import os
import io

class MockUnityConnection:
    def __init__(self, unity_app_url, logger, mock_unity_dir):
        #self.app = app
        self.logger = logger
        self.unity_app_url = unity_app_url
        self.image_size = 256
        self.frame_count = 0
        self.mock_dir = mock_unity_dir
        self.current_image = self.image_from_unity()

    def ping(self):
        """A simple ping endpoint to check server status."""
        return jsonify({"message": "pong"}), 200
  
    def image_from_unity(self):
        """Fetch an image from Unity and convert it to a PNG encoded byte array."""
        self.frame_count += 1
        if self.frame_count > 4:
            self.frame_count = 1
        filename = "capturedimage" + str(self.frame_count) + ".png"
        image_file_name = os.path.join(self.mock_dir, filename)
        with open(image_file_name, 'rb') as image_png_file:
            image_png_data = image_png_file.read()
        self.current_image = io.BytesIO(image_png_data)
        return self.current_image


    def set_robot_yangle(self, params):
        """Set the robot camera's angle about the Y axis to the specified number of degrees.
         Args:
            A dictionary containing the following parameter:
            current_angle: The current Y angle of the camera in degrees.
        """
        if "current_angle" not in params:
            return { "message": "error: set_robot_yangle is missing required parameter", "success": False }
        self.frame_count = 0
        return { "message": "robot angle successfully set", "success": True}
                
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
            return { "message" : "error: aidog_rotatezaxis_absolute is missing required parameters", "success": False }
        new_angle = params["current_angle"]
        new_angle += params["turn_angle"]
        response = { "last_angle" : new_angle, "at_end": False, "success": True }
        response["message"] = "robot successfully turned"
        if params["end_angle"] > 0 and new_angle >= params["end_angle"]:
            response["at_end"] = True
            response["last_angle"] = params["end_angle"]
            response["message"] = "robot at end angle"
        elif params["end_angle"] <= 0 and new_angle <= params["end_angle"]:
            response["at_end"] = True
            response["last_angle"] = params["end_angle"]
            response["message"] = "robot at end angle"
        return response

    def bounds_to_unity(self, object_name, bbox):
        """
        Send the bounding box of an object to Unity.
        Args:
            object_name: The name of the object.
            bbox: The bounding box coordinates in the format [x, y, width, height]. 
        """
        return {"message": "Bounding box sent successfully"}

