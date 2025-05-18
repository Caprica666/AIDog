from ultralytics import YOLO
import numpy as np

class ObjectDetector():
    def __init__(self, model_name="yolo11n.pt"):
        self.model_name = model_name
        self.model = YOLO(self.model_name)
        
    def detect_objects(self, image):
        results = self.model.predict(source = image)
        box_results = [ ]
        for result in results:
            boxes = result.boxes  # Boxes object for bounding box outputs
            # Sort indices of boxes.conf in descending order
            if boxes.conf is not None and len(boxes.conf) > 0:
                conf_array = np.array(boxes.conf)
                sorted_indices = conf_array.argsort()[::-1]
            else:
                sorted_indices = range(len(boxes))
            for i in sorted_indices:
                id = int(boxes.cls[i])  # Ensure id is an integer
                name = result.names[id]
                coords = boxes.xywh[i]
                coords = [int(c) for c in coords]  # Convert all coords to int
                box_results.append({ "label" : name, "box": coords })
        return box_results


