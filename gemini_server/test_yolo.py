import unittest
import yolo_connection as Yolo
from PIL import Image
import os
import numpy as np

class TestYOLOObjectDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        cls.static_dir = os.path.join(app_dir, 'static')
        cls.yolo_model = "yolo12n.pt"
        cls.files_to_test = ["capturedimage.png", "ball_on_floor.jpg"]
        cls.test_results = [
            [{'label': 'sports ball', 'box': [203, 141, 38, 33]}, {'label': 'umbrella', 'box': [76, 145, 56, 51]}],
            [{'label': 'sports ball', 'box': [88, 42, 43, 44]}]
        ]
        cls.yolo = Yolo.ObjectDetector(model_name = cls.yolo_model)

    def detect_objects_in_file(self, filename):
        image_file = os.path.join(self.static_dir, filename)
        image = Image.open(image_file)
        img_data = np.array(image)
        return self.yolo.detect_objects(img_data)

    def test_yolo_detection(self):
        for i, fname in enumerate(self.files_to_test):
            with self.subTest(image=fname):
                result = self.detect_objects_in_file(fname)
                print(result)
                # Only compare labels and box structure, not confidence
                expected = self.test_results[i]
                self.assertEqual(len(result), len(expected))
                for r, e in zip(result, expected):
                    self.assertEqual(r['label'], e['label'])
                    self.assertEqual(len(r['box']), len(e['box']))

if __name__ == "__main__":
    unittest.main()