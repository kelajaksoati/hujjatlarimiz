import asyncio, os, zipfile, shutil, logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web
from dotenv import load_dotenv

from database import Database
from processor import smart_rename, edit_excel, add_pdf_watermark, edit_docx

load_dotenv()
logging.basicConfig(level=logging.INFO)
db = Database()
bot = Bot(token=os.getenv("BOT_TOKEN"), default=types.DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
scheduler = AsyncIOScheduler()

OWNER_ID = int(os.getenv("ADMIN_ID", 0))
CH_ID = os.getenv("CHANNEL_ID")
CH_NAME = os.getenv("CHANNEL_USERNAME", "ish_reja_uz").replace("@", "")

class AdminStates(StatesGroup):
    waiting_for_time = State()

def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📅 Rejalarni ko'rish"), KeyboardButton(text="📈 Batafsil statistika")],
        [KeyboardButton(text="⚙️ Sozlamalar")]
    ], resize_keyboard=True)

async def is_bot_admin(user_id):
    return await db.is_admin(user_id, OWNER_ID)

async def send_processed_file(file_path, original_name):
    try:
        new_name = smart_rename(original_name)
        new_path = os.path.join(os.path.dirname(file_path), new_name)
        os.rename(file_path, new_path)

        if new_name.lower().endswith(('.xlsx', '.xls')): edit_excel(new_path)
        elif new_name.lower().endswith('.pdf'): add_pdf_watermark(new_path)
        elif new_name.lower().endswith('.docx'): edit_docx(new_path)

        cap_tpl = await db.get_setting('post_caption')
        footer = await db.get_setting('footer_text')
        
        sent = await bot.send_document(CH_ID, FSInputFile(new_path), 
                                     caption=cap_tpl.format(name=new_name, channel=CH_NAME) + footer)
        
        cat = "BSB_CHSB" if "bsb" in new_name.lower() else "Yuqori"
        await db.add_to_catalog(new_name, cat, f"https://t.me/{CH_NAME}/{sent.message_id}", sent.message_id)
        
        if os.path.exists(new_path): os.remove(new_path)
    except Exception as e:
        logging.error(f"Post error: {e}")

@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    if await is_bot_admin(m.from_user.id):
        await m.answer("🛡 Admin Panel Faol", reply_markup=get_main_kb())

@dp.message(F.document)
async def handle_doc(m: Message, state: FSMContext):
    if not await is_bot_admin(m.from_user.id): return
    path = f"downloads/{m.document.file_name}"
    os.makedirs("downloads", exist_ok=True)
    await bot.download(m.document, destination=path)
    await state.update_data(f_path=path, f_name=m.document.file_name)
    await m.answer("📅 Vaqtni kiriting (DD.MM.YYYY HH:MM) yoki darhol yuborish uchun 0:")
    await state.set_state(AdminStates.waiting_for_time)

@dp.message(AdminStates.waiting_for_time)
async def process_time(m: Message, state: FSMContext):
    data = await state.get_data()
    file_path, file_name = data['f_path'], data['f_name']

    if m.text == "0":
        if file_name.endswith(".zip"):
            ex_dir = f"downloads/zip_{datetime.now().timestamp()}"
            with zipfile.ZipFile(file_path, 'r') as z: z.extractall(ex_dir)
            for r, d, fs in os.walk(ex_dir):
                for f in fs:
                    if not f.startswith('.') and "__MACOSX" not in r:
                        await send_processed_file(os.path.join(r, f), f)
            shutil.rmtree(ex_dir)
        else:
            await send_processed_file(file_path, file_name)
        await m.answer("✅ Bajarildi")
    else:
        try:
            run_time = datetime.strptime(m.text, "%d.%m.%Y %H:%M")
            scheduler.add_job(send_processed_file, 'date', run_date=run_time, args=[file_path, file_name])
            await m.answer(f"⏳ Rejalashtirildi: {m.text}")
        except:
            await m.answer("⚠️ Format xato")
    await state.clear()

async def main():
    await db.create_tables()
    scheduler.start()
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot Active"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
