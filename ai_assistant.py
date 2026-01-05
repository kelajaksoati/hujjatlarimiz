import os
import re
import google.generativeai as genai
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Gemini API kalitini sozlash
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Model nomini yangilaymiz: 'gemini-1.5-flash' eng barqaror va tezkor variant
model = genai.GenerativeModel('gemini-1.5-flash')

def clean_html_response(text):
    """
    AI qaytargan matndan Markdown belgilarini (
    va Telegram HTML formati uchun tozalaydi.
    """
    # 
html ... ``` yoki ``` ...
    text = re.sub(r'
(?:html)?', '', text)
    text = text.replace('`', '').strip()
    return text

async def generate_ai_ad(file_name, cat, grade, quarter):
    """
    Fayl ma'lumotlari asosida jozibali reklama matni yaratish
    """
    try:
        prompt = (
            f"Fayl nomi: {file_name}\n"
            f"Kategoriya: {cat}\n"
            f"Sinf: {grade}\n"
            f"Chorak: {quarter}\n\n"
            f"Vazifa: @ish_reja_uz kanali uchun o'zbek tilida qisqa va jozibali reklama yoz. "
            f"Telegram HTML formatidan (<b>, <i>, <a>) foydalan. "
            f"Faqat reklama matnini qaytar, tushuntirish berma."
        )
        
        # AI dan javob olish
        response = await model.generate_content_async(prompt)
        cleaned_text = clean_html_response(response.text)
        
        return cleaned_text, None
    except Exception as e:
        print(f"DEBUG (generate_ai_ad xatosi): {e}")
        return f"📝 <b>Fayl:</b> {file_name}\n✅ Tayyor, kanalga yuklash mumkin!", None

async def ai_consultant(message_text):
    """
    Metodik yordamchi bilan suhbat rejimi
    """
    try:
        prompt = (
            f"Siz @ish_reja_uz kanalining aqlli metodik yordamchisisiz. "
            f"O'qituvchilarga dars ishlanmalari va metodika bo'yicha yordam berasiz. "
            f"O'zbek tilida xushmuomala javob bering.\n\n"
            f"Savol: {message_text}"
        )
        
        # AI dan javob olish
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        print(f"DEBUG (ai_consultant xatosi): {e}")
        return "Hozirda AI xizmati biroz band. Iltimos, keyinroq urinib ko'ring."
