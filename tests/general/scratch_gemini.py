import os
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key loaded: {'Yes' if api_key else 'No'} (starts with {api_key[:4] if api_key else 'None'})")
genai.configure(api_key=api_key)

try:
    img = Image.new('RGB', (100, 30), color = (73, 109, 137)) # Create a dummy image
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(["Extract text", img])
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
