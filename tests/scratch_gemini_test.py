import os
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

img = Image.open('debug_captcha_attempt_1.png')
model = genai.GenerativeModel('gemini-3.5-flash')
prompt = "Extract the text from this CAPTCHA image. Return ONLY the extracted alphanumeric characters, with NO spaces, NO punctuation, and NO markdown formatting. It is usually 6 uppercase letters and numbers."
response = model.generate_content([prompt, img])
print(f"Gemini output: '{response.text}'")
