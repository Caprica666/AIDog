import numpy as np
from PIL import Image
import torch
from torchvision import transforms
from torchvision.models.detection import fasterrcnn_resnet50_fpn
import mcp
from unity_connection import bounds_to_unity, image_from_unity, start_server
from mcp.server.fastmcp import FastMCP
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("MCPServer")

AGENT_SERVER_URL = "http://localhost:8000"

# Initialize the object detection model
model = fasterrcnn_resnet50_fpn(pretrained=True)
model.eval()

# Define a transformation for the input image
transform = transforms.Compose([
    transforms.ToTensor()
])

mcp = FastMCP("Unity AIDog Server", host=AGENT_SERVER_URL, port=8000)

class ObjectDetector:
    def __init__(self, object_name):
        self.object_name = object_name
        return

    def process_image(self, image):
        logger.info("Calling process_image")

        # Transform the image for the model
        input_tensor = transform(image).unsqueeze(0)
        logger.info("image was transformed")
        # Perform object detection
        with torch.no_grad():
            predictions = model(input_tensor)[0]
        logger.info("predictions were made")
        # Find the bounding box for the specified object
        for label, box, score in zip(predictions['labels'], predictions['boxes'], predictions['scores']):
            if score > 0.5:  # Confidence threshold
                # Convert label to object name (using COCO dataset labels)
                if self.get_coco_label(label) == self.object_name:
                    logger.info("found the object in the image")
                    return box.tolist()
        logger.info("object not found in image")
        return None

    def get_coco_label(self, label):
        # Map COCO dataset labels to object names
        coco_labels = {1: 'ball', 2: 'box'}  # Add all COCO labels here
        return coco_labels.get(label.item(), 'unknown')

    def on_image_received(self, raw_pixels, width, height):     
        # Convert raw pixel data to a numpy 2D array
        image_array = np.frombuffer(raw_pixels, dtype=np.uint8).reshape((height, width, 3))
        # Process the image and find the bounding box   
        bounding_box = self.process_image(image_array)
        if response == None:
            print(f"Failed to find object: {self.object_name}")
            return None
        else:
            print(f"Bounding box found for object:  {self.object_name}")

            response = {
                "object_name": self.object_name,
                "bounding_box": bounding_box
            }
            return response           
 
@mcp.tool(description="Finds an object in a 3D scene.")
async def find_object(object_name: str) -> str:
    if not object_name:
        return {"error": "Object name is required"}
    finder = ObjectDetector(object_name)
    while True:
        image = image_from_unity(object_name)
        if image == None:
            logger.info("Failed to get image from Unity")
            return {"error": "Failed to get image from Unity"}
        result = finder.on_image_received(image, 512, 512)
        if result != None:
            logger.info("image gotten from Unity")
            bounds_to_unity(result)
            break;
    return {"message": "Object found"}
    
# Initialize the agent
if __name__ == "__main__":
    logger.info("Starting Unity connection server in a separate thread...")
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    logger.info("Starting MCP server...")
    mcp.run()



