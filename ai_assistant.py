import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

async def generate_ai_ad(file_name, cat, grade, quarter):
    prompt = f"Fayl: {file_name}, Bo'lim: {cat}, Sinf: {grade}, Chorak: {quarter}. @ish_reja_uz kanali uchun jozibali HTML reklama yoz."
    response = model.generate_content(prompt)
    return response.text, None

async def ai_chat_assistant(message_text):
    prompt = f"Siz @ish_reja_uz metodik yordamchisisiz. Admin savoli: {message_text}"
    response = model.generate_content(prompt)
    return response.text
