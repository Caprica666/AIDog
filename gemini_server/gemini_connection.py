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
        self.bounding_box_system_instructions = """
            Return bounding boxes as a JSON array with labels. Never return masks or code fencing. Limit to 10 objects.
            If an object is present multiple times, name them according to their unique characteristic (colors, size, position, unique characteristics, etc..).
            """
        self.safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH",
            ),
        ]
        
    def call_gemini_text(self, prompt, config: Optional[types.GenerateContentConfig] = None):
        """Call Gemini with text prompt and return text."""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents = [prompt],
            config = config
        )
        # Check output
        return response.text

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
    
    def convert_prompt_to_filename(self, user_prompt: str) -> str:
        """Convert a text prompt into a suitable filename.
        
        Args:
            prompt: The text prompt from the user
            
        Returns:
            A concise, descriptive filename generated based on the prompt
        """
        try:
            # Create a prompt for Gemini to generate a filename
            filename_prompt = f"""
            Based on this user prompt: "{user_prompt}"
            
            Generate a short, descriptive file name.
            The filename should:
            - Be concise (maximum 5 words)
            - Use underscores between words
            - Not include any file extension
            - Only return the filename, nothing else
            """
            
            # Call Gemini and get the filename
            filename = self.call_gemini_text(filename_prompt)
            self.logger.info(f"convert_prompt_to_filename: {filename}")
            
            # Return the filename only, without path or extension
            return filename
    
        except Exception as e:
            self.logger.error(f"Error generating filename with Gemini: {str(e)}")
            # Fallback to a simple filename if Gemini fails
            truncated_text = user_prompt[:12].strip()
            return f"image_{truncated_text}_{str(uuid.uuid4())[:8]}"






        