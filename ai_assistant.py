import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Gemini API kalitini sozlash
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Model: gemini-1.5-flash
model = genai.GenerativeModel('gemini-1.5-flash')

def clean_html_response(text):
    """
    Telegram HTML xatolarini oldini olish uchun matnni tozalash.
    """
    if not text:
        return ""
    # Ortiqcha markdown belgilari va kod bloklarini olib tashlash
    text = text.replace('`html', '').replace('```', '').replace('`', '').strip()
    return text

async def generate_ai_ad(file_name, cat, grade, quarter):
    """
    Fayl ma'lumotlari asosida reklama matni yaratish
    """
    try:
        prompt = (
            f"Fayl nomi: {file_name}\n"
            f"Kategoriya: {cat}\n"
            f"Sinf: {grade}\n"
            f"Chorak: {quarter}\n\n"
            f"Vazifa: @ish_reja_uz kanali uchun o'zbek tilida qisqa HTML reklama yoz. "
            f"Faqat <b>, <i> teglari bo'lsin. Tushuntirish berma."
        )
        
        # Asinxron so'rov
        response = await model.generate_content_async(prompt)
        cleaned_text = clean_html_response(response.text)
        
        return cleaned_text, None
    except Exception as e:
        print(f"AI Ad Error: {e}")
        return f"📝 <b>Fayl:</b> {file_name}\n✅ @ish_reja_uz kanali uchun.", None

async def ai_consultant(message_text):
    """
    Metodik yordamchi bilan suhbat
    """
    try:
        prompt = (
            f"Siz @ish_reja_uz metodik yordamchisisiz. "
            f"O'zbek tilida xushmuomala javob bering.\n\n"
            f"Savol: {message_text}"
        )
        
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"AI Consultant Error: {e}")
        return "Hozirda AI bilan bog'lanishda muammo bor."
