import asyncio, os, zipfile, shutil, aiohttp, logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web
from dotenv import load_dotenv

from database import Database
from processor import smart_rename, edit_excel, add_pdf_watermark

# Sozlamalar
load_dotenv()
logging.basicConfig(level=logging.INFO)
db = Database()
bot = Bot(token=os.getenv("BOT_TOKEN"), default=types.DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
OWNER_ID = int(os.getenv("ADMIN_ID", 0))
CH_ID = os.getenv("CHANNEL_ID")
CH_NAME = os.getenv("CHANNEL_USERNAME", "ish_reja_uz").replace("@", "")

class AdminStates(StatesGroup):
    waiting_for_caption = State()
    waiting_for_footer = State()
    waiting_for_new_admin = State()

# --- KLAVIATURALAR ---
def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📅 Rejalarni ko'ish"), KeyboardButton(text="📈 Batafsil statistika")],
        [KeyboardButton(text="📁 Kategoriyalar"), KeyboardButton(text="⚙️ Sozlamalar")],
        [KeyboardButton(text="💎 Adminlarni boshqarish")]
    ], resize_keyboard=True)

def get_settings_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Shablon", callback_data="edit_tpl"), InlineKeyboardButton(text="🖋 Footer", callback_data="edit_footer")],
        [InlineKeyboardButton(text="📅 Chorakni tanlash", callback_data="choose_q")],
        [InlineKeyboardButton(text="🗑 Tozalash", callback_data="clear_all"), InlineKeyboardButton(text="⚡ Tezkor", callback_data="quick_settings")]
    ])

# --- ADMIN TEKSHIRUV ---
async def check_admin(m: Message):
    if not await db.is_admin(m.from_user.id, OWNER_ID):
        await m.answer("Siz admin emassiz!")
        return False
    return True

# --- HANDLERLAR ---
@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    if await check_admin(m):
        await m.answer("🛡 <b>Professional Admin Panel</b> yuklandi.", reply_markup=get_main_kb())

@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(m: Message):
    if await check_admin(m):
        q = await db.get_setting('quarter')
        await m.answer(f"⚙️ <b>Tizim sozlamalari</b>\n\nHozirgi holat: <code>{q}</code>", reply_markup=get_settings_kb())

@dp.callback_query(F.data == "choose_q")
async def choose_q(c: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{i}-chorak", callback_data=f"set_q_{i}") for i in range(1, 3)],
        [InlineKeyboardButton(text=f"{i}-chorak", callback_data=f"set_q_{i}") for i in range(3, 5)]
    ])
    await c.message.edit_text("Yangi chorakni tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("set_q_"))
async def set_q(c: CallbackQuery):
    q = f"{c.data.split('_')[2]}-chorak"
    await db.update_setting('quarter', q.upper())
    await c.answer(f"✅ {q} tanlandi")
    await settings_menu(c.message)

@dp.message(F.text == "📈 Batafsil statistika")
async def show_stats(m: Message):
    if await check_admin(m):
        count = await db.get_stats()
        await m.answer(f"📊 <b>Bot statistikasi:</b>\n\n✅ Bazadagi fayllar: {count} ta\n📡 Kanal: @{CH_NAME}")

@dp.message(F.text == "💎 Adminlarni boshqarish")
async def manage_admins(m: Message):
    if m.from_user.id != OWNER_ID: return
    await m.answer("Yangi admin ID raqamini yuboring (Faqat asosiy admin uchun):")
    # Bu yerda FSM orqali ID qabul qilish mumkin

# --- FAYL BILAN ISHLASH (PRO) ---
async def process_file(local_path, filename):
    try:
        new_name = smart_rename(filename)
        new_path = os.path.join(os.path.dirname(local_path), new_name)
        os.rename(local_path, new_path)
        
        if new_name.lower().endswith(('.xlsx', '.xls')): edit_excel(new_path)
        elif new_name.lower().endswith('.pdf'): add_pdf_watermark(new_path)

        cat = "Boshlang'ich"
        if any(x in new_name.lower() for x in ["bsb", "chsb"]): cat = "BSB_CHSB"
        elif any(x in new_name.lower() for x in ["5-", "6-", "7-", "8-", "9-", "10-", "11-"]): cat = "Yuqori"

        caption = await db.get_setting('post_caption')
        footer = await db.get_setting('footer_text')
        
        sent = await bot.send_document(CH_ID, FSInputFile(new_path), caption=caption.format(name=new_name, channel=CH_NAME) + footer)
        await db.add_to_catalog(new_name, cat, f"https://t.me/{CH_NAME}/{sent.message_id}", sent.message_id)
        return True
    except Exception as e:
        logging.error(f"Error: {e}")
        return False

@dp.message(F.document)
async def handle_docs(m: Message):
    if not await check_admin(m): return
    status = await m.answer("⏳ Ishlov berilmoqda...")
    path = f"downloads/{m.document.file_name}"
    await bot.download(m.document, destination=path)
    
    if path.endswith(".zip"):
        ex = f"downloads/zip_{m.message_id}"
        os.makedirs(ex, exist_ok=True)
        with zipfile.ZipFile(path, 'r') as z: z.extractall(ex)
        for r, d, fs in os.walk(ex):
            for f in fs:
                if not f.startswith('.') and "__MACOSX" not in r:
                    await process_file(os.path.join(r, f), f)
        shutil.rmtree(ex)
        await status.edit_text("✅ ZIP barcha fayllari kanalda!")
    else:
        await process_file(path, m.document.file_name)
        await status.edit_text("✅ Fayl tayyor!")
    if os.path.exists(path): os.remove(path)

# --- RENDER WEB SERVER ---
async def main():
    await db.create_tables()
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is Live"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
