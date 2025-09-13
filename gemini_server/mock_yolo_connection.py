

class MockObjectDetector():
    def __init__(self, logger, model_name = "yolo11n.pt", labels = None):
        self.labels = labels
        self.frame_count = 0
        self.logger = logger
        self.mock_results = [
            {},     # capturedimage1.png
             [ {'label': 'ball', 'box': [49.5, 150.3, 25, 23] } ], # "find the ball" capturedimage2.png
             [ {'label': 'ball', 'box': [131.0, 148.6, 22, 22] },  # "find the ball" or "find the box" capturedimage3.png
               {'label': 'box', 'box': [29.5, 150.0, 33, 27]} ],
             [ {'label': 'box', 'box': [111.0, 148.6, 30, 28]} ] ] # "find the box" capturedimage4.png
        self.logger.debug("MockObjectDetector with model " + model_name)
      
    def set_classes(self, labels):
        if self.labels != labels:
            self.labels = labels
        
    def detect_objects(self, image):       
        if self.frame_count > 3:
            self.frame_count = 0
        results = self.mock_results[self.frame_count]
        self.frame_count += 1
        if isinstance(results, (list, tuple)) and len(results) > 0:
            for temp in results:
                if self.labels and "label" in temp:
                    label = self.labels[0]
                    if temp["label"] == label:
                        self.logger.debug(temp)
                        return [ temp ]         
        return {}


