import uuid
from google import genai
from google.genai import types
import os
from typing import Optional

class GeminiClient:
    def __init__(self, logger, model_name="gemini-2.5-pro-exp-03-25"):
        GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        if (GEMINI_API_KEY is None):
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.logger = logger
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = model_name # @param ["gemini-1.5-flash-latest","gemini-2.0-flash-lite","gemini-2.0-flash","gemini-2.5-flash-preview-04-17","gemini-2.5-pro-exp-03-25"] {"allow-input":true}
        self.initial_prompt = """
            You are controlling a robot that has a camera. You can see the world through the robot's camera.
            You will be asked to find objects the robot sees and return their bounding boxes.
            If the object is not found in the image provided, return its bounding box.
            Return bounding boxes as a JSON array with labels. Never return masks or code fencing. Limit to 10 objects.
            If an object is present multiple times, name them according to their unique characteristic (colors, size, position, unique characteristics, etc..).
            If the object is not found in the image, call the turn_robot_camera function with the following arguments:
                - amount_to_turn: The number of degrees to turn the camera (use 30 degrees).
                - direction: The direction to turn the camera (use "clockwise" here).
            This function will provide a new image of what the robot sees after it turns.
            It will provide a new current angle for the robot and set at_start_angle to True if turning the robot brings it back to the starting angle.
            If at_start_angle is True, indicate that the object is not found and do not turn the robot camera further.
        """
        self.safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH",
            ),
        ]
        
    def call_with_functions(self, prompt, image, function_list):
        self.contents = [ types.Content(role = "user", parts = [ types.Part(text = prompt) ]) ]
        image_part = types.Part.from_bytes(data=image, mime_type="image/png")
        self.contents.append(types.Content(role="user", parts = [image_part]))
        tools = self.convert_functions_to_gemini_tools(function_list)
        try:
            self.config = types.GenerateContentConfig(
                    system_instruction = self.initial_prompt,
                    safety_settings = self.safety_settings,
                    tools = tools,
                    automatic_function_calling = types.AutomaticFunctionCallingConfig(disable = True),
                )
        except Exception as e:
            self.logger.error(f"GenerateContentConfig call failed: {str(e)}")
            raise
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=self.contents,
            config=self.config
        )
        return response
        
    def call_with_function_response(self, function_call, function_result, image):
        function_response_part = types.Part.from_function_response(
            name = function_call.name,
            response = function_result
        )
        # Append function call and result of the function execution to contents
        self.contents.append(types.Content(role="model", parts = [types.Part(function_call=function_call)])) # Append the model's function call message
        self.contents.append(types.Content(role="user", parts = [function_response_part])) # Append the function response
        if image is not None:
            image_part = types.Part.from_bytes(data=image, mime_type="image/png")
            self.contents.append(types.Content(role="user", parts = [image_part]))
        final_response = self.client.models.generate_content(
            model=self.model_name,
            config=self.config,
            contents=self.contents,
        )
        return final_response

    def convert_function_to_gemini_tool(self, function):
        """Convert a function to Gemini format.""" 
        func_decl = types.FunctionDeclaration(
            name = function["name"],
            description = function["description"])
        tool = types.Tool(function_declarations = [func_decl])
        return tool
    
    def convert_functions_to_gemini_tools(self, function_list):
        """Convert function list to Gemini format."""
        tools = []
        for function in function_list:
            tool = self.convert_function_to_gemini_tool(function)     
            tools.append(tool)
        return tools
    
    # Find the objects in the image designated in the prompt.
    # The image is passed as a PNG encoded byte array.
    # The prompt is a string that describes the objects to find.
    def find_objects_in_image(self, prompt, image):
        """Find objects in the image using Gemini API.
        
        Args:
            prompt: The text prompt from the user indicating what to look for
            image: The image data as a PNG encoded byte array
            
        Returns:
            A JSON string containing the bounding boxes and labels of the objects found
        """
        # Run model to find bounding boxes
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[prompt, types.Part.from_bytes(data=image, mime_type="image/png")],
            config=types.GenerateContentConfig(
                system_instruction=self.bounding_box_system_instructions,
                temperature=0.5,
                safety_settings=self.safety_settings,
                response_mime_type='application/json',
            )
        )
        # Check output
        self.logger.debug("find_objects_in_image: ", response.text)
        return response.text






