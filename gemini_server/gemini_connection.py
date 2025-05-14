import uuid
from google import genai
from google.genai import types
import os
from typing import Optional

class GeminiClient:
    """
    A class to interact with the Gemini API for object detection and bounding box generation.
    Sets up the initial prompt and safety settings for the Gemini model."""
    def __init__(self, logger, model_name="gemini-2.5-pro-exp-03-25"):
        self.gemini_key_var = "GEMINI_API_KEY_ANNE"
        #self.gemini_key_var = "GEMINI_API_KEY"
        self.GEMINI_API_KEY = os.getenv(self.gemini_key_var)
        if (self.GEMINI_API_KEY is None):
            raise ValueError(self.gemini_key_var + "environment variable not set.")
        self.logger = logger
        self.client = genai.Client(api_key = self.GEMINI_API_KEY)
        self.model_name = model_name # @param ["gemini-1.5-flash-latest","gemini-2.0-flash-lite","gemini-2.0-flash","gemini-2.5-flash-preview-04-17","gemini-2.5-pro-exp-03-25"] {"allow-input":true}
        self.initial_prompt = """
            You are controlling a robot that has a camera. You can see the world through the robot's camera.
            You will be asked to find objects the robot sees and return their bounding boxes.
            You will be given a prompt that describes the object to find.
            If the object is found in the image provided, return its name and bounding box.
            If the object is not found in the image, call the turn_robot_camera function with the following arguments:
                - amount_to_turn: The number of degrees to turn the camera (make the value 30 degrees).
                - direction: The direction to turn the camera (make the value "counterclockwise").
            This function will return a JSON response with:
            - image: new image of what the robot sees after it turns.
            - current_angle: current amount the robot has turned in degrees with respect to start_angle
            - at_start_angle: True if turning the robot brings it back to the starting angle, false to turn further.
                              If True, indicate that the object is not found and do not turn the robot camera further.
            Rules:
            1. Return bounding boxes as a JSON array with the following format:
                - label: The name of the object.
                - bbox: The bounding box coordinates in the format [x, y, width, height].
            2. Never return masks or code fencing.
            3. Limit to 10 objects.
            4. If an object is present multiple times, name them according to their unique characteristic (colors, size, position, unique characteristics, etc..).

        """
        self.safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH",
            ),
        ]
        
    def call_with_functions(self, prompt, image, function_list):
        """
        Call the Gemini API with a prompt and an image, and return the response.
        Args:
            prompt: The text prompt from the user.
            image: The image data as a PNG encoded byte array.
            function_list: A list of functions to be used in the API call.
        Returns:
            A dictionary containing the function call, arguments, and text response.
            function_call: The function call made by the model.
            args: The arguments passed to the function.
            function_name: The name of the function called.
            text: The text response from the model.   
        """
        self.contents = [ types.Content(role = "user", parts = [ types.Part(text = prompt) ]) ]
        image_part = types.Part.from_bytes(data=image, mime_type="image/png")
        self.contents.append(types.Content(role="user", parts = [image_part]))
        tools = self.convert_functions_to_gemini_tools(function_list)
        result = { }
        try:
            self.config = types.GenerateContentConfig(
                    system_instruction = self.initial_prompt,
                    safety_settings = self.safety_settings,
                    tools = tools,
                    automatic_function_calling = types.AutomaticFunctionCallingConfig(disable = True),
                )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=self.contents,
                config=self.config
            )
        except Exception as e:
            self.logger.error(f"Genmini call failed: {str(e)}")
            result["status"] = "ERROR: " + str(e)
            return result
        parts = response.candidates[0].content.parts
        for part in parts:
            if part.function_call:
                result["function_call"] =  part.function_call
                result["args"] = part.function_call.args
                result["function_name"] = part.function_call.name
            if part.text:
                text_part = part.text
                result["text"] = text_part
        return result
        
    def call_with_function_response(self, function_call, function_result, image):
        """
        Call the Gemini API with a function call and its result, and return the response.  
        Args:
            function_call: The function call made by the model.
            function_result: The result of the function call.
            image: The image data as a PNG encoded byte array.
            Returns:                
                Response from the Gemini API after executing the function call.
                This should be a list of bounding boxes and labels of the objects found
                or a message indicating that the object was not found.
        """
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
        try:
            final_response = self.client.models.generate_content(
                model=self.model_name,
                config=self.config,
                contents=self.contents,
            )
            return final_response
        except Exception as e:
            self.logger.error(f"Genmini call failed: {str(e)}")
            return { "text" : "ERROR: " + str(e) }

    def convert_function_to_gemini_tool(self, function):
        """
        Convert a function description to a Gemini Tool.
        Args:
            function: A dictionary containing the function name and description.
        Returns:
            A Gemini Tool object containing the function declaration.
        """ 
        func_decl = types.FunctionDeclaration(
            name = function["name"],
            description = function["description"])
        tool = types.Tool(function_declarations = [func_decl])
        return tool
    
    def convert_functions_to_gemini_tools(self, function_list):
        """
        Convert a list of function descriptions to Gemini Tools.
        Args:
            function_list: A list of dictionaries containing function names and descriptions.
            Returns:
                A list of Gemini Tool objects containing the function declarations.
        """
        tools = []
        for function in function_list:
            tool = self.convert_function_to_gemini_tool(function)     
            tools.append(tool)
        return tools

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






