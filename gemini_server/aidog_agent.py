
from flask import jsonify
import mcp
from unity_connection import bounds_to_unity, image_from_unity, start_server
from mcp.server.fastmcp import FastMCP
import logging
import threading
import json
from unity_connection import UnityConnection
from typing import Tuple
from gemini_connection import GeminiClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("AIDogAgent")
logger.setLevel(logging.DEBUG)

AGENT_SERVER_URL = "http://localhost:8000"
UNITY_APP_URL = "http://localhost:5000"
UNITY_CONNECT_PORT = 5001
USE_GEMINI = True  # Set to False to disable Gemini usage
logger.info("Starting AIDog agent...")
mcp = FastMCP("Unity AIDog Server", host=AGENT_SERVER_URL, port=8000)
mcp.set_debug(True)
gemini = GeminiClient(logger)
unity = UnityConnection(None, UNITY_APP_URL)

@mcp.tool(description="Generate the name of a file based on the user's prompt.")
async def generate_filename_from_prompt(prompt: str) -> Tuple[bytes, str]:
    """Generate the name of a file based on the user's prompt.

    Args:
        prompt: User's text prompt telling the robot what to look for
        
    Returns:
        the name of the file generated
    """
    try:   
        # Ask gemini to generate a filename based on the prompt
        filename = await gemini.convert_prompt_to_filename(prompt)
        return filename
    
    except Exception as e:
        error_msg = f"Error generating image: {str(e)}"
        logger.error(error_msg)
        return None
                       
@mcp.tool(description="Capture an image of what the robot sees.")
async def capture_image(filename: str) -> str:
    """
    Capture an image of what the robot sees as a PNG file.

    Args:
        filename: name of file to save the image to.
        The image will be 512x512 in PNG format.
        
    Returns:
        name of the file saved or None if the image could not be captured.
    """
    image_data = unity.image_from_unity()
    with open(filename, 'wb') as fd:
        fd.write(image_data)
        fd.close()
    logger.info(f"capture_image: Image saved to {filename}")
    return filename
        

@mcp.tool(description="Find the name and bounding box of a designated object in an image.")
async def find_object_in_image(user_prompt, image):
    response = await gemini.find_objects_in_image(user_prompt, image)    
    response_dict = json.loads(response)
    # Check if the response contains bounding boxes
    if response_dict:
        first_entry = response_dict[0]
        object_name = first_entry['label']
        gemini_bbox = first_entry['box_2d']
        # gemini returns the bounding box ymin, xmin, ymax, xmax in a 1000x1000 coordinate system
        # convert it xmin, ymin, width, heigth in a 512x512 coordinate system
        bbox = [0, 0, 0, 0]
        bbox[0] = gemini_bbox[1]  # xmin
        bbox[1] = gemini_bbox[0]  # ymin   
        bbox[3] = gemini_bbox[2] - gemini_bbox[0]  # ymax - ymin
        bbox[2] = gemini_bbox[3] - gemini_bbox[1]  # xmax - xmin
        bbox = [int((coord * 512) / 1000) for coord in bbox]
        return jsonify({ "object_name": object_name, "bbox": bbox})
    else:
        return None
    
# Initialize the agent
if __name__ == "__main__":
    logger.info("Starting Unity connection server in a separate thread...")
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    logger.info("Starting MCP server...")
    mcp.run()



