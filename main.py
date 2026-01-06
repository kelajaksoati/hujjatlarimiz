import asyncio, os, zipfile, shutil, aiohttp, logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web
from dotenv import load_dotenv

from database import Database
from processor import smart_rename, edit_excel, add_pdf_watermark, edit_docx

# Sozlamalar va Loglar
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()
bot = Bot(token=os.getenv("BOT_TOKEN"), default=types.DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
scheduler = AsyncIOScheduler()

OWNER_ID = int(os.getenv("ADMIN_ID", 0))
CH_ID = os.getenv("CHANNEL_ID")
CH_NAME = os.getenv("CHANNEL_USERNAME", "ish_reja_uz").replace("@", "")

# --- STATES (Holatlar) ---
class AdminStates(StatesGroup):
    waiting_for_time = State()
    waiting_for_caption = State()
    waiting_for_footer = State()

# --- KLAVIATURALAR ---
def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📅 Rejalarni ko'rish"), KeyboardButton(text="📈 Batafsil statistika")],
        [KeyboardButton(text="📁 Kategoriyalar"), KeyboardButton(text="⚙️ Sozlamalar")],
        [KeyboardButton(text="💎 Adminlarni boshqarish")]
    ], resize_keyboard=True)

def get_settings_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Shablon", callback_data="set_tpl"), InlineKeyboardButton(text="🖋 Footer", callback_data="set_footer")],
        [InlineKeyboardButton(text="📅 Chorakni tanlash", callback_data="choose_q")],
        [InlineKeyboardButton(text="🗑 Katalog tozalash", callback_data="clear_cat")]
    ])

# --- ADMIN TEKSHIRUV ---
async def is_bot_admin(user_id):
    return await db.is_admin(user_id, OWNER_ID)

# --- REJALASHTIRILGAN POST FUNKSIYASI ---
async def send_scheduled_file(file_path, original_name):
    try:
        new_name = smart_rename(original_name)
        new_path = os.path.join(os.path.dirname(file_path), new_name)
        os.rename(file_path, new_path)
        
        # Fayl turiga qarab tahrirlash
        if new_name.lower().endswith(('.xlsx', '.xls')): edit_excel(new_path)
        elif new_name.lower().endswith('.pdf'): add_pdf_watermark(new_path)
        elif new_name.lower().endswith('.docx'): edit_docx(new_path)

        # Kategoriya aniqlash
        cat = "Boshlang'ich"
        if any(x in new_name.lower() for x in ["bsb", "chsb"]): cat = "BSB_CHSB"
        elif any(x in new_name.lower() for x in ["5-", "6-", "7-", "8-", "9-", "10-", "11-"]): cat = "Yuqori"

        caption_tpl = await db.get_setting('post_caption')
        footer = await db.get_setting('footer_text')
        
        sent = await bot.send_document(
            CH_ID, 
            FSInputFile(new_path), 
            caption=caption_tpl.format(name=new_name, channel=CH_NAME) + footer
        )
        
        await db.add_to_catalog(new_name, cat, f"https://t.me/{CH_NAME}/{sent.message_id}", sent.message_id)
        
        if os.path.exists(new_path): os.remove(new_path)
        logger.info(f"Fayl muvaffaqiyatli yuborildi: {new_name}")
    except Exception as e:
        logger.error(f"Xatolik yuborishda: {e}")

# --- HANDLERLAR ---
@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    if await is_bot_admin(m.from_user.id):
        await m.answer("🔝 <b>Professional Ma'muriyat Paneli</b>", reply_markup=main_kb())

@dp.message(F.document)
async def handle_incoming_doc(m: Message, state: FSMContext):
    if not await is_bot_admin(m.from_user.id): return
    
    status = await m.answer("⏳ Fayl qabul qilinmoqda...")
    path = f"downloads/{m.document.file_name}"
    await bot.download(m.document, destination=path)
    
    await state.update_data(f_path=path, f_name=m.document.file_name)
    await status.edit_text(
        "📅 <b>Ushbu fayl qachon yuborilsin?</b>\n\n"
        "Format: <code>06.01.2025 23:00</code>\n"
        "Hozir yuborish uchun <b>0</b> yozing."
    )
    await state.set_state(AdminStates.waiting_for_time)

@dp.message(AdminStates.waiting_for_time)
async def process_schedule_time(m: Message, state: FSMContext):
    data = await state.get_data()
    file_path = data['f_path']
    file_name = data['f_name']

    if m.text == "0":
        # Darhol yuborish
        await m.answer("🚀 Darhol yuborish boshlandi...")
        if file_name.endswith(".zip"):
            # ZIP mantiqi
            ex_dir = f"downloads/zip_{m.message_id}"
            os.makedirs(ex_dir, exist_ok=True)
            with zipfile.ZipFile(file_path, 'r') as z: z.extractall(ex_dir)
            for r, d, fs in os.walk(ex_dir):
                for f in fs:
                    if not f.startswith('.') and "__MACOSX" not in r:
                        await send_scheduled_file(os.path.join(r, f), f)
            shutil.rmtree(ex_dir)
            await m.answer("✅ ZIP ichidagi barcha fayllar kanalga yuborildi.")
        else:
            await send_scheduled_file(file_path, file_name)
            await m.answer("✅ Fayl kanalga yuborildi.")
    else:
        # Rejalashtirish
        try:
            run_time = datetime.strptime(m.text, "%d.%m.%Y %H:%M")
            if run_time < datetime.now():
                await m.answer("❌ Xato! O'tib ketgan vaqt kiritildi.")
                return

            scheduler.add_job(send_scheduled_file, 'date', run_date=run_time, args=[file_path, file_name])
            await m.answer(f"⏳ Fayl rejalashtirildi: <b>{m.text}</b>\nBot ushbu vaqtda avtomat ishlaydi.")
        except ValueError:
            await m.answer("⚠️ Format xato! Namuna: 06.01.2025 23:00")
            return

    await state.clear()
    if os.path.exists(file_path) and not file_path.endswith(".zip"): os.remove(file_path)

@dp.message(F.text == "⚙️ Sozlamalar")
async def show_settings(m: Message):
    if await is_bot_admin(m.from_user.id):
        q = await db.get_setting('quarter')
        await m.answer(f"⚙️ <b>Tizim sozlamalari</b>\nHozirgi chorak: <code>{q}</code>", reply_markup=get_settings_kb())

@dp.message(F.text == "📈 Batafsil statistika")
async def show_stats(m: Message):
    if await is_bot_admin(m.from_user.id):
        count = await db.get_stats()
        await m.answer(f"📊 <b>Statistika:</b>\n\n✅ Bazadagi fayllar: {count} ta\n📡 Kanal: @{CH_NAME}")

# --- WEB SERVER (RENDER UCHUN) ---
async def main():
    await db.create_tables()
    scheduler.start()
    
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is Live 🚀"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
