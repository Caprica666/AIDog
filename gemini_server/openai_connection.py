import os
from openai import OpenAI

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
        self.client = OpenAI()
        
    def set_initial_prompt(self, prompt):
        self.initial_prompt = prompt

    def call_with_functions(self, prompt, image, function_list):
        """
        Call the OpenAI API with a prompt and an image, and return the response.
        Args:
            prompt: The text prompt from the user.
            function_list: A list of functions to be used in the API call (not used in OpenAI API, but kept for compatibility).
        Returns:
            A dictionary containing the function call, arguments, and text response.
        """
        # Encode image as base64 for OpenAI API
        user_prompt =  { "role": "user", "content": { "type": "input_text", "text": prompt } }
        system_prompt =  { "role": "system", "content": { "type": "input_text", "text": self.initial_prompt } }
        self.prompt = [ system_prompt, user_prompt ]
        input = [ system_prompt, user_prompt ]
    
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

    def call_with_function_response(self, function_call, function_result):
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