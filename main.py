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

# --- Mundarija Generator (Siz xohlagan shablon bilan) ---
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
    
    # Asosiy matn shabloni
    text = (
        f"<b>FANLARDAN {quarter} EMAKTAB.UZ TIZIMIGA YUKLASH UCHUN OʻZBEK MAKTABLARGA "
        f"2025-2026 OʻQUV YILI ISH REJALARI</b>\n\n"
        f"✅Oʻzingizga kerakli boʻlgan reja ustiga bosing va yuklab oling. "
        f"Boshqalarga ham ulashishni unutmang.\n\n"
    )

    # Agar bazada fayllar bo'lsa, ularni chiqaradi
    if files:
        for name, link in files:
            text += f"📚 {name} — <a href='{link}'>YUKLAB OLISH</a>\n"
    else:
        # Fayllar yuklanmagan bo'lsa, standart fanlar ro'yxatini ko'rsatadi
        subjects = [
            "Alifbe 1-sinf", "Yozuv 1-sinf", "Oʻqish savodxonligi 1-4-sinf", "Adabiyot 5-11-sinf",
            "Biologiya 7-11-sinf", "Fizika 7-11-sinf", "Informatika 1-11-sinf", "Ingliz tili 1-11-sinf",
            "Matematika 1-7-sinf", "Algebra 8-11-sinf", "Geometriya 8-11-sinf", "Kelajak soati 1-11-sinf"
        ]
        for sub in subjects:
            text += f"📚 {sub}\n"
        text += "\n<i>Hozircha yuklab olish havolalari mavjud emas.</i>"

    text += (
        f"\n\n❗️OʻQITUVCHILARGA JOʻNATISHNI UNUTMANG❗️\n\n"
        f"#taqvim_mavzu_reja\n"
        f"✅Kanalga obuna bo‘lish:👇👇👇\n"
        f"https://t.me/{CHANNEL_USERNAME}"
    )
    
    await message.answer(text, disable_web_page_preview=True)

# --- Shablon yaratish (Word) ---
@dp.message(F.text == "📝 Shablon yaratish")
async def start_tpl(message: Message, state: FSMContext):
    await message.answer("<b>Word shablon yaratish</b>\n\nIltimos, ma'lumotni kiriting:\n"
                         "<code>Ism, Fan, Sinf</code> formatida.")
    await state.set_state(BotStates.waiting_for_template_data)

@dp.message(BotStates.waiting_for_template_data)
async def create_tpl_file(message: Message, state: FSMContext):
    try:
        parts = message.text.split(",")
        if len(parts) < 3:
            await message.answer("⚠️ Ma'lumot kam. Namuna: <i>Ali Valiyev, Tarix, 7-sinf</i>")
            return
        
        file_path = create_lesson_template(parts[0].strip(), parts[1].strip(), parts[2].strip())
        await message.answer_document(FSInputFile(file_path), caption="✅ Shablon tayyor!")
        os.remove(file_path)
    except Exception as e:
        await message.answer(f"Xato: {e}")
    finally:
        await state.clear()

# --- AI Suhbat ---
@dp.message(F.text == "💬 AI bilan suhbat")
async def start_ai(message: Message, state: FSMContext):
    await message.answer("Savolingizni yozing (Chiqish: /cancel):")
    await state.set_state(BotStates.ai_chat)

@dp.message(BotStates.ai_chat)
async def handle_ai(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Suhbat tugadi.", reply_markup=main_menu())
        return
    res = await ai_consultant(message.text)
    await message.answer(res)

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
