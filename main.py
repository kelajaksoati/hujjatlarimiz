Tayyor! Barcha funksiyalarni, jumladan, 3-chorak sozlamalari va admin fayl yuklaganda kanalga avtomatik reklama bilan yuborish mantiqini yagona main.py fayliga jamladim.

Bu kod asinxron ma'lumotlar bazasi va Gemini AI bilan to'liq integratsiya qilingan.

🚀 Yakuniy va To'liq main.py
Python

import asyncio, os, re
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

# O'z modullaringiz
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
    setting_quarter = State()
    uploading_file = State()

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

# --- 1. Mundarija Generator (Dinamik Chorak bilan) ---
@dp.message(F.text.in_(["📚 Boshlang'ich (1-4)", "🎓 Yuqori (5-11)", "📝 BSB va CHSB"]))
async def send_dynamic_catalog(message: Message):
    cat_map = {
        "📚 Boshlang'ich (1-4)": "Boshlang'ich",
        "🎓 Yuqori (5-11)": "Yuqori",
        "📝 BSB va CHSB": "BSB_CHSB"
    }
    category = cat_map.get(message.text)
    
    quarter = await db.get_quarter()
    files = await db.get_catalog(category)
    
    text = (
        f"<b>FANLARDAN {quarter} EMAKTAB.UZ TIZIMIGA YUKLASH UCHUN OʻZBEK MAKTABLARGA "
        f"2025-2026 OʻQUV YILI ISH REJALARI</b>\n\n"
        f"✅Oʻzingizga kerakli boʻlgan reja ustiga bosing va yuklab oling.\n\n"
    )

    if files:
        for name, link in files:
            text += f"📚 {name} — <a href='{link}'>YUKLAB OLISH</a>\n"
    else:
        text += f"<i>Hozircha {quarter} uchun fayllar yuklanmagan. Tez orada qo'shiladi!</i>\n"

    text += f"\n\n#taqvim_mavzu_reja\n✅Kanal: @{CHANNEL_USERNAME}"
    await message.answer(text, disable_web_page_preview=True)

# --- 2. Admin uchun fayl yuklash va avtomatik reklama ---
@dp.message(F.document & F.from_user.id == SUPER_ADMIN)
async def handle_admin_upload(message: Message, state: FSMContext):
    file_id = message.document.file_id
    file_name = message.document.file_name
    file_path = f"downloads/{file_name}"
    
    await bot.download(message.document, destination=file_path)
    await state.update_data(file_path=file_path, file_name=file_name)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Boshlang'ich", callback_data="cat_Boshlang'ich")],
        [InlineKeyboardButton(text="Yuqori", callback_data="cat_Yuqori")],
        [InlineKeyboardButton(text="BSB/CHSB", callback_data="cat_BSB_CHSB")]
    ])
    await message.answer(f"📁 <b>{file_name}</b> qaysi bo'limga qo'shilsin?", reply_markup=kb)

@dp.callback_query(F.data.startswith("cat_"))
async def cb_finalize_send(call: CallbackQuery, state: FSMContext):
    category = call.data.split("_")[1]
    data = await state.get_data()
    quarter = await db.get_quarter()
    
    # AI reklama yaratadi
    ad_text, _ = await generate_ai_ad(data['file_name'], category, "Barcha", quarter)
    
    try:
        msg = await bot.send_document(CHANNEL_ID, FSInputFile(data['file_path']), caption=ad_text)
        file_link = f"https://t.me/{CHANNEL_USERNAME}/{msg.message_id}"
        await db.add_to_catalog(data['file_name'], category, file_link)
        await call.message.edit_text(f"🚀 Fayl {quarter} sarlavhasi bilan kanalga yuborildi va mundarijaga qo'shildi!")
    except Exception as e:
        await call.message.answer(f"❌ Xato: {e}")
    
    if os.path.exists(data['file_path']): os.remove(data['file_path'])
    await state.clear()

# --- 3. Sozlamalar (Chorakni o'zgartirish) ---
@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_panel(message: Message):
    if message.from_user.id != SUPER_ADMIN: return
    current_q = await db.get_quarter()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Chorakni o'zgartirish", callback_data="change_quarter")]
    ])
    await message.answer(f"⚙️ <b>Sozlamalar</b>\n\nJoriy davr: <b>{current_q}</b>", reply_markup=kb)

@dp.callback_query(F.data == "change_quarter")
async def cb_change_q(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Yangi chorak nomini yozing (Masalan: 3-CHORAK):")
    await state.set_state(BotStates.setting_quarter)

@dp.message(BotStates.setting_quarter)
async def process_new_quarter(message: Message, state: FSMContext):
    await db.set_quarter(message.text.upper()) 
    await message.answer(f"✅ Chorak o'zgartirildi: {message.text.upper()}", reply_markup=main_menu())
    await state.clear()

# --- 4. AI Xizmatlari va Shablon ---
@dp.message(F.text == "💬 AI bilan suhbat")
async def start_ai(message: Message, state: FSMContext):
    await message.answer("Savolingizni yozing (Chiqish: /cancel):")
    await state.set_state(BotStates.ai_chat)

@dp.message(BotStates.ai_chat)
async def handle_ai(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("Suhbat tugadi.", reply_markup=main_menu())
    res = await ai_consultant(message.text)
    await message.answer(res)

@dp.message(F.text == "📝 Shablon yaratish")
async def start_tpl(message: Message, state: FSMContext):
    await message.answer("Ma'lumotni kiriting:\n<code>Ism, Fan, Sinf</code>")
    await state.set_state(BotStates.waiting_for_template_data)

@dp.message(BotStates.waiting_for_template_data)
async def create_tpl_file(message: Message, state: FSMContext):
    try:
        parts = message.text.split(",")
        file_path = create_lesson_template(parts[0].strip(), parts[1].strip(), parts[2].strip())
        await message.answer_document(FSInputFile(file_path), caption="✅ Shablon tayyor!")
        os.remove(file_path)
    except:
        await message.answer("❌ Xato! Namuna: Ali Valiyev, Tarix, 7-sinf")
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
    await message.answer(f"Salom! @{CHANNEL_USERNAME} botiga xush kelibsiz.", reply_markup=main_menu())

# --- Server qismi ---
async def main():
    await db.create_tables() 
    port = int(os.environ.get("PORT", 10000))
    try:
        await asyncio.start_server(lambda r, w: None, '0.0.0.0', port)
    except: pass
    print("🚀 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
