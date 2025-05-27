
from google import genai
from google.genai import types
from llm_connection import LLMClient

class GeminiClient(LLMClient):
    """
    A class to interact with the Gemini API for object detection and bounding box generation.
    Sets up the initial prompt and safety settings for the Gemini model."""
    def __init__(self, logger, model_name = "gemini-2.5-pro-preview-05-06"):
        super().__init__(logger, "GEMINI_API_KEY", model_name)
        self.safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH",
            ),
        ]
        
    def set_initial_prompt(self, prompt):
        super().set_initial_prompt(prompt)
        
    def start_client(self):
        self.client = genai.Client(api_key = self.API_KEY)
        
    def set_tools(self, function_list):
        super().set_tools(self.convert_functions_to_gemini_tools(function_list))
        
    def call_llm(self, prompt, function_info):
        """
        Call the Gemini API with a prompt and an image, and return the response.
        Args:
            prompt: The text prompt from the user.
            function_call: The function that Gemini indicated should be called (or None)
            function_response: The response from the function call (or None)
        Returns:
            A dictionary containing the function call, arguments, and text response.
            function_call: The function call made by the model.
            args: The arguments passed to the function.
            function_name: The name of the function called.
            text: The text response from the model.   
        """       
        if function_info:
            function_call_part = types.Part.from_function_call(
                name = function_info["name"],
                args = function_info["arguments"]
            )
            self.contents.append(types.Content(role = "model", parts = [ function_call_part ]))
            function_response_part = types.Part.from_function_response(
                name = function_info["name"],
                response = function_info["function_output"])
            # Append result of the function execution to contents
            self.contents.append(types.Content(role = "user", parts = [ function_response_part ]))
        else:
            self.contents = [ types.Content(role = "user", parts = [ types.Part(text = prompt) ]) ]        
        result = { }
        try:
            self.config = types.GenerateContentConfig(
                    system_instruction = self.initial_prompt,
                    safety_settings = self.safety_settings,
                    tools = self.tools,
                    automatic_function_calling = types.AutomaticFunctionCallingConfig(disable = True),
                )
            response = self.client.models.generate_content(
                model = self.model_name,
                contents = self.contents,
                config = self.config
            )
        except Exception as e:
            self.logger.error(f"Gemini call failed: {str(e)}")
            result["status"] = "ERROR: " + str(e)
            return result
        parts = response.candidates[0].content.parts
        function_info = None
        for part in parts:
            if part.function_call:
                function_info = { "name" : part.function_call.name, "arguments" : part.function_call.args }
                result["args"] = part.function_call.args
                result["function_name"] = part.function_call.name
            if part.text:
                text_part = part.text
                result["text"] = text_part
        return result, function_info
        
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






