import google.generativeai as genai
import os
import time
from typing import Dict

class GeminiClient:
    """Direct Gemini API client with free-tier safe selection and retry logic."""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 20  # seconds, if quota exceeded
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        
        # List models dynamically and pick a free-tier one
        try:
            print("🔍 Listing available Gemini models...")
            self.model_name = None
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    # Pick only free-tier models
                    if 'free' in model.description.lower() or 'gemini-2.5' in model.name:
                        self.model_name = model.name.replace('models/', '')
                        break
            
            if not self.model_name:
                raise Exception("No free-tier models available.")
            
            self.model = genai.GenerativeModel(self.model_name)
            print(f"✅ Using Gemini model: {self.model_name}")
            
        except Exception as e:
            print(f"⚠️ Could not list models: {e}")
            # fallback: use a safe known model
            self.model = genai.GenerativeModel('gemini-2.5-pro')
            print("✅ Using fallback model: gemini-2.5-pro (might hit quota)")

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text with retry if quota exceeded."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=2048,
                    )
                )
                return response.text
            except Exception as e:
                error_msg = str(e)
                if "quota" in error_msg.lower() or "429" in error_msg:
                    wait = self.RETRY_DELAY * attempt
                    print(f"⚠️ Quota exceeded, retrying in {wait}s (attempt {attempt})...")
                    time.sleep(wait)
                else:
                    print(f"❌ Gemini API error: {error_msg}")
                    return f"Error generating content: {error_msg}"
        return "⚠️ Failed: quota exceeded after retries"

    def generate_with_template(self, template: str, variables: Dict) -> str:
        """Generate using template (simple string formatting)"""
        try:
            formatted_prompt = template.format(**variables)
            return self.generate(formatted_prompt)
        except Exception as e:
            print(f"❌ Template generation error: {e}")
            return f"Error: {str(e)}"


# Global instance
llm_client = GeminiClient()
