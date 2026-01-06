import asyncio, os, zipfile, shutil, aiohttp, logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties 
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web
from dotenv import load_dotenv

# O'zingizning fayllaringizdan import
from database import Database
from processor import smart_rename, edit_excel, add_pdf_watermark, edit_docx

# Sozlamalar
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()
bot = Bot(
    token=os.getenv("BOT_TOKEN"), 
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

OWNER_ID = int(os.getenv("ADMIN_ID", 0))
CH_ID = os.getenv("CHANNEL_ID")
CH_NAME = os.getenv("CHANNEL_USERNAME", "ish_reja_uz").replace("@", "")

class AdminStates(StatesGroup):
    waiting_for_time = State()
    waiting_for_caption = State()

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

# --- FUNKSIYALAR ---
async def process_and_send(file_path, original_name):
    try:
        new_name = smart_rename(original_name)
        new_path = os.path.join(os.path.dirname(file_path), new_name)
        os.rename(file_path, new_path)
        
        # Faylni tahrirlash
        if new_name.lower().endswith(('.xlsx', '.xls')): edit_excel(new_path)
        elif new_name.lower().endswith('.pdf'): add_pdf_watermark(new_path)
        elif new_name.lower().endswith('.docx'): edit_docx(new_path)

        # Kategoriya aniqlash
        cat = "BSB_CHSB" if "bsb" in new_name.lower() or "chsb" in new_name.lower() else \
              ("Yuqori" if any(x in new_name.lower() for x in ["5-","6-","7-","8-","9-","10-","11-"]) else "Boshlang'ich")

        caption_tpl = await db.get_setting('post_caption')
        footer = await db.get_setting('footer_text')
        
        sent = await bot.send_document(
            CH_ID, 
            FSInputFile(new_path), 
            caption=caption_tpl.format(name=new_name, channel=CH_NAME) + footer
        )
        
        await db.add_to_catalog(new_name, cat, f"https://t.me/{CH_NAME}/{sent.message_id}", sent.message_id)
        if os.path.exists(new_path): os.remove(new_path)
        logger.info(f"Fayl yuborildi: {new_name}")
    except Exception as e:
        logger.error(f"Xatolik: {e}")

# --- HANDLERLAR ---
@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    if m.from_user.id == OWNER_ID or await db.is_admin(m.from_user.id, OWNER_ID):
        await m.answer("🛡 <b>Admin Panel yuklandi.</b>", reply_markup=get_main_kb())

@dp.message(F.document)
async def handle_doc(m: Message, state: FSMContext):
    if not (m.from_user.id == OWNER_ID or await db.is_admin(m.from_user.id, OWNER_ID)): return
    
    os.makedirs("downloads", exist_ok=True)
    path = f"downloads/{m.document.file_name}"
    await bot.download(m.document, destination=path)
    
    await state.update_data(f_path=path, f_name=m.document.file_name)
    await m.answer("📅 Fayl qachon yuborilsin? (Format: <code>DD.MM.YYYY HH:MM</code>)\nHozir yuborish uchun <b>0</b> yuboring.")
    await state.set_state(AdminStates.waiting_for_time)

@dp.message(AdminStates.waiting_for_time)
async def schedule_step(m: Message, state: FSMContext):
    data = await state.get_data()
    if m.text == "0":
        if data['f_name'].endswith(".zip"):
            ex_dir = f"downloads/zip_{datetime.now().timestamp()}"
            with zipfile.ZipFile(data['f_path'], 'r') as z: z.extractall(ex_dir)
            for r, d, fs in os.walk(ex_dir):
                for f in fs:
                    if not f.startswith('.') and "__MACOSX" not in r: 
                        await process_and_send(os.path.join(r, f), f)
            shutil.rmtree(ex_dir)
            if os.path.exists(data['f_path']): os.remove(data['f_path'])
        else:
            await process_and_send(data['f_path'], data['f_name'])
        await m.answer("✅ Fayllar yuborildi.")
    else:
        try:
            run_time = datetime.strptime(m.text, "%d.%m.%Y %H:%M")
            scheduler.add_job(process_and_send, 'date', run_date=run_time, args=[data['f_path'], data['f_name']])
            await m.answer(f"⏳ Fayl rejalashtirildi: {m.text}")
        except:
            await m.answer("❌ Format xato. Namuna: 06.01.2025 23:00")
            return
    await state.clear()

@dp.message(F.text == "📁 Kategoriyalar")
async def show_cats(m: Message):
    if not (m.from_user.id == OWNER_ID or await db.is_admin(m.from_user.id, OWNER_ID)): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Boshlang'ich", callback_data="cat_Boshlang'ich")],
        [InlineKeyboardButton(text="Yuqori sinflar", callback_data="cat_Yuqori")],
        [InlineKeyboardButton(text="BSB/CHSB", callback_data="cat_BSB_CHSB")]
    ])
    await m.answer("Mundarija yaratish uchun kategoriyani tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("cat_"))
async def create_catalog(c: CallbackQuery):
    cat = c.data.split("_", 1)[1]
    items = await db.get_catalog(cat)
    if not items: return await c.answer("Hozircha bu bo'limda fayl yo'q", show_alert=True)
    
    q = await db.get_setting('quarter')
    header = await db.get_setting('catalog_header')
    text = f"<b>{header.format(quarter=q)}</b>\n\n"
    for i, (name, link) in enumerate(items, 1):
        text += f"{i}. <a href='{link}'>{name}</a>\n"
    
    await bot.send_message(CH_ID, text, disable_web_page_preview=True)
    await c.answer("Mundarija kanalga yuborildi!")

@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(m: Message):
    if m.from_user.id == OWNER_ID or await db.is_admin(m.from_user.id, OWNER_ID):
        await m.answer("⚙️ <b>Sozlamalar paneli:</b>", reply_markup=get_settings_kb())

@dp.message(F.text == "📈 Batafsil statistika")
async def show_stats(m: Message):
    if m.from_user.id == OWNER_ID or await db.is_admin(m.from_user.id, OWNER_ID):
        count = await db.get_stats()
        await m.answer(f"📊 <b>Statistika:</b>\n\n✅ Bazadagi fayllar: {count} ta\n📡 Kanal: @{CH_NAME}")

# --- RENDER SERVER ---
async def main():
    await db.create_tables()
    scheduler.start()
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is Live"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
