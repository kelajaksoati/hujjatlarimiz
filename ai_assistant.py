import os
import google.generativeai as genai

# API kalitini olish
api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    # REST transporti Render va boshqa Cloud platformalarda gRPC bloklanishini oldini oladi
    genai.configure(api_key=api_key, transport='rest')
    # Modelni aniq 'models/' prefiksi bilan chaqiramiz
    model = genai.GenerativeModel('models/gemini-1.5-flash')
else:
    model = None
    print("⚠️ DIQQAT: GEMINI_API_KEY topilmadi!")

async def generate_ai_ad(file_name, cat, grade, quarter):
    """
    Fayl uchun kanalga reklama matni yaratadi.
    """
    if not model: 
        return f"<b>📚 {file_name}</b>\n✅ @ish_reja_uz kanali uchun tayyorlandi!", None
        
    try:
        prompt = (
            f"Fayl nomi: {file_name}\nKategoriya: {cat}\nSinf: {grade}\nChorak: {quarter}\n\n"
            f"Vazifa: @ish_reja_uz kanali uchun qisqa va jozibali HTML reklama yoz. "
            f"Faqat <b> va <i> teglaridan foydalan. Tushuntirish berma."
        )
        
        response = await model.generate_content_async(
            contents=prompt,
            generation_config={"temperature": 0.8}
        )
        
        # Markdown kod bloklarini tozalash
        text = response.text.replace('```html', '').replace('```', '').replace('`', '').strip()
        return text, None
        
    except Exception as e:
        print(f"AI Ad Generation Error: {e}")
        # AI ishlamay qolganda qaytadigan standart reklama
        return f"<b>📚 {file_name}</b>\n\n✅ Yangi ish rejasi kanalga yuklandi!\n📍 Kanalimiz: @ish_reja_uz", None

async def ai_consultant(query):
    """
    Metodik yordamchi bilan suhbat funksiyasi (Zaxira varianti bilan).
    """
    if not model: 
        return "⚠️ AI xizmati sozlanmagan. Iltimos, API kalitni tekshiring."
        
    try:
        # Tizim ko'rsatmasini (system prompt) savolga qo'shamiz
        full_prompt = (
            f"Siz @ish_reja_uz metodik yordamchisisiz. "
            f"O'zbek tilida xushmuomala javob bering.\n\nSavol: {query}"
        )
        
        # Asinxron murojaat (Render uchun xavfsiz)
        response = await model.generate_content_async(
            contents=full_prompt,
            generation_config={"temperature": 0.7}
        )
        return response.text
        
    except Exception as e:
        print(f"AI Error: {e}")
        # AI ishlamasa yoki xato bersa qaytadigan standart xavfsiz javob
        return ("Hozirda AI xizmati vaqtincha band. Iltimos, birozdan so'ng urinib ko'ring "
                "yoki metodik yordam uchun admin bilan bog'laning.")
