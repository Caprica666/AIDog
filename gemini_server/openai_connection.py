import os
from openai import OpenAI
import json

class OpenAIClient:
    """
    A class to interact with the OpenAI API for object detection and bounding box generation.
    Mimics the GeminiClient interface for compatibility.
    """
    def __init__(self, logger, model_name="gpt-4o-mini"):
        self.openai_key_var = "OPENAI_API_KEY"
        self.OPENAI_API_KEY = os.getenv(self.openai_key_var)
        if self.OPENAI_API_KEY is None:
            raise ValueError(self.openai_key_var + " environment variable not set.")
        self.logger = logger
        self.model_name = model_name
        self.client = OpenAI(api_key = self.OPENAI_API_KEY)
        self.initial_prompt = None
        self.contents = []

    def set_initial_prompt(self, prompt):
        self.initial_prompt = prompt

    def call_with_functions(self, prompt, function_list, function_info):
        """
        Call the OpenAI API with a prompt and optional function call/response.
        Args:
            prompt: The text prompt from the user.
            function_list: A list of functions to be used in the API call.
            function_name: The function that OpenAI indicated should be called (or None)
            function_response: The response from the function call (or None)
        Returns:
            A dictionary containing the function call, arguments, and text response.
        """
        messages = []
        if self.initial_prompt:
            messages.append({"role": "system", "content": self.initial_prompt})
        if function_info:
            messages.append({
                "type": "function_call",
                "id": function_info["id"],
                "call_id": function_info["call_id"],
                "name": function_info["name"],
                "arguments" : function_info["arguments"]
            })
            messages.append({
                "type": "function_call_output",
                "call_id": function_info["call_id"],
                "output": function_info["function_output"]
            })
        else:
            messages.append({"role": "user", "content": prompt})

        tools = self.convert_functions_to_openai_tools(function_list)
        result = {}
        try:
            response = self.client.responses.create(
                model = self.model_name,
                input = messages,
                tools = tools
            )
        except Exception as e:
            self.logger.error(f"OpenAI call failed: {str(e)}")
            result["status"] = "ERROR: " + str(e)
            return result
        tool_call = response.output[0]
        if hasattr(tool_call, "call_id"):
            result["args"] = json.loads(tool_call.arguments)
            result["function_name"] = tool_call.name
        else:
            tool_call = None
            result["text"] = response.output[0]
        return result, tool_call

    def convert_function_to_openai_tools(self, function):
        """
        Convert a function description to an OpenAI tool format.
        Args:
            function: A dictionary containing the function name and description.
        Returns:
            A dictionary in OpenAI tool format.
        """
        return {
            "type": "function",
            "name": function["name"],
            "description": function["description"],
            "parameters": function.get("parameters", {})
        }

    def convert_functions_to_openai_tools(self, function_list):
        """
        Convert a list of function descriptions to OpenAI tool format.
        Args:
            function_list: A list of dictionaries containing function names and descriptions.
        Returns:
            A list of OpenAI tool dictionaries.
        """
        return [self.convert_function_to_openai_tools(f) for f in function_list]
