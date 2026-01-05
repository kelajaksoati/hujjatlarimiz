import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# API kalitini sozlash
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    
    # MUHIM: Model nomini 'models/gemini-1.5-flash' ko'rinishida yozamiz
    # Bu 404 API v1beta xatosini bartaraf etadi
    model = genai.GenerativeModel('models/gemini-1.5-flash')
else:
    model = None
    print("XATO: GEMINI_API_KEY topilmadi!")

async def generate_ai_ad(file_name, cat, grade, quarter):
    if not model: return f"Fayl: {file_name}", None
    try:
        prompt = f"Fayl: {file_name}, Bo'lim: {cat}. Jozibali reklama yoz."
        response = await model.generate_content_async(prompt)
        return response.text.strip(), None
    except Exception as e:
        return f"📝 Fayl: {file_name}", None

async def ai_consultant(message_text):
    if not model: return "AI kaliti sozlanmagan."
    try:
        prompt = f"Siz @ish_reja_uz yordamchisisiz. Savol: {message_text}"
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        # Loglarda xatoni ko'rish uchun
        print(f"AI Error: {e}")
        return "Hozirda AI xizmati ulanishda xato bermoqda."
