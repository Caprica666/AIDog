import httpx
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
            if response.headers.get('Content-Type') == 'image/png':
                return image_data
            elif response.headers.get('Content-Type') == 'application/octet-stream':
                # Convert the binary data to a numpy array               
                raw_pixels = io.BytesIO(image_data).getvalue()
                # Convert raw pixel data to a numpy 2D array
                image_array = np.frombuffer(raw_pixels, dtype=np.uint8).reshape((512, 512, 3))
                return image_array
        else:
            return None


    # Post the bounds for an object to Unity
    def bounds_to_unity(self, object_name, bbox):
        url = f"{self.unity_app_url}/bounds_to_unity"
        payload = {"object_name": object_name, "bounding_box": bbox}
        response = httpx.post(url, json=payload)

        if response.status_code == 200:
            return jsonify({"message": "Bounding box sent successfully"}), 200
        else:
            return jsonify({"error": "Failed to send bounding box to Unity"}), response.status_code
