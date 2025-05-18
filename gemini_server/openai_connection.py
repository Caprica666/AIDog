import os
from openai import OpenAI
import base64
import logging
from typing import Optional

class OpenAIClient:
    """
    A class to interact with the OpenAI API for object detection and bounding box generation.
    Sets up the initial prompt and configuration for the OpenAI model.
    """
    def __init__(self, logger, model_name="gpt-4-vision-preview"):
        self.openai_key_var = "OPENAI_API_KEY"
        self.OPENAI_API_KEY = os.getenv(self.openai_key_var)
        if self.OPENAI_API_KEY is None:
            raise ValueError(self.openai_key_var + " environment variable not set.")
        self.logger = logger
        self.model_name = model_name
        self.initial_prompt = (
            "You are controlling a robot that has a camera. You can see the world through the robot's camera. "
            "You will be asked to find objects the robot sees and return their bounding boxes. "
            "If the object is not found in the image provided, call the turn_robot_camera function with the following arguments: "
            "- amount_to_turn: The number of degrees to turn the camera (use 30 degrees). "
            "- direction: The direction to turn the camera (use 'counterclockwise'). "
            "This function will provide a new image of what the robot sees after it turns. "
            "It will provide a new current angle for the robot and set at_start_angle to True if turning the robot brings it back to the starting angle. "
            "If at_start_angle is True, indicate that the object is not found and do not turn the robot camera further. "
            "Return bounding boxes as a JSON array with the following format: "
            "- label: The name of the object. "
            "- bbox: The bounding box coordinates in the format [ymin, xmin, ymax, xmax]. "
            "Never return masks or code fencing. Limit to 5 objects. "
            "If an object is present multiple times, name them according to their unique characteristic (colors, size, position, unique characteristics, etc..)."
        )
        self.client = OpenAI()

    def call_with_functions(self, prompt, image, function_list):
        """
        Call the OpenAI API with a prompt and an image, and return the response.
        Args:
            prompt: The text prompt from the user.
            image: The image data as a PNG encoded byte array.
            function_list: A list of functions to be used in the API call (not used in OpenAI API, but kept for compatibility).
        Returns:
            A dictionary containing the function call, arguments, and text response.
        """
        # Encode image as base64 for OpenAI API
        image_b64 = base64.b64encode(image).decode('utf-8')
        user_prompt =  { "role": "user", "content": { "type": "input_text", "text": prompt } }
        system_prompt =  { "role": "system", "content": { "type": "input_text", "text": self.initial_prompt } }
        self.prompt = [ system_prompt, user_prompt ]
        input = [ system_prompt, user_prompt ]
        input.append({ "role": "user", "content": { "type": "input_image", "image_url": {"url": f"data:image/png;base64,{image_b64}" } } })

        try:
            response = self.client.chat.completions.create(
                model = self.model_name,
                messages = input,
                tools = function_list
            )
            output = response.output[0]
            result = {}
            if "error" in response:
                result["status"] = "ERROR: " + response.error
                return result
            if "type" in output:
                if output["type"] == "function_call":
                    function_call = output
                    self.input.append(function_call)
                    result["function_call"] = function_call
                    result["args"] = output["arguments"]
                    result["function_name"] = output["name"]
                    return result
                elif output["type"] == "message" and "type" in output["content"] and output["content"]["type"] == "text":
                    result["text"] = output["content"]["text"]
                    return result                        
            result["status"] = "ERROR: " +  response
            return result
        except Exception as e:
            self.logger.error(f"OpenAI call failed: {str(e)}")
            return {"status": "ERROR: " + str(e)}

    def call_with_function_response(self, function_call, function_result, image):
        """
        Call the OpenAI API with a function call and its result, and return the response.  
        Args:
            function_call: The function call made by the model.
            function_result: The result of the function call.
            image: The image data as a PNG encoded byte array.
            Returns:                
                Response from OpenAI after executing the function call.
                This should be a list of bounding boxes and labels of the objects found
                or a message indicating that the object was not found.
        """
        # For OpenAI, just re-call with the new image and prompt
        input = [ ]
        input.append(self.prompt)
        if image is not None:
            image_b64 = base64.b64encode(image).decode('utf-8')
            input.append({ "role": "user", "content": { "type": "input_image", "image_url": {"url": f"data:image/png;base64,{image_b64}" } } })
        input.append(function_call)
        input.append({
            "type": "function_call_output",
            "call_id": function_call["call_id"],
            "output": function_result
        })

        response = self.client.chat.completions.create(
                model = self.model_name,
                messages = input)
        return response