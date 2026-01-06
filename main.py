import asyncio, os, zipfile, shutil, aiohttp, logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from dotenv import load_dotenv

from database import Database
from processor import smart_rename, edit_excel, add_pdf_watermark

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

db = Database()
bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CH_ID = os.getenv("CHANNEL_ID")
CH_NAME = os.getenv("CHANNEL_USERNAME", "ish_reja_uz").replace("@", "")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

for folder in ["downloads", "templates"]: os.makedirs(folder, exist_ok=True)

# --- KLAVIATURALAR ---
def admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📂 Fayllar Mundarijasi")],
        [KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="🗑 Bazani tozalash")]
    ], resize_keyboard=True)

def settings_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1-CHORAK", callback_data="set_q_1"), InlineKeyboardButton(text="2-CHORAK", callback_data="set_q_2")],
        [InlineKeyboardButton(text="3-CHORAK", callback_data="set_q_3"), InlineKeyboardButton(text="4-CHORAK", callback_data="set_q_4")]
    ])

# --- FUNKSIYALAR ---
async def keep_alive():
    if not RENDER_URL: return
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(RENDER_URL) as resp: logger.info(f"📡 Ping: {resp.status}")
            except: pass
            await asyncio.sleep(600)

async def process_file_logic(local_path, original_name):
    try:
        new_name = smart_rename(original_name)
        new_path = os.path.join(os.path.dirname(local_path), new_name)
        os.rename(local_path, new_path)
        if new_name.lower().endswith(('.xlsx', '.xls')): edit_excel(new_path)
        elif new_name.lower().endswith('.pdf'): add_pdf_watermark(new_path)

        cat = "Boshlang'ich"
        if any(x in new_name.lower() for x in ["bsb", "chsb"]): cat = "BSB_CHSB"
        elif any(x in new_name.lower() for x in ["5-", "6-", "7-", "8-", "9-", "10-", "11-"]): cat = "Yuqori"

        caption_tpl = await db.get_setting('post_caption')
        sent_msg = await bot.send_document(CH_ID, FSInputFile(new_path), caption=caption_tpl.format(name=new_name, channel=CH_NAME))
        await db.add_to_catalog(new_name, cat, f"https://t.me/{CH_NAME}/{sent_msg.message_id}", sent_msg.message_id)
        return True
    except: return False

# --- HANDLERLAR ---
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("Boshqaruv paneli:", reply_markup=admin_kb())

@dp.message(F.text == "⚙️ Sozlamalar")
async def show_settings(message: Message):
    curr_q = await db.get_setting('quarter')
    await message.answer(f"Hozirgi chorak: <b>{curr_q}</b>\n\nO'zgartirish uchun tanlang:", reply_markup=settings_kb())

@dp.callback_query(F.data.startswith("set_q_"))
async def update_q(call: CallbackQuery):
    q_num = call.data.split("_")[2]
    await db.update_setting('quarter', f"{q_num}-CHORAK")
    await call.message.edit_text(f"✅ Chorak {q_num}-CHORAK ga o'zgartirildi!")
    await call.answer()

@dp.message(F.text == "📂 Fayllar Mundarijasi")
async def show_catalog(message: Message):
    q = await db.get_setting('quarter')
    header = await db.get_setting('catalog_header')
    found = False
    for c in ["Boshlang'ich", "Yuqori", "BSB_CHSB"]:
        items = await db.get_catalog(c)
        if not items: continue
        found = True
        text = f"<b>{header.format(quarter=q)}</b>\n\n<u>{c} bo'limi:</u>\n\n"
        for idx, name, link in items: text += f"📚 <a href='{link}'>{name}</a>\n"
        await message.answer(text, disable_web_page_preview=True)
    if not found: await message.answer("Bazada fayllar yo'q. Avval fayl yuklang!")

@dp.message(F.document & (F.from_user.id == ADMIN_ID))
async def handle_docs(message: Message):
    msg = await message.answer("⏳ Ishlanmoqda...")
    path = f"downloads/{message.document.file_name}"
    await bot.download(message.document, destination=path)
    if path.endswith(".zip"):
        ex = f"downloads/zip_{message.message_id}"
        os.makedirs(ex, exist_ok=True)
        with zipfile.ZipFile(path, 'r') as z: z.extractall(ex)
        for r, d, fs in os.walk(ex):
            for f in fs:
                if f.startswith('.') or "__MACOSX" in r: continue
                await process_file_logic(os.path.join(r, f), f)
        shutil.rmtree(ex)
        await msg.edit_text("✅ ZIP arxivdagi barcha fayllar joylandi!")
    else:
        await process_file_logic(path, message.document.file_name)
        await msg.edit_text("✅ Fayl tayyor!")
    if os.path.exists(path): os.remove(path)

@dp.message(F.text == "🗑 Bazani tozalash")
async def clear_db(message: Message):
    await db.clear_database()
    await message.answer("✅ Barcha ma'lumotlar o'chirildi.")

async def main():
    await db.create_tables()
    asyncio.create_task(keep_alive())
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Live"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
