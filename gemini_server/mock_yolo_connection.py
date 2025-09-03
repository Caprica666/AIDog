

class MockObjectDetector():
    def __init__(self, logger, model_name = "yolo11n.pt", labels = None):
        self.labels = labels
        self.frame_count = 0
        self.logger = logger
        self.mock_results = [
            {},     # capturedimage1.png
            [ {'label': 'ball', 'box': [-0.5, 162.0, 43, 36] } ], # "find the ball" capturedimage2.png
            {},     # capturedimage2.png
            [ {'label': 'box', 'box': [46.5, 155.66666666666666, 55, 55]} ] ] # "find the box" capturedimage4.png
        self.logger.debug("MockObjectDetector with model " + model_name)
      
    def set_classes(self, labels):
        if self.labels != labels:
            self.labels = labels
        
    def detect_objects(self, image):       
        if self.frame_count > 3:
            self.frame_count = 0
        self.logger.debug("MockObjectDetector frame #" + str(self.frame_count))
        results = self.mock_results[self.frame_count]
        self.frame_count += 1
        if isinstance(results, (list, tuple)) and len(results) > 0:
            temp = results[0]
            if self.labels and "label" in temp:
                label = self.labels[0]
                if temp["label"] == label:
                    return results          
        return {}


