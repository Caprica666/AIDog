
import os

class LLMClient:
    """
    A class to interact with the LLM API.
    """
    def __init__(self, logger, api_key_name, model_name):
        self.api_key_var = api_key_name
        self.API_KEY = os.getenv(self.api_key_var)
        if (self.API_KEY is None):
            raise ValueError(self.api_key_var + "environment variable not set.")
        if model_name is None:
            raise ValueError("Model name must be specified.")
        self.logger = logger
        self.model_name = model_name
        self.client = None
        self.initial_prompt = None
        
    def start_client(self):
        """
        Start the AI client.
        This method should be overridden in subclasses to initialize the client.
        """
        raise NotImplementedError("start_client must be overridden in a subclass.") 
        
    def set_tools(self, tool_list):
        """
        Set the tools for the AI client.
        Args:
            tool_list: A list of tools to be used by the AI client.
        """
        self.tools = tool_list
        
    def set_initial_prompt(self, prompt):
        """
        Set the initial prompt for the AI client
        Args:
            prompt: The initial prompt to be used by the AI client.
        """
        self.initial_prompt = prompt
        
    def call_llm(self, prompt, function_info):
        """
        Call the LLM API with a prompt and return the response.
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
        raise NotImplementedError("call_llm must be overridden in a subclass.")
    






