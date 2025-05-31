import os
import pytest
from unittest.mock import patch, MagicMock
from robot_functions import RobotFunctions

MOCK_UNITY_DIR = os.path.join(os.path.dirname(__file__), 'static', 'mock_unity')

@pytest.fixture
def robot_funcs():
    return RobotFunctions(mock_unity_dir=MOCK_UNITY_DIR)

def test_get_function_list(robot_funcs):
    funcs = robot_funcs.get_function_list()
    assert isinstance(funcs, list)
    assert any(f['name'] == 'turn_robot_camera' for f in funcs)
    assert any(f['name'] == 'detect_object' for f in funcs)

def test_turn_robot_camera_valid(robot_funcs):
    args = {"amount_to_turn": 30, "current_angle": 0, "direction": "clockwise"}
    result = robot_funcs.turn_robot_camera(args)
    assert "current_angle" in result
    assert "action" in result
    assert "image" in result
    assert result["status"] == "robot successfully turned"

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

@patch("robot_functions.ObjectDetector.detect_objects")
def test_detect_object_found(mock_detect, robot_funcs):
    # Simulate YOLO returning a detection
    mock_detect.return_value = [{"label": "dog", "box": [10, 10, 50, 50]}]
    result = robot_funcs.detect_object({"label": "dog"})
    assert result["status"] == "Object found"
    assert result["label"] == "dog"
    assert result["box"] == [10, 10, 50, 50]
    assert result["image"] is not None

@patch("robot_functions.ObjectDetector.detect_objects")
def test_detect_object_not_found(mock_detect, robot_funcs):
    # Simulate YOLO returning no detections
    mock_detect.return_value = []
    result = robot_funcs.detect_object({"label": "cat"})
    assert result["status"] == "Object not found"
    assert result["image"] is not None
