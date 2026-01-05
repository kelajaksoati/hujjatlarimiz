import asyncio, os, re
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

# Modullaringiz
from database import Database
from processor import add_watermark, rename_file, create_lesson_template
from ai_assistant import generate_ai_ad, ai_consultant

load_dotenv()

# --- Kerakli papkalarni yaratish ---
for folder in ["downloads", "templates"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

db = Database()
bot = Bot(
    token=os.getenv("BOT_TOKEN"), 
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

SUPER_ADMIN = int(os.getenv("ADMIN_ID", 0))
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_USERNAME = (os.getenv("CHANNEL_USERNAME") or "ish_reja_uz").replace("@", "")

class BotStates(StatesGroup):
    ai_chat = State()
    waiting_for_template_data = State()
    setting_quarter = State() # Chorakni sozlash uchun holat

# --- Tugmalar ---
def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📂 Fayllar Mundarijasi"), KeyboardButton(text="🤖 AI Xizmati")],
        [KeyboardButton(text="⚙️ Sozlamalar")]
    ], resize_keyboard=True)

def catalog_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📚 Boshlang'ich (1-4)"), KeyboardButton(text="🎓 Yuqori (5-11)")],
        [KeyboardButton(text="📝 BSB va CHSB"), KeyboardButton(text="🔙 Orqaga")]
    ], resize_keyboard=True)

def ai_service_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💬 AI bilan suhbat"), KeyboardButton(text="📝 Shablon yaratish")],
        [KeyboardButton(text="📝 Imtihon javoblari"), KeyboardButton(text="🔙 Orqaga")]
    ], resize_keyboard=True)

# --- 1. Mundarija Generator ---
@dp.message(F.text.in_(["📚 Boshlang'ich (1-4)", "🎓 Yuqori (5-11)", "📝 BSB va CHSB"]))
async def send_dynamic_catalog(message: Message):
    cat_map = {
        "📚 Boshlang'ich (1-4)": "Boshlang'ich",
        "🎓 Yuqori (5-11)": "Yuqori",
        "📝 BSB va CHSB": "BSB_CHSB"
    }
    category = cat_map.get(message.text)
    files = db.get_catalog(category)
    quarter = db.get_quarter() or "2-CHORAK"
    
    text = (
        f"<b>FANLARDAN {quarter} EMAKTAB.UZ TIZIMIGA YUKLASH UCHUN OʻZBEK MAKTABLARGA "
        f"2025-2026 OʻQUV YILI ISH REJALARI</b>\n\n"
        f"✅Oʻzingizga kerakli boʻlgan reja ustiga bosing va yuklab oling.\n\n"
    )

    if files:
        for name, link in files:
            text += f"📚 {name} — <a href='{link}'>YUKLAB OLISH</a>\n"
    else:
        text += "<i>Hozircha bu bo'limda fayllar yuklanmagan.</i>\n"

    text += (
        f"\n\n#taqvim_mavzu_reja\n"
        f"✅Kanal: @{CHANNEL_USERNAME}"
    )
    await message.answer(text, disable_web_page_preview=True)

# --- 2. Sozlamalar (Chorakni o'zgartirish) ---
@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_panel(message: Message):
    if message.from_user.id != SUPER_ADMIN:
        return await message.answer("Ushbu bo'lim faqat adminlar uchun.")
    
    current_q = db.get_quarter() or "Aniq emas"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Chorakni o'zgartirish", callback_data="change_quarter")],
        [InlineKeyboardButton(text="Statistika", callback_data="show_stats")]
    ])
    await message.answer(f"⚙️ <b>Sozlamalar paneli</b>\n\nJoriy chorak: <b>{current_q}</b>", reply_markup=kb)

@dp.callback_query(F.data == "change_quarter")
async def cb_change_q(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Yangi chorak nomini yozing (Masalan: 3-CHORAK):")
    await state.set_state(BotStates.setting_quarter)

@dp.message(BotStates.setting_quarter)
async def process_new_quarter(message: Message, state: FSMContext):
    db.set_quarter(message.text.upper()) # database.py da bu funksiya bo'lishi kerak
    await message.answer(f"✅ Chorak muvaffaqiyatli o'zgartirildi: {message.text.upper()}", reply_markup=main_menu())
    await state.clear()

# --- 3. Imtihon Javoblari (AI Yordami) ---
@dp.message(F.text == "📝 Imtihon javoblari")
async def exam_answers(message: Message):
    text = (
        "<b>📝 Imtihon javoblari va metodik yordam</b>\n\n"
        "Sizga kerakli bo'lgan sinf va fan imtihon savollarini AI orqali yechishimiz mumkin. "
        "Yoki tayyor bazadan qidirish uchun admin bilan bog'laning.\n\n"
        "<i>AI dan foydalanish uchun 'AI bilan suhbat' bo'limiga o'ting.</i>"
    )
    await message.answer(text)

# --- 4. Shablon yaratish (Word) ---
@dp.message(F.text == "📝 Shablon yaratish")
async def start_tpl(message: Message, state: FSMContext):
    await message.answer("<b>Word shablon yaratish</b>\n\nMa'lumotni kiriting:\n<code>Ism, Fan, Sinf</code>")
    await state.set_state(BotStates.waiting_for_template_data)

@dp.message(BotStates.waiting_for_template_data)
async def create_tpl_file(message: Message, state: FSMContext):
    try:
        parts = message.text.split(",")
        if len(parts) < 3:
            return await message.answer("⚠️ Namuna: <i>Ali Valiyev, Tarix, 7-sinf</i>")
        
        file_path = create_lesson_template(parts[0].strip(), parts[1].strip(), parts[2].strip())
        await message.answer_document(FSInputFile(file_path), caption="✅ Shablon tayyor!")
        os.remove(file_path)
    except Exception as e:
        await message.answer(f"Xato: {e}")
    finally:
        await state.clear()

# --- Navigatsiya ---
@dp.message(F.text == "📂 Fayllar Mundarijasi")
async def show_cats(message: Message): await message.answer("Bo'limni tanlang:", reply_markup=catalog_menu())

@dp.message(F.text == "🤖 AI Xizmati")
async def show_ai(message: Message): await message.answer("AI xizmatlari:", reply_markup=ai_service_menu())

@dp.message(F.text == "🔙 Orqaga")
async def go_back(message: Message): await message.answer("Asosiy menyu", reply_markup=main_menu())

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(f"Xush kelibsiz @{CHANNEL_USERNAME} admin paneli!", reply_markup=main_menu())

# --- Server qismi ---
async def main():
    port = int(os.environ.get("PORT", 10000))
    try:
        await asyncio.start_server(lambda r, w: None, '0.0.0.0', port)
    except: pass
    print("🚀 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
