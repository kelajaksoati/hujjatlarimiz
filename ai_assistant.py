import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

async def generate_ai_ad(file_name, grade, quarter):
    """Fayl uchun jozibali reklama va spoilerli matn yaratadi"""
    prompt = f"Fayl: {file_name}, Sinf: {grade}, Chorak: {quarter}. Telegram kanal uchun HTML formatda reklama yoz."
    response = model.generate_content(prompt)
    return response.text

async def ai_consultant(question):
    """Adminlar bilan metodik suhbat va imtihon javoblari"""
    prompt = f"Siz @ish_reja_uz botining metodik yordamchisisiz. Savol: {question}"
    response = model.generate_content(prompt)
    return response.text
