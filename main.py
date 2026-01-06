import asyncio, os, zipfile, shutil, aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from database import Database
from processor import smart_rename, edit_excel, add_pdf_watermark

load_dotenv()
db = Database()
bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
CH_ID = os.getenv("CHANNEL_ID")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") # Render'dagi bot manzili

# --- 1. UXLAMASLIK UCHUN SELF-PING ---
async def keep_alive():
    """Bot uxlab qolmasligi uchun har 10 daqiqada o'ziga signal yuboradi"""
    if not RENDER_URL: return
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(RENDER_URL) as resp:
                    print(f"📡 Ping yuborildi: {resp.status}")
            except: print("📡 Ping xatosi")
            await asyncio.sleep(600) # 10 daqiqa

# --- 2. QOTMASLIK UCHUN AVTO-TOZALASH ---
async def auto_clear():
    while True:
        await asyncio.sleep(3600) # Har soatda tekshirish
        for d in ["downloads", "templates"]:
            for f in os.listdir(d):
                try: os.remove(os.path.join(d, f))
                except: pass

# --- ZIP VA FAYL PROCESSOR ---
async def handle_single_file(path, filename):
    new_name = smart_rename(filename)
    new_path = os.path.join(os.path.dirname(path), new_name)
    os.rename(path, new_path)
    
    if new_name.lower().endswith(('.xlsx', '.xls')): edit_excel(new_path)
    elif new_name.lower().endswith('.pdf'): add_pdf_watermark(new_path)
    
    cat = "Boshlang'ich" if any(x in new_name.lower() for x in ["1-sinf", "sinf", "alifbe"]) else "Yuqori"
    if "bsb" in new_name.lower() or "chsb" in new_name.lower(): cat = "BSB_CHSB"
    
    tpl = await db.get_setting('post_caption')
    msg = await bot.send_document(CH_ID, FSInputFile(new_path), caption=tpl.format(name=new_name, channel="ish_reja_uz"))
    await db.add_to_catalog(new_name, cat, f"https://t.me/ish_reja_uz/{msg.message_id}", msg.message_id)

@dp.message(F.document & (F.from_user.id == ADMIN_ID))
async def on_admin_doc(message: Message):
    l_path = f"downloads/{message.document.file_name}"
    await bot.download(message.document, destination=l_path)
    
    if l_path.endswith(".zip"):
        ex = f"downloads/ex_{message.message_id}"
        with zipfile.ZipFile(l_path, 'r') as z: z.extractall(ex)
        for r, d, fs in os.walk(ex):
            for f in fs:
                if f.startswith('.') or "__MACOSX" in r: continue
                await handle_single_file(os.path.join(r, f), f)
                await asyncio.sleep(0.3) # Qotib qolmaslik uchun pauza
        shutil.rmtree(ex)
    else:
        await handle_single_file(l_path, message.document.file_name)
    
    if os.path.exists(l_path): os.remove(l_path)
    await message.answer("✅ Muvaffaqiyatli yakunlandi!")

@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer("Bot onlayn va tezkor ishlamoqda! ⚡️")

async def main():
    await db.create_tables()
    asyncio.create_task(keep_alive())
    asyncio.create_task(auto_clear())
    
    # Render port binding (Health check uchun)
    from aiohttp import web
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
