import os
import sys
from google import genai
from dotenv import load_dotenv

class GoogleGenAIAdapter:
    def __init__(self, model_name: str = 'gemini-3-flash-preview'):
        load_dotenv()
        self.api_key = os.environ.get('GOOGLE_API_KEY')
        if not self.api_key:
            print("Critical Error: GOOGLE_API_KEY not found in environment.")
            sys.exit(1)
            
        # Suppress SDK warning if dual keys exist
        if os.environ.get('GEMINI_API_KEY'):
            del os.environ['GEMINI_API_KEY']
            
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

    def generate(self, prompt: str) -> str:
        """
        Generates content with basic error handling.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name, 
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"[LLM Error] {e}")
            return "ERROR"
