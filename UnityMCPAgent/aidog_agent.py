import numpy as np
from PIL import Image
import torch
from torchvision import transforms
from torchvision.models.detection import fasterrcnn_resnet50_fpn
import mcp
from UnityMCPAgent.unity_connection import bounds_to_unity, image_from_unity
from mcp.server.fastmcp import FastMCP

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

    def process_image(self, raw_pixels):
        # Convert raw pixels to a PIL image
        image = Image.fromarray(np.array(raw_pixels, dtype=np.uint8))

        # Transform the image for the model
        input_tensor = transform(image).unsqueeze(0)

        # Perform object detection
        with torch.no_grad():
            predictions = model(input_tensor)[0]

        # Find the bounding box for the specified object
        for label, box, score in zip(predictions['labels'], predictions['boxes'], predictions['scores']):
            if score > 0.5:  # Confidence threshold
                # Convert label to object name (using COCO dataset labels)
                if self.get_coco_label(label) == self.object_name:
                    return box.tolist()

        return None

    def get_coco_label(self, label):
        # Map COCO dataset labels to object names
        coco_labels = {1: 'ball', 2: 'box'}  # Add all COCO labels here
        return coco_labels.get(label.item(), 'unknown')

    def on_image_received(self, raw_pixels):
        # Process the image and find the bounding box
        bounding_box = self.process_image(raw_pixels)
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
 
@mcp.tool()
async def find_object(object_name: str) -> str:
    if not object_name:
        return {"error": "Object name is required"}
    finder = ObjectDetector(object_name)
    while True:
        image = image_from_unity(object_name)
        if image is None:
            return {"error": "Failed to get image from Unity"}
        result = finder.on_image_received(image)
        if result != None:
            bounds_to_unity(result)
            break;
    return {"message": "Object found"}
    
    
# Initialize the agent
if __name__ == "__main__":
    mcp.run()
    
    
    