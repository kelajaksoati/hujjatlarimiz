import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    FSInputFile, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

# O'zingiz yaratgan modullar
from database import Database
from processor import create_lesson_template

load_dotenv()

# Kerakli papkalar mavjudligini tekshirish
for folder in ["downloads", "templates"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Ma'lumotlar bazasi va Botni sozlash
db = Database()
bot = Bot(
    token=os.getenv("BOT_TOKEN"), 
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# Muhit o'zgaruvchilari
SUPER_ADMIN = int(os.getenv("ADMIN_ID", 0))
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_USERNAME = (os.getenv("CHANNEL_USERNAME") or "ish_reja_uz").replace("@", "")

class BotStates(StatesGroup):
    setting_quarter = State()
    waiting_for_template_data = State()

# --- Tugmalar (Keyboards) ---
def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📂 Fayllar Mundarijasi")],
        [KeyboardButton(text="📝 Shablon yaratish"), KeyboardButton(text="⚙️ Sozlamalar")]
    ], resize_keyboard=True)

def catalog_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📚 Boshlang'ich (1-4)"), KeyboardButton(text="🎓 Yuqori (5-11)")],
        [KeyboardButton(text="📝 BSB va CHSB"), KeyboardButton(text="🔙 Orqaga")]
    ], resize_keyboard=True)

# --- Mundarija Logic ---
@dp.message(F.text.in_(["📚 Boshlang'ich (1-4)", "🎓 Yuqori (5-11)", "📝 BSB va CHSB"]))
async def send_catalog(message: Message):
    cat_map = {
        "📚 Boshlang'ich (1-4)": "Boshlang'ich", 
        "🎓 Yuqori (5-11)": "Yuqori", 
        "📝 BSB va CHSB": "BSB_CHSB"
    }
    category = cat_map.get(message.text)
    files = await db.get_catalog(category)
    quarter = await db.get_quarter()
    
    text = f"<b>{quarter} UCHUN ISH REJALARI</b>\n\n"
    if files:
        for name, link in files:
            text += f"📚 {name} — <a href='{link}'>YUKLAB OLISH</a>\n"
    else:
        text += "<i>Hozircha bu bo'limda fayllar yuklanmagan.</i>"
    
    await message.answer(text, disable_web_page_preview=True)

# --- Admin: Fayl yuklash ---
@dp.message(F.document & (F.from_user.id == SUPER_ADMIN))
async def handle_upload(message: Message, state: FSMContext):
    file_path = f"downloads/{message.document.file_name}"
    await bot.download(message.document, destination=file_path)
    await state.update_data(file_path=file_path, file_name=message.document.file_name)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Boshlang'ich", callback_data="add_Boshlang'ich")],
        [InlineKeyboardButton(text="Yuqori", callback_data="add_Yuqori")],
        [InlineKeyboardButton(text="BSB/CHSB", callback_data="add_BSB_CHSB")]
    ])
    await message.answer(f"📁 <b>{message.document.file_name}</b> bo'limini tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("add_"))
async def finalize_upload(call: CallbackQuery, state: FSMContext):
    category = call.data.split("_")[1]
    data = await state.get_data()
    quarter = await db.get_quarter()
    
    caption = f"<b>📚 {data['file_name']}</b>\n\n✅ {quarter} dars rejasi tayyorlandi.\n📍 Kanal: @{CHANNEL_USERNAME}"
    
    # Kanalga yuborish
    msg = await bot.send_document(CHANNEL_ID, FSInputFile(data['file_path']), caption=caption)
    link = f"https://t.me/{CHANNEL_USERNAME}/{msg.message_id}"
    
    # Bazaga qo'shish
    await db.add_to_catalog(data['file_name'], category, link)
    
    await call.message.edit_text("✅ Kanalga yuborildi va mundarijaga qo'shildi!")
    
    # Vaqtincha faylni o'chirish
    if os.path.exists(data['file_path']):
        os.remove(data['file_path'])
    await state.clear()

# --- Sozlamalar ---
@dp.message(F.text == "⚙️ Sozlamalar")
async def settings(message: Message):
    if message.from_user.id != SUPER_ADMIN:
        return
    q = await db.get_quarter()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Chorakni o'zgartirish", callback_data="set_q")]
    ])
    await message.answer(f"⚙️ Sozlamalar\n\nJoriy davr: <b>{q}</b>", reply_markup=kb)

@dp.callback_query(F.data == "set_q")
async def start_set_q(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Yangi davr nomini kiriting (Masalan: 4-CHORAK):")
    await state.set_state(BotStates.setting_quarter)

@dp.message(BotStates.setting_quarter)
async def save_q(message: Message, state: FSMContext):
    await db.set_quarter(message.text.upper())
    await message.answer(f"✅ Yangilandi: {message.text.upper()}", reply_markup=main_menu())
    await state.clear()

# --- Shablon yaratish ---
@dp.message(F.text == "📝 Shablon yaratish")
async def tpl_start(message: Message, state: FSMContext):
    await message.answer("Ma'lumotlarni kiriting (Namuna: Ali Valiyev, Matematika, 5-sinf):")
    await state.set_state(BotStates.waiting_for_template_data)

@dp.message(BotStates.waiting_for_template_data)
async def tpl_done(message: Message, state: FSMContext):
    try:
        p = message.text.split(",")
        if len(p) < 3:
            raise ValueError("Ma'lumot yetarli emas")
            
        path = create_lesson_template(p[0].strip(), p[1].strip(), p[2].strip())
        await message.answer_document(FSInputFile(path), caption="✅ Shablon tayyor!")
        
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        await message.answer("❌ Xato! Iltimos, namunadagidek vergul bilan ajratib yozing.\nNamuna: Ali Valiyev, Tarix, 7-sinf")
    finally:
        await state.clear()

# --- Umumiy navigatsiya ---
@dp.message(F.text == "📂 Fayllar Mundarijasi")
async def cats(message: Message):
    await message.answer("Kategoriyani tanlang:", reply_markup=catalog_menu())

@dp.message(F.text == "🔙 Orqaga")
async def back(message: Message):
    await message.answer("Asosiy menyu", reply_markup=main_menu())

@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer("Xush kelibsiz! Kerakli bo'limni tanlang:", reply_markup=main_menu())

# --- Asosiy ishga tushirish ---
async def main():
    await db.create_tables()
    
    # Render uchun portni band qilish (Health Check uchun)
    port = int(os.environ.get("PORT", 10000))
    try:
        server = await asyncio.start_server(lambda r, w: None, '0.0.0.0', port)
        asyncio.create_task(server.serve_forever())
    except Exception as e:
        print(f"Port band qilishda xato: {e}")
        
    print("🚀 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot to'xtatildi")
