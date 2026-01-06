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
from processor import smart_rename, edit_excel, add_pdf_watermark

load_dotenv()
logging.basicConfig(level=logging.INFO)
db = Database()
bot = Bot(token=os.getenv("BOT_TOKEN"), default=types.DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
scheduler = AsyncIOScheduler()

OWNER_ID = int(os.getenv("ADMIN_ID", 0))
CH_ID = os.getenv("CHANNEL_ID")
CH_NAME = os.getenv("CHANNEL_USERNAME", "ish_reja_uz").replace("@", "")

class AdminState(StatesGroup):
    waiting_for_time = State()
    waiting_for_shablon = State()
    waiting_for_footer = State()

# --- KLAVIATURALAR ---
def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📅 Rejalarni ko'rish"), KeyboardButton(text="📈 Batafsil statistika")],
        [KeyboardButton(text="📁 Kategoriyalar"), KeyboardButton(text="⚙️ Sozlamalar")],
        [KeyboardButton(text="💎 Adminlarni boshqarish")]
    ], resize_keyboard=True)

def settings_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Shablon", callback_data="set_tpl"), InlineKeyboardButton(text="🖋 Footer", callback_data="set_footer")],
        [InlineKeyboardButton(text="📅 Chorakni tanlash", callback_data="choose_q")],
        [InlineKeyboardButton(text="🗑 Tozalash", callback_data="clear_cat")]
    ])

# --- REJALASHTIRILGAN FUNKSIYA ---
async def send_scheduled_post(file_path, filename):
    try:
        new_name = smart_rename(filename)
        new_path = os.path.join(os.path.dirname(file_path), new_name)
        os.rename(file_path, new_path)
        
        if new_name.lower().endswith(('.xlsx', '.xls')): edit_excel(new_path)
        elif new_name.lower().endswith('.pdf'): add_pdf_watermark(new_path)

        caption = await db.get_setting('post_caption')
        footer = await db.get_setting('footer_text')
        
        sent = await bot.send_document(CH_ID, FSInputFile(new_path), 
                                     caption=caption.format(name=new_name, channel=CH_NAME) + footer)
        
        cat = "Boshlang'ich"
        if any(x in new_name.lower() for x in ["bsb", "chsb"]): cat = "BSB_CHSB"
        elif any(x in new_name.lower() for x in ["5-", "6-", "7-", "8-", "9-", "10-", "11-"]): cat = "Yuqori"
        
        await db.add_to_catalog(new_name, cat, f"https://t.me/{CH_NAME}/{sent.message_id}", sent.message_id)
        if os.path.exists(new_path): os.remove(new_path)
    except Exception as e:
        logging.error(f"Scheduling error: {e}")

# --- HANDLERLAR ---
@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    if await db.is_admin(m.from_user.id, OWNER_ID):
        await m.answer("🔝 <b>Professional Ma'muriyat Paneli</b>", reply_markup=main_kb())

@dp.message(F.document)
async def handle_doc(m: Message, state: FSMContext):
    if not await db.is_admin(m.from_user.id, OWNER_ID): return
    path = f"downloads/{m.document.file_name}"
    await bot.download(m.document, destination=path)
    await state.update_data(f_path=path, f_name=m.document.file_name)
    await m.answer("📅 Fayl qachon yuborilsin?\nFormat: <code>06.01.2025 23:00</code>\n(Hozir yuborish uchun 0 yozing)")
    await state.set_state(AdminState.waiting_for_time)

@dp.message(AdminState.waiting_for_time)
async def process_time(m: Message, state: FSMContext):
    data = await state.get_data()
    if m.text == "0":
        await send_scheduled_post(data['f_path'], data['f_name'])
        await m.answer("✅ Fayl darhol yuborildi.", reply_markup=main_kb())
    else:
        try:
            time = datetime.strptime(m.text, "%d.%m.%Y %H:%M")
            scheduler.add_job(send_scheduled_post, 'date', run_date=time, args=[data['f_path'], data['f_name']])
            await m.answer(f"⏳ Fayl rejalashtirildi: {m.text}", reply_markup=main_kb())
        except:
            await m.answer("❌ Format noto'g'ri. Namunaga qarang.")
            return
    await state.clear()

@dp.message(F.text == "⚙️ Sozlamalar")
async def settings(m: Message):
    if await db.is_admin(m.from_user.id, OWNER_ID):
        await m.answer("Sozlamalar bo'limi:", reply_markup=settings_kb())

async def main():
    await db.create_tables()
    scheduler.start()
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Live"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
