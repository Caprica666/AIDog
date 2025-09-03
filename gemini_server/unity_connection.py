import httpx
from robot_connection import RobotConnection

class UnityConnection(RobotConnection):
    def __init__(self, robot_url, logger):
        super().__init__(robot_url, logger)
        self.logger.debug("UnityConnection at URL " + robot_url)
        self.current_image = self.image_from_robot()

    def bounds_to_unity(self, object_name, bbox):
        """
        Send the bounding box of an object to Unity.
        Args:
            object_name: The name of the object.
            bbox: The bounding box coordinates in the format [x, y, width, height]. 
        """
        url = f"{self.robot_post_url}/aidog_set_bounds"
        payload = {"object_name": object_name, "bounding_box": bbox}
        response = httpx.post(url, json=payload)

        if response.status_code == 200:
            return {"status": "Bounding box sent successfully"}
        else:
            return {"status": "Failed to send bounding box to Unity"}