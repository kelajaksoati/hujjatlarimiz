import os
import google.generativeai as genai

# API kalitini bevosita tizimdan olamiz (Render'da sozlangan bo'lishi shart)
api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    # REST transporti Render'da barqaror ishlaydi
    genai.configure(api_key=api_key, transport='rest')
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

async def generate_ai_ad(file_name, cat, grade, quarter):
    if not model: return f"Fayl: {file_name}", None
    try:
        prompt = f"{file_name} uchun @ish_reja_uz kanaliga HTML reklama yoz."
        response = await model.generate_content_async(prompt)
        return response.text.replace('`html', '').replace('```', '').strip(), None
    except:
        return f"<b>Fayl:</b> {file_name}\n✅ Tayyor!", None

async def ai_consultant(message_text):
    if not model: return "AI sozlanmagan."
    try:
        response = await model.generate_content_async(message_text)
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return "Hozirda AI xizmati ulanishda xato bermoqda."
