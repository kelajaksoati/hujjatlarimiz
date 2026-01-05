Barcha so'ralgan funksiyalarni, xususan, Mundarija (Fanlar ro'yxati) shabloni va Shablon yaratish bo'limlarini o'z ichiga olgan to'liq main.py kodi quyida keltirilgan.

🛠 Yangilangan main.py
Python

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

# --- Mundarija Generator (Siz so'ragan fanlar ro'yxati bilan) ---
@dp.message(F.text.in_(["📚 Boshlang'ich (1-4)", "🎓 Yuqori (5-11)", "📝 BSB va CHSB"]))
async def send_catalog(message: Message):
    category = "Boshlang'ich" if "Boshlang'ich" in message.text else "Yuqori"
    if "BSB" in message.text: category = "BSB_CHSB"
    
    files = db.get_catalog(category)
    quarter = db.get_quarter() or "2-CHORAK"
    
    # Asosiy matn shabloni
    text = (
        f"<b>FANLARDAN {quarter} EMAKTAB.UZ TIZIMIGA YUKLASH UCHUN OʻZBEK MAKTABLARGA "
        f"2025-2026 OʻQUV YILI ISH REJALARI</b>\n\n"
        f"✅Oʻzingizga kerakli boʻlgan reja ustiga bosing va yuklab oling. "
        f"Boshqalarga ham ulashishni unutmang.\n\n"
    )

    # Agar bazada fayllar bo'lsa, ularni havolasi bilan chiqaramiz
    if files:
        for name, link in files:
            text += f"📚 {name} — <a href='{link}'>YUKLAB OLISH</a>\n"
    else:
        # Fayl topilmasa, siz yuborgan standart fanlar ro'yxatini chiqaramiz
        subjects = [
            "Alifbe 1-sinf", "Yozuv 1-sinf", "Oʻqish savodxonligi 1-4-sinf",
            "Adabiyot 5-11-sinf", "Biologiya 7-11-sinf", "Fizika 7-11-sinf",
            "Informatika 1-11-sinf", "Ingliz tili 1-11-sinf", "Matematika 1-7-sinf",
            "Ona tili 2-11-sinf", "Tarix 5-11-sinf", "Kelajak soati 1-11-sinf"
        ]
        for sub in subjects:
            text += f"📚 {sub}\n"
        text += "\n<i>Hozircha yuklash uchun linklar tayyorlanmoqda...</i>"

    text += (
        f"\n\n❗️OʻQITUVCHILARGA JOʻNATISHNI UNUTMANG❗️\n\n"
        f"#taqvim_mavzu_reja\n"
        f"✅Kanalga obuna bo‘lish:👇👇👇\n"
        f"https://t.me/{CHANNEL_USERNAME}"
    )
    
    await message.answer(text, disable_web_page_preview=True)

# --- Shablon yaratish logikasi ---
@dp.message(F.text == "📝 Shablon yaratish")
async def ask_template_info(message: Message, state: FSMContext):
    await message.answer("<b>Yangi dars ishlanmasi shabloni yaratish</b>\n\n"
                         "Iltimos, ma'lumotlarni quyidagi formatda yuboring:\n"
                         "<code>Ism Familiya, Fan nomi, Sinf</code>\n\n"
                         "<i>Masalan: Anvar Valiyev, Matematika, 5-sinf</i>")
    await state.set_state(BotStates.waiting_for_template_data)

@dp.message(BotStates.waiting_for_template_data)
async def process_template_creation(message: Message, state: FSMContext):
    try:
        data = message.text.split(",")
        if len(data) < 3:
            await message.answer("⚠️ Ma'mulotlar to'liq emas. Namuna: <i>Ism, Fan, Sinf</i>")
            return

        name, subject, grade = data[0].strip(), data[1].strip(), data[2].strip()
        file_path = create_lesson_template(name, subject, grade)
        
        if file_path and os.path.exists(file_path):
            await message.answer_document(
                FSInputFile(file_path), 
                caption=f"✅ <b>{subject}</b> fanidan dars ishlanmasi shabloni tayyor!"
            )
            os.remove(file_path)
        else:
            await message.answer("❌ Shablon yaratishda texnik xatolik yuz berdi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
    finally:
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
    res = await ai_consultant(message.text)
    await message.answer(res)

# --- Fayl Yuklash va Admin Amallari ---
@dp.message(F.document)
async def handle_doc(message: Message, state: FSMContext):
    if message.from_user.id != SUPER_ADMIN: return
    file_name = message.document.file_name
    file_path = f"downloads/{file_name}"
    if not os.path.exists("downloads"): os.makedirs("downloads")
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
    ad_text, _ = await generate_ai_ad(data['file_name'], category, "Barcha", "2-chorak")
    try:
        msg = await bot.send_document(CHANNEL_ID, FSInputFile(data['file_path']), caption=ad_text)
        file_link = f"https://t.me/{CHANNEL_USERNAME}/{msg.message_id}"
        db.add_to_catalog(data['file_name'], category, file_link)
        await call.message.edit_text(f"🚀 Fayl {category} bo'limiga yuborildi!")
    except Exception as e:
        await call.message.answer(f"❌ Kanalga yuborishda xato: {e}")
    if os.path.exists(data['file_path']): os.remove(data['file_path'])
    await state.clear()

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

async def main():
    port = int(os.environ.get("PORT", 10000))
    try:
        await asyncio.start_server(lambda r, w: None, '0.0.0.0', port)
        print(f"✅ Render uchun {port}-port band qilindi.")
    except Exception as e:
        print(f"⚠️ Port xatosi: {e}")
    print("🚀 Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
