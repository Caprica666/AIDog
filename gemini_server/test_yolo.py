import unittest
import yolo_connection as Yolo
from PIL import Image
import os
import numpy as np
import logging

logging.basicConfig(level = logging.DEBUG)

do_compare = True
#detect_this = ["dog", "box", "ball", "toy"]
detect_this = ["dog", "box", "striped ball", "ball", "red toy", "blue toy", "brown toy", "green toy", "purple toy"]
test_files = ["dog_toys_in_LR.jpg", "capturedimage.png", "ball_on_floor.jpg",
              "saber_blue_toy2.jpg", "saber_brown_toy.jpg", "saber_with_ball.jpg" ]

#yolo_model = "yolo12n.pt"
yolo_model = "yoloe-11l-seg.pt"

test_results_yolo12n = [
    [ # dog_toys_in_LR.jpg
        {'label': 'teddy bear', 'box': [206, 347, 174, 127]},
        {'label': 'couch', 'box': [106, 132, 211, 157]},
        {'label': 'couch', 'box': [106, 178, 212, 250]},
        {'label': 'dog', 'box': [313, 196, 143, 136]}
    ],
    [ # capturedimage.png
        {'label': 'sports ball', 'box': [203, 141, 38, 33]},
        {'label': 'suitcase', 'box': [152.5, 16.0, 103, 96]}
    ],
    [ # ball_on_floor.jpg
        {'label': 'sports ball', 'box': [88, 42, 43, 43]}
    ],
    [ # saber_blue_toy2.jpg
        {'label': 'dog', 'box': [2263, 2106, 1595, 1040]},
        {'label': 'couch', 'box': [3370, 1951, 1316, 2138]},
        {'label': 'potted plant', 'box': [503, 1128, 554, 789]},
        {'label': 'couch', 'box': [3371, 1468, 1307, 1189]},
        {'label': 'cup', 'box': [2182, 1495, 120, 154]}
    ],
    [ # saber_brown_toy.jpg
        {'label': 'dog', 'box': [367, 210, 458, 277]},
        {'label': 'couch', 'box': [148, 113, 294, 227]}
    ],
    [ # saber_with_ball.jpg
        {'label': 'dog', 'box': [254, 317, 453, 259]}, 
        {'label': 'chair', 'box': [468, 116, 222, 232]},
        {'label': 'sports ball', 'box': [422, 365, 89, 96]},
        {'label': 'dining table', 'box': [286, 79, 172, 158]}
    ]]     


test_results_yoloe = [
    [ # "dog_toys_in_LR.jpg         
        {'label': 'blue toy', 'box': [545, 392, 188, 104]},
        {'label': 'blue toy', 'box': [570, 297, 65, 58]},
        {'label': 'dog', 'box': [312, 197, 138, 135]},
        {'label': 'blue toy', 'box': [349, 305, 90, 51]},
        {'label': 'blue toy', 'box': [454, 254, 73, 52]},
        {'label': 'brown toy', 'box': [526, 293, 52, 62]},
        {'label': 'blue toy', 'box': [570, 282, 139, 107]},
        {'label': 'red toy', 'box': [454, 254, 74, 52]},
        {'label': 'blue toy', 'box': [259, 280, 47, 48]},
        {'label': 'blue toy', 'box': [617, 265, 43, 73]}
    ],
    [ # capturedimage.png
        {'label': 'green toy', 'box': [44.0, 70.33333333333333, 82, 26]},
        {'label': 'red toy', 'box': [183.5, 157.66666666666666, 37, 34]},
        {'label': 'box', 'box': [46.5, 155.66666666666666, 55, 55]},
        {'label': 'blue toy', 'box': [46.5, 155.66666666666666, 55, 55]}
    ],
    [ # ball_on_floor.jpg
        {'label': 'striped ball', 'box': [88, 41, 42, 42]}
    ],
    [ # saber_blue_toy2.jpg
        {'label': 'blue toy', 'box': [542, 2745, 449, 363]},
        {'label': 'dog', 'box': [2350, 2099, 1414, 1027]},
        {'label': 'striped ball', 'box': [841, 1775, 328, 344]},
        {'label': 'brown toy', 'box': [902, 1450, 169, 88]}
    ],
    [ # saber_brown_toy.jpg
        {'label': 'dog', 'box': [366, 207, 455, 270]},
        {'label': 'brown toy', 'box': [367, 405, 221, 129]},
        {'label': 'blue toy', 'box': [613, 163, 53, 275]},
        {'label': 'blue toy', 'box': [618, 387, 43, 42]}
    ],
    [ # saber_with_ball.jpg
        {'label': 'dog', 'box': [274, 316, 413, 256]},
        {'label': 'ball', 'box': [423, 365, 88, 95]},
        {'label': 'red toy', 'box': [423, 365, 88, 95]},
        {'label': 'striped ball', 'box': [423, 365, 88, 95]}
    ]]

class TestYOLOObjectDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        cls.static_dir = os.path.join(app_dir, 'static')
        cls.yolo_model = yolo_model
        cls.files_to_test = test_files
        if yolo_model == "yoloe-11l-seg.pt":
            cls.test_results = test_results_yoloe
            labels = detect_this
        else:
            cls.test_results = test_results_yolo12n
            labels = None
        cls.do_compare = do_compare
        logger = logging.getLogger("YOLOTest")
        logger.setLevel(logging.DEBUG)
        cls.yolo = Yolo.ObjectDetector(logger, model_name = cls.yolo_model, labels=labels)

    def detect_objects_in_file(self, filename):
        image_file = os.path.join(self.static_dir, filename)
        image = Image.open(image_file)
        img_data = np.array(image)
        # Convert RGB to BGR
        if img_data.shape[-1] == 3:
            img_data = img_data[..., ::-1]
        return self.yolo.detect_objects(img_data)

    def test_yolo_detection(self):
        save_results = []
        for i, fname in enumerate(self.files_to_test):
            with self.subTest(image=fname):
                result = self.detect_objects_in_file(fname)
                print(result)
                #save_results.append(result)
                if self.do_compare:
                    # Only compare labels and box structure, not confidence
                    expected = self.test_results[i]
                    self.assertEqual(len(result), len(expected))
                    for r, e in zip(result, expected):
                        self.assertEqual(r['label'], e['label'])
                        self.assertEqual(len(r['box']), len(e['box']))
        #print(save_results)

if __name__ == "__main__":
    unittest.main()