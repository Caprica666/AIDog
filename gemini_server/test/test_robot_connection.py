import os
import pytest
import logging
from PIL import Image
import io
from unity_connection import UnityConnection
from ros_connection import ROSConnection

MOCK_YOLO = False
CONNECTION_TYPE = "unity"   # "unity" or "ros"

logging.basicConfig(level = logging.DEBUG)
logger = logging.getLogger("RobotConnection")
logger.setLevel(logging.DEBUG)

ROBOT_URL = "http://localhost:5000"

@pytest.fixture
def robot_connection():
    if CONNECTION_TYPE == "unity":
        robot = UnityConnection(ROBOT_URL, logger)
    elif CONNECTION_TYPE == "ros":
        robot = ROSConnection(ROBOT_URL, logger)
    else:
        raise ValueError("CONNECTION_TYPE must be either 'unity' or 'ros'.")
    robot.set_robot_yangle({ "current_angle" : 60, "angular_velocity": 20 })
    robot.image_from_robot()
    return robot

def show_image(image_png_data):
    if image_png_data is None:
        return
    image = Image.open(image_png_data)
    image.show()              

def is_image_data(obj):
    try:
        if isinstance(obj, (bytes, bytearray)):
            Image.open(io.BytesIO(obj)).verify()
        elif hasattr(obj, 'read'):
            pos = obj.tell() if hasattr(obj, 'tell') else None
            Image.open(obj).verify()
            if pos is not None:
                obj.seek(pos)
        else:
            return False
        return True
    except Exception:
        return False
    
def test_turn_robot_camera_valid(robot_connection):
    args = {
        "turn_angle": 30,
        "current_angle": 0,
        "angular_velocity": 10,
        "end_angle": 180
        }
    result = robot_connection.turn_robot_camera(args)
    assert "last_angle" in result
    assert "at_end" in result
    assert result["last_angle"] == 30
    assert result["at_end"] == False
    assert result["success"] is True
    assert "robot successfully turned" in result["message"] 
    
def test_turn_robot_camera_end_angle(robot_connection):
    args = {
        "turn_angle": 30,
        "current_angle": 60,
        "angular_velocity": 10,
        "end_angle": 70
        }
    result = robot_connection.turn_robot_camera(args)
    assert "last_angle" in result
    assert "at_end" in result
    assert result["last_angle"] == 70
    assert result["at_end"] == True
    assert result["success"] is True
    assert "robot at end angle" in result["message"]
    
def test_turn_robot_camera_end_angle_neg(robot_connection):
    args = {
        "turn_angle": 30,
        "current_angle": -60,
        "angular_velocity": 10,
        "end_angle": -70
        }
    result = robot_connection.turn_robot_camera(args)
    assert "last_angle" in result
    assert "at_end" in result
    assert result["last_angle"] == -70
    assert result["at_end"] == True
    assert result["success"] is True
    assert "robot at end angle" in result["message"]

def test_turn_robot_camera_missing_args(robot_connection):
    args = {"turn_angle": 30}
    result = robot_connection.turn_robot_camera(args)
    assert result["success"] is False
    assert "error" in result["message"]

def test_get_camera_image(robot_connection):
    result = robot_connection.image_from_robot()
    assert result is not None
    assert is_image_data(result)
