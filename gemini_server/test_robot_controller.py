import os
import pytest
import logging
from robot_controller import RobotController
from gemini_connection import GeminiClient

MOCK_UNITY = True
MOCK_YOLO = True
MOCK_UNITY_DIR = os.path.join(os.path.dirname(__file__), 'static', 'mock_unity')
logging.basicConfig(level = logging.DEBUG)
logger = logging.getLogger("RobotClient")
logger.setLevel(logging.DEBUG)
          
@pytest.fixture
def robot_controller():
    aihelper = GeminiClient(logger, model_name = "gemini-2.0-flash")
    if MOCK_UNITY:
        robot = RobotController(logger, aihelper, mock_unity_dir = MOCK_UNITY_DIR, mock_yolo = MOCK_YOLO)
    else:
        robot = RobotController(logger, aihelper)
    robot.robot.unity.set_robot_yangle({ "current_angle" : 60 })
    return robot

def test_process_bounding_box_list(robot_controller):
    bbox_input = '   json [ {"label": "ball", "box": [-0.5, 162.0, 43, 36] } ] '
    result = {}
    robot_controller.process_bounding_box(bbox_input, result)
    assert result["label"] == "ball"
    assert "bbox" in result
    bbox = result["bbox"]
    assert bbox[0] == -0.5
    assert bbox[1] == 162.0
    assert bbox[2] == 43
    assert bbox[3] == 36
    
def test_process_bounding_box_single(robot_controller):
    result = {}
    bbox_input = 'json----{ "label" : "cat", "bbox" : [ 1, 2, 3, 4 ]}'
    robot_controller.process_bounding_box(bbox_input, result)
    assert result["label"] == "cat"
    assert "bbox" in result
    bbox = result["bbox"]
    assert bbox[0] == 1
    assert bbox[1] == 2
    assert bbox[2] == 3
    assert bbox[3] == 4
    
def test_process_bounding_box_error(robot_controller):
    result = {}
    bbox_input = "object not found"
    robot_controller.process_bounding_box(bbox_input, result)
    assert "status" in result
    assert result["status"] == "Failed to parse LLM response."
    assert result["action"] == None


def test_turn_robot_camera_valid(robot_controller):
    args = {"amount_to_turn": 30, "current_angle": 0, "direction": "clockwise", "end_angle" : 180}
    result = robot_controller.process_function_call("turn_robot_camera", args)
    assert "current_angle" in result
    assert result["current_angle"] == 30
    assert "at_end_angle" in result
    assert result["at_end_angle"] == False
    assert "action" in result
    assert result["action"] == "resubmit"
    assert result["status"] == "robot successfully turned"

def test_turn_robot_camera_missing_args(robot_controller):
    args = {"amount_to_turn": 30}
    result = robot_controller.process_function_call("turn_robot_camera", args)
    assert "error" in result["status"]

def test_detect_object_missing_label(robot_controller):
    result = robot_controller.process_function_call("detect_object", {})
    assert "error" in result["status"]

def test_detect_object_no_image(robot_controller):
    robot_controller.robot.unity.current_image = None
    result = robot_controller.process_function_call("detect_object", {"label": "dog"})
    assert "error" in result["status"]

def test_detect_object_found(robot_controller):
    result = robot_controller.process_function_call("detect_object", {"label": "ball"})
    assert result["status"] == "Object not found"
    args = {"amount_to_turn": 30, "current_angle": 0, "direction": "counterclockwise", "end_angle" : -180 }
    result = robot_controller.process_function_call("turn_robot_camera", args)
    assert result["current_angle"] == -30
    assert result["status"] == "robot successfully turned"
    assert result["action"] == "resubmit"
    result = robot_controller.process_function_call("detect_object", {"label": "ball"})
    assert result["label"] == "ball"
    assert result["box"] == [-0.5, 162.0, 43, 36]
    assert result["status"] == "Object found"
    assert result["image"] is not None

def test_detect_object_not_found(robot_controller):
    result = robot_controller.process_function_call("detect_object", {"label": "cat"})
    assert result["status"] == "Object not found"
    assert result["image"] is not None
    
def test_process_command_single_turn(robot_controller):
    result = robot_controller.process_command("find the ball")
    assert "image" in result
    assert result["action"] == "resubmit"
    assert result["image"] is not None
    assert robot_controller.function_info is not None
    assert robot_controller.function_info["name"] == "turn_robot_camera"
    assert "function_output" in robot_controller.function_info
    result = robot_controller.function_info["function_output"]
    assert result["current_angle"] == -30
    assert result["status"] == "robot successfully turned"
    result = robot_controller.process_command("find the ball")
    assert "image" in result
    assert result["image"] is not None
    assert result["status"] == "Object found"
    assert robot_controller.function_info is None
    assert result["label"] == "ball"
    assert result["box"] == [-0.5, 162.0, 43, 36]
    
def test_process_command_three_turns(robot_controller):
    result = robot_controller.process_command("find the box")
    assert "image" in result
    assert result["action"] == "resubmit"
    assert result["image"] is not None
    assert robot_controller.function_info is not None
    assert robot_controller.function_info["name"] == "turn_robot_camera"
    assert "function_output" in robot_controller.function_info
    result = robot_controller.function_info["function_output"]
    assert result["current_angle"] == -30
    assert result["status"] == "robot successfully turned"
    assert result["action"] == "resubmit"
    result = robot_controller.process_command("find the box")
    assert robot_controller.function_info is not None
    assert robot_controller.function_info["name"] == "turn_robot_camera"
    assert "function_output" in robot_controller.function_info
    result = robot_controller.function_info["function_output"]
    assert result["current_angle"] == -60
    assert result["status"] == "robot successfully turned"
    assert result["action"] == "resubmit"
    result = robot_controller.process_command("find the box")
    assert robot_controller.function_info is not None
    assert robot_controller.function_info["name"] == "turn_robot_camera"
    assert "function_output" in robot_controller.function_info
    result = robot_controller.function_info["function_output"]
    assert result["current_angle"] == -90
    assert result["status"] == "robot successfully turned"
    assert result["action"] == "resubmit"
    result = robot_controller.process_command("find the box")
    assert "image" in result
    assert result["image"] is not None
    assert result["status"] == "Object found"
    assert robot_controller.function_info is None
    assert result["label"] == "box"
    assert result["box"] == [46.5, 155.66666666666666, 55, 55]
    
    