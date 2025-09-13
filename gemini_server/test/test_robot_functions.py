import os
import pytest
from PIL import Image
from pathlib import Path
from robot_functions import RobotFunctions
MOCK_UNITY = False
MOCK_YOLO = False
TEST_PATH = Path.cwd()
PARENT_PATH = TEST_PATH.parent                      
MOCK_UNITY_DIR = os.path.join(PARENT_PATH, 'gemini_server', 'static', 'mock_unity')

@pytest.fixture
def robot_funcs():
    if MOCK_UNITY:
        robot = RobotFunctions(connection_type ="mock_unity", mock_unity_dir = MOCK_UNITY_DIR, mock_yolo = MOCK_YOLO)
    else:
        robot = RobotFunctions(connection_type = "unity")
    robot.set_robot_yangle({ "current_angle" : 60 })
    robot.yolo.frame_count = 0
    return robot            

def show_image(image_png_data):
    if image_png_data is None:
        return
    image = Image.open(image_png_data)
    image.show() 
    
def test_get_function_list(robot_funcs):
    funcs = robot_funcs.get_function_list()
    assert isinstance(funcs, list)
    assert any(f['name'] == 'turn_robot_camera' for f in funcs)
    assert any(f['name'] == 'detect_object' for f in funcs)

def test_turn_robot_camera_valid(robot_funcs):
    args = {
        "turn_angle": 30,
        "current_angle": 0,
        "direction": "clockwise",
        "end_angle": 180
        }
    result = robot_funcs.turn_robot_camera(args)
    assert "current_angle" in result
    assert "at_end" in result
    assert result["current_angle"] == 30
    assert result["at_end"] == False
    assert result["success"] is True
    assert "action" in result
    assert "image" in result
    assert "robot successfully turned" in result["message"] 
    
def test_turn_robot_camera_end_angle(robot_funcs):
    args = {
        "turn_angle": 30,
        "current_angle": 60,
        "direction": "clockwise",
        "end_angle": 70
        }
    result = robot_funcs.turn_robot_camera(args)
    assert "current_angle" in result
    assert "at_end" in result
    assert result["current_angle"] == 70
    assert result["at_end"] == True
    assert result["success"] is True
    assert "action" in result
    assert "image" in result
    assert "robot at end angle" in result["message"]
    
def test_turn_robot_camera_end_angle_neg(robot_funcs):
    args = {
        "turn_angle": 30,
        "current_angle": -60,
        "direction": "counterclockwise",
        "end_angle": -70
        }
    result = robot_funcs.turn_robot_camera(args)
    assert "current_angle" in result
    assert "at_end" in result
    assert result["current_angle"] == -70
    assert result["at_end"] == True
    assert result["success"] is True
    assert "action" in result
    assert "image" in result
    assert "robot at end angle" in result["message"]

def test_turn_robot_camera_missing_args(robot_funcs):
    args = {"turn_angle": 30}
    result = robot_funcs.turn_robot_camera(args)
    assert result["success"] is False
    assert "error" in result["message"]

def test_detect_object_missing_label(robot_funcs):
    result = robot_funcs.detect_object({})
    assert result["success"] is False
    assert "error" in result["message"]

def test_detect_object_no_image(robot_funcs):
    robot_funcs.remote_robot.current_image = None
    result = robot_funcs.detect_object({"label": "dog"})
    assert result["success"] is False
    assert "error" in result["message"]

def test_detect_object_not_found(robot_funcs):
    result = robot_funcs.detect_object({"label": "cat"})
    assert result["success"] is False
    assert result["message"] == "Object not found"
    assert result["image"] is not None
    
def test_detect_ball_found(robot_funcs):
    result = robot_funcs.detect_object({"label": "ball"})
    assert result["message"] == "Object not found"
    assert result["success"] is False
    args = {"turn_angle": 30, "current_angle": 0, "direction": "counterclockwise", "end_angle" : 180 }
    result = robot_funcs.turn_robot_camera(args)
    assert result["success"] is True
    assert result["current_angle"] == -30
    assert "robot successfully turned" in result["message"]
    assert result["image"] is not None
    result = robot_funcs.detect_object({"label": "ball"})
    assert result["success"] is True
    assert result["message"] == "Object found"
    assert result["label"] == "ball"
    assert [int(x) for x in result["box"]] == [49, 150, 25, 23]

def test_detect_box_found(robot_funcs):
    result = robot_funcs.detect_object({"label": "box"})
    assert result["message"] == "Object not found"
    assert result["success"] is False

    args = {"turn_angle": 30, "current_angle": 60, "direction": "counterclockwise", "end_angle" : 180 }
    result = robot_funcs.turn_robot_camera(args)
    assert result["success"] is True
    assert result["current_angle"] == 30
    assert "robot successfully turned" in result["message"]
    result = robot_funcs.detect_object({"label": "box"})
    assert result["message"] == "Object not found"
    assert result["success"] is False
    robot_funcs.yolo.frame_count -= 1
    result = robot_funcs.detect_object({"label": "ball"})
    assert result["success"] is True
    assert [int(x) for x in result["box"]] == [49, 150, 25, 23]
    
    args = {"turn_angle": 30, "current_angle": 30, "direction": "counterclockwise", "end_angle" : 180 }
    result = robot_funcs.turn_robot_camera(args)
    assert result["success"] is True
    assert result["current_angle"] == 0
    assert "robot successfully turned" in result["message"]    
    result = robot_funcs.detect_object({"label": "box"})
    assert result["label"] == "box"
    assert result["success"] is True
    assert [int(x) for x in result["box"]] == [29, 150, 33, 27]
    robot_funcs.yolo.frame_count -= 1
    result = robot_funcs.detect_object({"label": "ball"})
    assert result["success"] is True
    assert [int(x) for x in result["box"]] == [131, 148, 22, 22]
    
    args = {"turn_angle": 30, "current_angle": 0, "direction": "counterclockwise", "end_angle" : 180 }
    result = robot_funcs.turn_robot_camera(args)
    assert result["success"] is True
    assert result["current_angle"] == -30
    assert "robot successfully turned" in result["message"]
    assert result["success"] is True
    result = robot_funcs.detect_object({"label": "box"})
    print("find the box:" + result["message"])
    assert "image" in result
    assert result["label"] == "box"
    assert [int(x) for x in result["box"]] == [111, 148, 30, 28]
    
def test_set_robot_yangle(robot_funcs):
    result = robot_funcs.set_robot_yangle({ "current_angle" : 60 })
    assert result["success"] is True
