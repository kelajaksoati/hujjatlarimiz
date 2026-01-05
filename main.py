import asyncio, os, re
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

# Sizning modullaringiz
from database import Database
from processor import add_watermark, rename_file
from ai_assistant import generate_ai_ad, ai_consultant

# .env yuklash (Docker'da Environment Variables ishlatilsa ham zarar qilmaydi)
load_dotenv()

db = Database()
bot = Bot(
    token=os.getenv("BOT_TOKEN"), 
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# O'zgaruvchilar
# Render'da kiritgan Environment Variable larni o'qiydi
SUPER_ADMIN = int(os.getenv("ADMIN_ID", 0))
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_USERNAME = (os.getenv("CHANNEL_USERNAME") or "ish_reja_uz").replace("@", "")

class BotStates(StatesGroup):
    ai_chat = State()
    choosing_category = State()

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
        [KeyboardButton(text="💬 AI bilan suhbat"), KeyboardButton(text="📝 Imtihon javoblari")],
        [KeyboardButton(text="🔙 Orqaga")]
    ], resize_keyboard=True)

# --- Mundarija Generator ---
@dp.message(F.text.contains("Boshlang'ich"))
async def send_primary_catalog(message: Message):
    files = db.get_catalog("Boshlang'ich")
    quarter = db.get_quarter()
    
    text = f"<b>FANLARDAN {quarter.upper()} EMAKTAB.UZ TIZIMIGA YUKLASH UCHUN OʻZBEK MAKTABLARGA 2025-2026 OʻQUV YILI ISH REJALARI</b>\n\n"
    text += "✅Oʻzingizga kerakli boʻlgan reja ustiga bosing va yuklab oling. Boshqalarga ham ulashishni unutmang.\n\n"
    
    if not files:
        text += "<i>Hozircha fayllar yuklanmagan.</i>"
    else:
        for name, link in files:
            text += f"📚 {name} — <a href='{link}'>YUKLAB OLISH</a>\n"
    
    text += f"\n❗️OʻQITUVCHILARGA JOʻNATISHNI UNUTMANG❗️\n\n#taqvim_mavzu_reja\n✅Kanal: @{CHANNEL_USERNAME}"
    await message.answer(text, disable_web_page_preview=True)

# --- Fayl Yuklash va Admin Amallari ---
@dp.message(F.document)
async def handle_doc(message: Message, state: FSMContext):
    # Admin ekanligini tekshirish
    if message.from_user.id != SUPER_ADMIN:
        return

    file_name = message.document.file_name
    file_path = f"downloads/{file_name}"
    
    # downloads papkasi yo'qligini tekshirish
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    await bot.download(message.document, destination=file_path)
    await state.update_data(file_path=file_path, file_name=file_name)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏷 User qo'shish (@)", callback_data="op_rename")],
        [InlineKeyboardButton(text="🛡 Muhr bosish", callback_data="op_watermark")],
        [InlineKeyboardButton(text="🚀 Kanalga yuborish", callback_data="op_category")]
    ])
    await message.answer(f"📄 Fayl: {file_name}\nTanlang:", reply_markup=kb)

@dp.callback_query(F.data == "op_rename")
async def cb_rename(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_path, new_name = rename_file(data['file_path'], CHANNEL_USERNAME)
    await state.update_data(file_path=new_path, file_name=new_name)
    await call.message.edit_text(f"✅ Nom o'zgardi: <code>{new_name}</code>", reply_markup=call.message.reply_markup)

@dp.callback_query(F.data == "op_category")
async def cb_choose_cat(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Boshlang'ich", callback_data="cat_Boshlang'ich")],
        [InlineKeyboardButton(text="🎓 Yuqori sinf", callback_data="cat_Yuqori")],
        [InlineKeyboardButton(text="📝 BSB/CHSB", callback_data="cat_BSB_CHSB")]
    ])
    await call.message.edit_text("Fayl qaysi bo'limga tushsin?", reply_markup=kb)

@dp.callback_query(F.data.startswith("cat_"))
async def cb_finalize_send(call: CallbackQuery, state: FSMContext):
    category = call.data.split("_")[1]
    data = await state.get_data()
    
    # AI orqali reklama matni yaratish
    ad_text = await ai_consultant(f"Fayl: {data['file_name']}, Bo'lim: {category} uchun reklama yoz.")
    
    # Kanalga yuborish
    try:
        msg = await bot.send_document(CHANNEL_ID, FSInputFile(data['file_path']), caption=ad_text)
        file_link = f"https://t.me/{CHANNEL_USERNAME}/{msg.message_id}"
        db.add_to_catalog(data['file_name'], category, file_link)
        await call.message.edit_text(f"🚀 Fayl {category} bo'limiga yuborildi!")
    except Exception as e:
        await call.message.answer(f"❌ Kanalga yuborishda xato: {e}")
    
    if os.path.exists(data['file_path']): 
        os.remove(data['file_path'])
    await state.clear()

# --- AI Suhbat ---
@dp.message(F.text == "💬 AI bilan suhbat")
async def start_ai_chat(message: Message, state: FSMContext):
    await message.answer("Siz AI metodik yordamchi bilan suhbat rejimidasiz. Savolingizni yozing (Chiqish uchun /cancel):")
    await state.set_state(BotStates.ai_chat)

@dp.message(BotStates.ai_chat)
async def process_ai_chat(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Suhbat yakunlandi.", reply_markup=main_menu())
        return
    
    # AI dan javob olish
    res = await ai_consultant(message.text)
    await message.answer(res)

# --- Navigatsiya ---
@dp.message(F.text == "📂 Fayllar Mundarijasi")
async def show_cats(message: Message): 
    await message.answer("Bo'limni tanlang:", reply_markup=catalog_menu())

@dp.message(F.text == "🤖 AI Xizmati")
async def show_ai(message: Message): 
    await message.answer("AI xizmatlari:", reply_markup=ai_service_menu())

@dp.message(F.text == "🔙 Orqaga")
async def go_back(message: Message): 
    await message.answer("Asosiy menyu", reply_markup=main_menu())

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(f"Xush kelibsiz @{CHANNEL_USERNAME} admin paneli!", reply_markup=main_menu())

# --- RENDER VA DOCKER UCHUN ASOSIY FUNKSIYA ---
async def main():
    # Render "No open ports detected" xatosini oldini olish uchun soxta server
    # Docker ichida 0.0.0.0 manzili shart
    port = int(os.environ.get("PORT", 10000))
    
    try:
        # Render kutayotgan portni band qilamiz
        await asyncio.start_server(lambda r, w: None, '0.0.0.0', port)
        print(f"✅ Render uchun {port}-port muvaffaqiyatli band qilindi.")
    except Exception as e:
        print(f"⚠️ Portni ochishda xatolik (mahalliyda normal): {e}")

    print("🚀 Bot ishga tushmoqda...")
    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot to'xtatildi.")
