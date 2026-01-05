import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Gemini API kalitini sozlash
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

async def generate_ai_ad(file_name, cat, grade, quarter):
    """
    Fayl ma'lumotlari asosida reklama matni yaratish
    """
    try:
        prompt = f"Fayl: {file_name}, Bo'lim: {cat}, Sinf: {grade}, Chorak: {quarter}. @ish_reja_uz kanali uchun jozibali HTML reklama yoz."
        response = model.generate_content(prompt)
        return response.text, None
    except Exception as e:
        return f"Reklama yaratishda xatolik: {str(e)}", None

async def ai_consultant(message_text):
    """
    Metodik yordamchi bilan muloqot (main.py dagi nomga moslandi)
    """
    try:
        prompt = f"Siz @ish_reja_uz metodik yordamchisisiz. Admin savoli: {message_text}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI javob berishda xatolik yuz berdi: {str(e)}"
