from google import genai
from google.genai import types
import os
from io import BytesIO

class GeminiClient:
    def __init__(self):
        GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        if (GEMINI_API_KEY is None):
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = "gemini-2.5-pro-exp-03-25" # @param ["gemini-1.5-flash-latest","gemini-2.0-flash-lite","gemini-2.0-flash","gemini-2.5-flash-preview-04-17","gemini-2.5-pro-exp-03-25"] {"allow-input":true}
        self.bounding_box_system_instructions = """
            Return bounding boxes as a JSON array with labels. Never return masks or code fencing. Limit to 25 objects.
            If an object is present multiple times, name them according to their unique characteristic (colors, size, position, unique characteristics, etc..).
            """
        self.safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH",
            ),
        ]

    # Find the objects in the image designated in the prompt.
    # The image is passed as a PNG encoded byte array.
    # The prompt is a string that describes the objects to find.
    def find_object(self, prompt, image):
        """Find objects in the image using Gemini API."""
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
        return response.text






        