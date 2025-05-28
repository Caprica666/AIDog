
from mcp.server.fastmcp import FastMCP
from flask import jsonify
from robot_functions import RobotFunctions

UNITY_APP_URL = "http://localhost:5000"

mcp = FastMCP("Robot MCP Server")
robot = RobotFunctions()

@mcp.tool(description = "Turn the robot camera a specific number of degrees.")
def turn_robot_camera(amount_to_turn, current_angle, direction):
    """
    Turn the robot camera a specific number of degrees.
    
    Args:
        amount_to_turn: The number of degrees to turn the camera.
        current_angle: The current angle of the camera before this turn.
        direction: The direction to turn the camera ("clockwise" or "counterclockwise").
        
    Returns: JSON with the following:
        at_end_angle: True if camera has been turned to the stendart angle, False otherwise.
        current_angle: The current angle of the camera after the turn.
        image: The image from the robot camera after the turn.
        status: status or error message
    """  
    if amount_to_turn == None or direction == None:
        return jsonify({ "status" : "error: Missing required arguments for turn_robot_camera function." })
    result = robot.turn_robot_camera( {
                                    "amount_to_turn": amount_to_turn,
                                    "current_angle": current_angle,
                                    "direction": direction,
                                    "end_angle": 360 })  
    if "error" not in result["status"]:
        result["action"] = "resubmit"
    return jsonify(result)

@mcp.tool(description = "Determine if the robot can currently see an object and returns its bounding box.")
def detect_object(label):
    """
    Determine if the robot can currently see an object and returns its bounding box.
    
    Args:
        label: name of the object to find
        
    Returns: JSON with image, object name and bounds (if the object is found)
        label: name of object found
        bbox: bounding box of object in format [ x, y, w, h ]
        status: status or error message
        image: PNG image from the robot's camera as a base64 string
    """
    if label is None:
        return jsonify({ "status": "error: Missing label for detect_objects function." })
    result = robot.detect_objects({ "label" : label})
    return jsonify(result)

#async def main():
#    await mcp.run_async(transport="stdio")

#if __name__ == "__main__":
#    asyncio.run(main())

if __name__ == "__main__":
    mcp.run(transport = "stdio")


