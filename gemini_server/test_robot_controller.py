import os
import pytest
import logging
from robot_controller import RobotController
from gemini_connection import GeminiClient

MOCK_UNITY = False
MOCK_YOLO = False
MOCK_UNITY_DIR = os.path.join(os.path.dirname(__file__), 'static', 'mock_unity')
logging.basicConfig(level = logging.DEBUG)
logger = logging.getLogger("RobotClient")
logger.setLevel(logging.DEBUG)
          
@pytest.fixture
def robot_controller():
    aihelper = GeminiClient(logger, model_name = "gemini-2.0-flash")
    if MOCK_UNITY:
        robot = RobotController(logger, aihelper, "mock_unity", mock_unity_dir = MOCK_UNITY_DIR, mock_yolo = MOCK_YOLO)
    else:
        robot = RobotController(logger, aihelper, "unity")
    robot.robot.remote_robot.set_robot_yangle({ "current_angle" : 60, "angular_velocity": 20 })
    robot.robot.yolo.frame_count = 0
    robot.robot.remote_robot.frame_count = 0
    robot.robot.remote_robot.image_from_robot()
    return robot

def test_process_bounding_box_list(robot_controller):
    bbox_input = '   json [ {"label": "ball", "box": [-0.5, 162.0, 43, 36] } ] '
    result = {}
    robot_controller.process_bounding_box(bbox_input, result)
    assert result["label"] == "ball"
    assert result["success"] is True
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
    assert result["success"] is True
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
    assert "message" in result
    assert "Failed to parse LLM response" in result["message"]
    assert result["success"] is False
    assert result["action"] == None


def test_turn_robot_camera_valid(robot_controller):
    args = {"turn_angle": 30, "current_angle": 0, "angular_velocity": 10, "direction": "clockwise", "end_angle" : 180}
    result = robot_controller.process_function_call("turn_robot_camera", args)
    assert "current_angle" in result
    assert result["current_angle"] == 30
    assert "at_end" in result
    assert result["at_end"] == False
    assert "action" in result
    assert result["action"] == "resubmit"
    assert "robot successfully turned" in result["message"]
    assert result["success"] is True
    assert result["success"] is True

def test_turn_robot_camera_missing_args(robot_controller):
    args = {"turn_angle": 30}
    result = robot_controller.process_function_call("turn_robot_camera", args)
    assert "error" in result["message"]
    assert result["success"] is False

def test_detect_object_missing_label(robot_controller):
    result = robot_controller.process_function_call("detect_object", {})
    assert "error" in result["message"]
    assert result["success"] is False


def test_detect_object_no_image(robot_controller):
    robot_controller.robot.remote_robot.current_image = None
    result = robot_controller.process_function_call("detect_object", {"label": "dog"})
    assert "error" in result["message"]
    assert result["success"] is False


def test_detect_object_found(robot_controller):
    result = robot_controller.process_function_call("detect_object", {"label": "ball"})
    assert result["message"] == "Object not found"
    args = {"turn_angle": 30, "current_angle": 0, "angular_velocity": 10, "direction": "counterclockwise", "end_angle" : -180 }
    result = robot_controller.process_function_call("turn_robot_camera", args)
    assert result["current_angle"] == -30
    assert result["success"] is True
    assert "robot successfully turned" in result["message"]
    assert result["action"] == "resubmit"
    result = robot_controller.process_function_call("detect_object", {"label": "ball"})
    assert result["label"] == "ball"
    assert result["box"] == [-0.5, 162.0, 43, 36]
    assert result["message"] == "Object found"
    assert result["success"] is True
    assert result["image"] is not None

def test_detect_object_not_found(robot_controller):
    result = robot_controller.process_function_call("detect_object", {"label": "cat"})
    assert result["message"] == "Object not found"
    assert result["image"] is not None
    assert result["success"] is False
    
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
    assert "robot successfully turned" in result["message"]
    assert result["success"] is True
    result = robot_controller.process_command("find the ball")
    assert "image" in result
    assert result["image"] is not None
    assert result["message"] == "Object found"
    assert robot_controller.function_info is None
    assert result["label"] == "ball"
    assert result["box"] == [-0.5, 162.0, 43, 36]
    assert result["success"] is True
    
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
    assert "robot successfully turned" in result["message"]
    assert result["success"] is True
    assert result["action"] == "resubmit"
    result = robot_controller.process_command("find the box")
    assert robot_controller.function_info is not None
    assert robot_controller.function_info["name"] == "turn_robot_camera"
    assert "function_output" in robot_controller.function_info
    result = robot_controller.function_info["function_output"]
    assert result["current_angle"] == -60
    assert "robot successfully turned" in result["message"]
    assert result["success"] is True
    assert result["action"] == "resubmit"
    result = robot_controller.process_command("find the box")
    assert robot_controller.function_info is not None
    assert robot_controller.function_info["name"] == "turn_robot_camera"
    assert "function_output" in robot_controller.function_info
    result = robot_controller.function_info["function_output"]
    assert result["current_angle"] == -90
    assert "robot successfully turned" in result["message"]
    assert result["success"] is True
    assert result["action"] == "resubmit"
    result = robot_controller.process_command("find the box")
    assert "image" in result
    assert result["image"] is not None
    assert result["message"] == "Object found"
    assert robot_controller.function_info is None
    assert result["label"] == "box"
    assert result["box"] == [46.5, 155.66666666666666, 55, 55]
    
    