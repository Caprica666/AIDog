import os
import pytest
from robot_functions import RobotFunctions

MOCK_UNITY_DIR = os.path.join(os.path.dirname(__file__), 'static', 'mock_unity')

@pytest.fixture
def robot_funcs():
    #robot = RobotFunctions(mock_unity_dir = MOCK_UNITY_DIR, mock_yolo = True)
    robot = RobotFunctions()
    robot.unity.set_robot_yangle({ "current_angle" : 60 })
    robot.yolo.frame_count = 0
    return robot            

def test_get_function_list(robot_funcs):
    funcs = robot_funcs.get_function_list()
    assert isinstance(funcs, list)
    assert any(f['name'] == 'turn_robot_camera' for f in funcs)
    assert any(f['name'] == 'detect_object' for f in funcs)

def test_turn_robot_camera_valid(robot_funcs):
    args = {
        "amount_to_turn": 30,
        "current_angle": 0,
        "direction": "clockwise",
        "end_angle": 180
        }
    result = robot_funcs.turn_robot_camera(args)
    assert "current_angle" in result
    assert "at_end_angle" in result
    assert result["current_angle"] == 30
    assert result["at_end_angle"] == False
    assert "action" in result
    assert "image" in result
    assert result["status"] == "robot successfully turned"
    
def test_turn_robot_camera_end_angle(robot_funcs):
    args = {
        "amount_to_turn": 30,
        "current_angle": 60,
        "direction": "clockwise",
        "end_angle": 70
        }
    result = robot_funcs.turn_robot_camera(args)
    assert "current_angle" in result
    assert "at_end_angle" in result
    assert result["current_angle"] == 70
    assert result["at_end_angle"] == True
    assert "action" in result
    assert "image" in result
    assert result["status"] == "robot at end angle"

def test_turn_robot_camera_missing_args(robot_funcs):
    args = {"amount_to_turn": 30}
    result = robot_funcs.turn_robot_camera(args)
    assert "error" in result["status"]

def test_detect_object_missing_label(robot_funcs):
    result = robot_funcs.detect_object({})
    assert "error" in result["status"]

def test_detect_object_no_image(robot_funcs):
    robot_funcs.unity.current_image = None
    result = robot_funcs.detect_object({"label": "dog"})
    assert "error" in result["status"]

def test_detect_object_found(robot_funcs):
    result = robot_funcs.detect_object({"label": "ball"})
    assert result["status"] == "Object not found"
    args = {"amount_to_turn": 30, "current_angle": 0, "direction": "clockwise", "end_angle" : 180 }
    result = robot_funcs.turn_robot_camera(args)
    assert result["current_angle"] == 30
    assert result["status"] == "robot successfully turned"
    result = robot_funcs.detect_object({"label": "ball"})
    assert result["label"] == "ball"
    assert result["box"] == [-0.5, 162.0, 43, 36]
    assert result["image"] is not None

def test_detect_object_not_found(robot_funcs):
    result = robot_funcs.detect_object({"label": "cat"})
    assert result["status"] == "Object not found"
    assert result["image"] is not None
