import asyncio, os, re
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

from database import Database
from processor import add_watermark
from ai_assistant import generate_ai_ad

load_dotenv()
db = Database()
bot = Bot(token=os.getenv("BOT_TOKEN"), default_bot_properties={"parse_mode": "HTML"})
dp = Dispatcher()

class BotStates(StatesGroup):
    waiting_for_action = State()
    ai_chat = State()

# --- Tugmalar ---
def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📂 Fayllar Mundarijasi"), KeyboardButton(text="🤖 AI Xizmati")],
        [KeyboardButton(text="📈 Statistika"), KeyboardButton(text="⚙️ Sozlamalar")]
    ], resize_keyboard=True)

def catalog_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📚 Boshlang'ich sinflar"), KeyboardButton(text="🎓 Yuqori sinflar")],
        [KeyboardButton(text="📝 BSB va CHSB"), KeyboardButton(text="🔙 Orqaga")]
    ], resize_keyboard=True)

def ai_service_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💬 AI bilan suhbat"), KeyboardButton(text="🛡 Faylga muhr bosish")],
        [KeyboardButton(text="📝 Imtihon javoblari"), KeyboardButton(text="🔙 Orqaga")]
    ], resize_keyboard=True)

# --- Mundarija Generator ---
@dp.message(F.text == "📚 Boshlang'ich sinflar")
async def send_primary_catalog(message: Message):
    files = db.get_files("Boshlang'ich")
    quarter = db.cursor.execute("SELECT value FROM settings WHERE key='quarter'").fetchone()[0]
    
    text = f"<b>FANLARDAN {quarter.upper()} ISH REJALARI (1-4 sinf)</b>\n\n"
    if not files:
        text += "Hozircha fayllar mavjud emas."
    else:
        for f_name, grade, link in files:
            text += f"📚 {f_name} — <a href='{link}'>YUKLAB OLISH</a>\n"
    
    text += f"\n✅ Kanalga obuna bo'ling: @{os.getenv('CHANNEL_USERNAME')}"
    await message.answer(text, disable_web_page_preview=True)

# --- Fayl Yuklash va Admin Amallari ---
@dp.message(F.document)
async def handle_doc(message: Message, state: FSMContext):
    file_path = f"downloads/{message.document.file_name}"
    await bot.download(message.document, destination=file_path)
    await state.update_data(file_path=file_path, original_name=message.document.file_name)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏷 User qo'shish", callback_data="add_user")],
        [InlineKeyboardButton(text="🛡 Muhr bosish", callback_data="add_watermark")],
        [InlineKeyboardButton(text="🚀 Kanalga yuborish", callback_data="send_to_chan")]
    ])
    await message.answer(f"Fayl qabul qilindi: {message.document.file_name}\nAmalni tanlang:", reply_markup=kb)

@dp.callback_query(F.data == "add_user")
async def cb_add_user(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    old_path = data['file_path']
    new_name = f"@{os.getenv('CHANNEL_USERNAME')}_{data['original_name']}"
    new_path = f"downloads/{new_name}"
    os.rename(old_path, new_path)
    await state.update_data(file_path=new_path)
    await call.answer("Kanal useri qo'shildi!")
    await call.message.edit_text(f"✅ Yangi nom: {new_name}")

# --- AI Suhbat ---
@dp.message(F.text == "💬 AI bilan suhbat")
async def start_ai_chat(message: Message, state: FSMContext):
    await message.answer("Siz AI metodik yordamchi bilan suhbat rejimiga o'tdingiz. Savolingizni yozing:")
    await state.set_state(BotStates.ai_chat)

@dp.message(BotStates.ai_chat)
async def ai_process(message: Message):
    # Bu yerda AI model chaqiriladi (masalan generate_ai_ad funksiyasi kabi)
    await message.answer("🤖 Metodik tahlil: Savolingiz bo'yicha 2-chorak rejalarida yangi DTS standartlari qo'llanilishi shart...")

# --- Tozalash ---
@dp.message(F.text == "⚙️ Sozlamalar")
async def settings(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 Xotirani tozalash", callback_data="clear_files")],
        [InlineKeyboardButton(text="🧨 Bazani o'chirish", callback_data="clear_db")]
    ])
    await message.answer("Tizim sozlamalari:", reply_markup=kb)

@dp.callback_query(F.data == "clear_files")
async def clear_fs(call: CallbackQuery):
    for f in os.listdir("downloads"):
        os.remove(os.path.join("downloads", f))
    await call.answer("Server xotirasi tozalandi!")

async def main():
    # Render uchun port binding va botni ishga tushirish mantiqi
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
