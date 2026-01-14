import google.generativeai as genai
import os
from typing import Dict

class GeminiClient:
    """Direct Gemini API client (bypasses LangChain issues)"""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY not found in environment variables")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # List available models to find the right one
        try:
            print("🔍 Checking available Gemini models...")
            available_models = []
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    available_models.append(model.name)
            
            print(f"✅ Available models: {available_models[:3]}")
            
            # Use the first available model (usually gemini-pro or gemini-1.5-pro-latest)
            if available_models:
                # Try to use a gemini-1.5 model if available, otherwise fall back to gemini-pro
                model_name = None
                for m in available_models:
                    if 'gemini-1.5' in m or 'gemini-pro' in m:
                        model_name = m.replace('models/', '')
                        break
                
                if not model_name:
                    model_name = available_models[0].replace('models/', '')
                
                self.model = genai.GenerativeModel(model_name)
                print(f"✅ Using Gemini model: {model_name}")
            else:
                # Fallback to gemini-pro
                self.model = genai.GenerativeModel('gemini-pro')
                print("✅ Using fallback model: gemini-pro")
                
        except Exception as e:
            print(f"⚠️  Could not list models: {e}")
            print("✅ Using default model: gemini-pro")
            self.model = genai.GenerativeModel('gemini-pro')
    
    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text from prompt"""
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
            print(f"❌ Gemini API error: {e}")
            return f"Error generating content: {str(e)}"
    
    def generate_with_template(self, template: str, variables: Dict) -> str:
        """Generate using template (simple string formatting)"""
        try:
            # Format the template with variables
            formatted_prompt = template.format(**variables)
            return self.generate(formatted_prompt)
        except Exception as e:
            print(f"❌ Template generation error: {e}")
            return f"Error: {str(e)}"

# Global instance
llm_client = GeminiClient()
