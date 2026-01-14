import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv('.env')
api_key = os.getenv('GEMINI_API_KEY')

print(f"🔑 API Key starts with: {api_key[:20]}...")

genai.configure(api_key=api_key)

print("\n📋 Available Gemini models:")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"  ✅ {model.name}")

# Test with gemini-pro
print("\n🧪 Testing gemini-pro model...")
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content("Say hello!")
print(f"Response: {response.text}")
