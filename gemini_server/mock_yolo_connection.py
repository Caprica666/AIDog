

class MockObjectDetector():
    def __init__(self, model_name = "yolo11n.pt", labels = None):
        self.labels = labels
        self.frame_count = 0
        self.mock_results = [
            {}, # "find the ball" capturedimage1.png
            [ {'label': 'ball', 'box': [-0.5, 162.0, 43, 36] } ], # "find the ball" capturedimage2.png
            {},    # "find the box" capturedimage3.png
            [ {'label': 'box', 'box': [46.5, 155.66666666666666, 55, 55]} ] ] # "find the box" capturedimage4.png
      
    def set_classes(self, labels):
        if self.labels != labels:
            self.labels = labels
        
    def detect_objects(self, image):       
        if self.frame_count > 3:
            self.frame_count = 0
        results = self.mock_results[self.frame_count]
        self.frame_count += 1
        if isinstance(results, (list, tuple)) and len(results) > 0:
            temp = results[0]
            if self.labels and "label" in temp:
                label = self.labels[0]
                if temp["label"] == label:
                    return results          
        return {}


