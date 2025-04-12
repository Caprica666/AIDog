import mcp
import numpy as np
from PIL import Image
import torch
from torchvision import transforms
from torchvision.models.detection import fasterrcnn_resnet50_fpn
import httpx

# Initialize the object detection model
model = fasterrcnn_resnet50_fpn(pretrained=True)
model.eval()

# Define a transformation for the input image
transform = transforms.Compose([
    transforms.ToTensor()
])

class ObjectDetectionAgent(mcp.Agent):
    def __init__(self, server_url):
        super().__init__()
        self.server_url = server_url

    def process_image(self, raw_pixels, object_name):
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
                if self.get_coco_label(label) == object_name:
                    return box.tolist()

        return None

    def get_coco_label(self, label):
        # Map COCO dataset labels to object names
        coco_labels = {1: 'ball', 2: 'box'}  # Add all COCO labels here
        return coco_labels.get(label.item(), 'unknown')

    def on_image_received(self, raw_pixels, object_name):
        # Process the image and find the bounding box
        bounding_box = self.process_image(raw_pixels, object_name)

        # Send the bounding box back to the server
        response = httpx.post(f"{self.server_url}/bounding_box", json={
            "object_name": object_name,
            "bounding_box": bounding_box
        })

        if response.status_code == 200:
            print("Bounding box sent successfully.")
        else:
            print(f"Failed to send bounding box: {response.status_code}")

# Initialize the agent
if __name__ == "__main__":
    server_url = "http://localhost:8000"  # Replace with the actual server URL
    agent = ObjectDetectionAgent(server_url)
    agent.run()