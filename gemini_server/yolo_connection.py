from ultralytics import YOLO
import numpy as np

class ObjectDetector():
    def __init__(self, logger, model_name = "yoloe-11l-seg.pt", labels = None):
        self.model_name = model_name
        self.model = YOLO(self.model_name)
        self.labels = None
        self.logger = logger
        if labels:
            self.set_classes(labels)
        self.logger.debug("ObjectDetector with model " + model_name)    
        
    def set_classes(self, labels):
        if self.labels != labels:
            self.model.set_classes(labels, self.model.get_text_pe(labels))
            self.labels = labels
        
    def detect_objects(self, image):
        results = self.model.predict(source = image)
        box_results = [ ]
        
        for result in results:
            #result.show()
            boxes = result.boxes  # Boxes object for bounding box outputs
            # Sort indices of boxes.conf in descending order
            if boxes.conf is not None and len(boxes.conf) > 0:
                conf_array = np.asarray(boxes.conf)
                sorted_indices = conf_array.argsort()[::-1]
            else:
                sorted_indices = range(len(boxes))
            for i in sorted_indices:
                id = int(boxes.cls[i])  # Ensure id is an integer
                name = result.names[id]
                coords = boxes.xywh[i]
                coords = [int(c) for c in coords]  # Convert all coords to int
                bbox = [ coords[0] - coords[2] / 2, coords[1] - coords[3] / 3, coords[2], coords[3]]
                box_results.append({ "label" : name, "box": bbox })
        return box_results


