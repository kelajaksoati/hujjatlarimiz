import asyncio
import os
import zipfile
import shutil
import aiohttp
import logging
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

for folder in ["downloads", "templates"]:
    os.makedirs(folder, exist_ok=True)

async def keep_alive():
    if not RENDER_URL:
        return
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(RENDER_URL) as resp:
                    logger.info(f"📡 Ping status: {resp.status}")
            except Exception as e:
                logger.error(f"📡 Ping error: {e}")
            await asyncio.sleep(600)

async def scheduled_cleanup():
    while True:
        await asyncio.sleep(3600)
        for folder in ["downloads", "templates"]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path): os.unlink(file_path)
                    elif os.path.isdir(file_path): shutil.rmtree(file_path)
                except: pass

async def process_file_logic(local_path, original_name):
    try:
        new_name = smart_rename(original_name)
        new_path = os.path.join(os.path.dirname(local_path), new_name)
        os.rename(local_path, new_path)

        if new_name.lower().endswith(('.xlsx', '.xls')): edit_excel(new_path)
        elif new_name.lower().endswith('.pdf'): add_pdf_watermark(new_path)

        cat = "Boshlang'ich"
        n_low = new_name.lower()
        if any(x in n_low for x in ["bsb", "chsb", "test"]): cat = "BSB_CHSB"
        elif any(x in n_low for x in ["5-sinf", "6-sinf", "7-sinf", "8-sinf", "9-sinf", "10-sinf", "11-sinf"]): cat = "Yuqori"

        caption_tpl = await db.get_setting('post_caption')
        caption = caption_tpl.format(name=new_name, channel=CH_NAME)
        
        sent_msg = await bot.send_document(CH_ID, FSInputFile(new_path), caption=caption)
        await db.add_to_catalog(new_name, cat, f"https://t.me/{CH_NAME}/{sent_msg.message_id}", sent_msg.message_id)
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

@dp.message(F.document & (F.from_user.id == ADMIN_ID))
async def handle_admin_document(message: Message):
    msg = await message.answer("⏳ Ishlov berilmoqda...")
    file_name = message.document.file_name
    local_path = f"downloads/{file_name}"
    await bot.download(message.document, destination=local_path)

    if file_name.lower().endswith(".zip"):
        extract_dir = f"downloads/zip_{message.message_id}"
        os.makedirs(extract_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(local_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            count = 0
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.startswith('.') or "__MACOSX" in root: continue
                    if await process_file_logic(os.path.join(root, f), f):
                        count += 1
                        await asyncio.sleep(0.5)
            await msg.edit_text(f"✅ ZIP yakunlandi: {count} ta fayl.")
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)
    else:
        if await process_file_logic(local_path, file_name):
            await msg.edit_text("✅ Fayl tayyor.")
        else:
            await msg.edit_text("❌ Xato.")

    if os.path.exists(local_path): os.remove(local_path)

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📂 Fayllar Mundarijasi")],[KeyboardButton(text="🗑 Bazani tozalash")]], resize_keyboard=True)
    await message.answer("Bot tayyor! 🚀", reply_markup=kb)

@dp.message(F.text == "📂 Fayllar Mundarijasi")
async def show_catalog(message: Message):
    q = await db.get_setting('quarter')
    header = await db.get_setting('catalog_header')
    for c in ["Boshlang'ich", "Yuqori", "BSB_CHSB"]:
        items = await db.get_catalog(c)
        if not items: continue
        text = f"<b>{header.format(quarter=q)}</b>\n\n<u>{c}</u>\n\n"
        for idx, name, link in items:
            text += f"📚 <a href='{link}'>{name}</a>\n"
        await message.answer(text, disable_web_page_preview=True)

@dp.message(F.text == "🗑 Bazani tozalash")
async def clear_db(message: Message):
    if message.from_user.id == ADMIN_ID:
        await db.clear_database()
        await message.answer("✅ Mundarija tozalandi.")

async def main():
    await db.create_tables()
    asyncio.create_task(keep_alive())
    asyncio.create_task(scheduled_cleanup())
    
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is Live!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
