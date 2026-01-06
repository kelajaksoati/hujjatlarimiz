import asyncio
import os
import zipfile
import shutil
import aiohttp
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from dotenv import load_dotenv

from database import Database
from processor import smart_rename, edit_excel, add_pdf_watermark

# Loglarni sozlash (Xatolarni ko'rib turish uchun)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Ma'lumotlar bazasi va Botni sozlash
db = Database()
bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CH_ID = os.getenv("CHANNEL_ID")
CH_NAME = os.getenv("CHANNEL_USERNAME", "ish_reja_uz").replace("@", "")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

# Kerakli papkalar mavjudligini tekshirish
for folder in ["downloads", "templates"]:
    os.makedirs(folder, exist_ok=True)

# --- UXLAMASLIK VA TOZALASH TIZIMI ---
async def keep_alive():
    """Render bepul tarifida botni uyg'oq saqlash"""
    if not RENDER_URL:
        logger.warning("RENDER_EXTERNAL_URL topilmadi. Bot uyquga ketishi mumkin.")
        return
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(RENDER_URL) as resp:
                    logger.info(f"📡 Self-ping muvaffaqiyatli: {resp.status}")
            except Exception as e:
                logger.error(f"📡 Ping xatosi: {e}")
            await asyncio.sleep(600) # 10 daqiqa

async def scheduled_cleanup():
    """Xotirani tejash uchun har soatda downloads papkasini tozalash"""
    while True:
        await asyncio.sleep(3600)
        now = datetime.now()
        logger.info(f"♻️ Tozalash boshlandi: {now}")
        for folder in ["downloads", "templates"]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error(f"❌ O'chirishda xato {file_path}: {e}")

# --- FAYLLAR BILAN ISHLASH ---
async def process_file_logic(local_path, original_name):
    """Faylni brendlash, nomlash va kanalga yuborish mantiqi"""
    try:
        # 1. Aqlli nomlash
        new_name = smart_rename(original_name)
        dir_name = os.path.dirname(local_path)
        new_path = os.path.join(dir_name, new_name)
        os.rename(local_path, new_path)

        # 2. Excel yoki PDF bo'lsa brendlash
        if new_name.lower().endswith(('.xlsx', '.xls')):
            edit_excel(new_path)
        elif new_name.lower().endswith('.pdf'):
            add_pdf_watermark(new_path)

        # 3. Kategoriya aniqlash
        cat = "Boshlang'ich"
        n_low = new_name.lower()
        if any(x in n_low for x in ["bsb", "chsb", "imtihon", "test"]):
            cat = "BSB_CHSB"
        elif any(x in n_low for x in ["5-sinf", "6-sinf", "7-sinf", "8-sinf", "9-sinf", "10-sinf", "11-sinf"]):
            cat = "Yuqori"

        # 4. Kanalga yuborish
        caption_tpl = await db.get_setting('post_caption')
        caption = caption_tpl.format(name=new_name, channel=CH_NAME)
        
        doc = FSInputFile(new_path)
        sent_msg = await bot.send_document(CH_ID, doc, caption=caption)
        
        # 5. Bazaga yozish
        link = f"https://t.me/{CH_NAME}/{sent_msg.message_id}"
        await db.add_to_catalog(new_name, cat, link, sent_msg.message_id)
        return True
    except Exception as e:
        logger.error(f"Fayl ishlovida xato: {e}")
        return False

@dp.message(F.document & (F.from_user.id == ADMIN_ID))
async def handle_admin_document(message: Message):
    msg = await message.answer("⏳ Fayl qabul qilindi, ishlov berilmoqda...")
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
                    f_path = os.path.join(root, f)
                    if await process_file_logic(f_path, f):
                        count += 1
                        await asyncio.sleep(0.5) # Telegram limitlari uchun
            
            await msg.edit_text(f"✅ ZIP yakunlandi. {count} ta fayl kanalga joylandi.")
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)
    else:
        success = await process_file_logic(local_path, file_name)
        if success:
            await msg.edit_text("✅ Fayl tahrirlandi va kanalga yuborildi.")
        else:
            await msg.edit_text("❌ Faylni qayta ishlashda xato yuz berdi.")

    if os.path.exists(local_path):
        os.remove(local_path)

# --- MENYU VA BOSHQARUV ---
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📂 Fayllar Mundarijasi")],
            [KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="🗑 Bazani tozalash")]
        ], resize_keyboard=True
    )
    await message.answer(f"Xush kelibsiz! Bot faol holatda. 🚀", reply_markup=kb)

# ... (Mundarija va o'chirish handlerlari avvalgi koddagidek qoladi)

async def main():
    # 1. Bazani tayyorlash
    await db.create_tables()
    
    # 2. Fon vazifalarini ishga tushirish
    asyncio.create_task(keep_alive())
    asyncio.create_task(scheduled_cleanup())
    
    # 3. Health check uchun veb-server (Render talabi)
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is Live!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()
    
    # 4. Bot polling
    logger.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    asyncio.run(main())
