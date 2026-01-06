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

# O'zingizning fayllaringizdan importlar
from database import Database
from processor import smart_rename, edit_excel, add_pdf_watermark, edit_docx

# Sozlamalar va Loglar
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
    waiting_for_tpl = State()
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
        [InlineKeyboardButton(text="📅 Chorak", callback_data="choose_q"), InlineKeyboardButton(text="🗑 Tozalash", callback_data="clear_cat")]
    ])

# --- ASOSIY FUNKSIYALAR ---
async def process_and_send(file_path, original_name):
    try:
        new_name = smart_rename(original_name)
        new_path = os.path.join(os.path.dirname(file_path), new_name)
        os.rename(file_path, new_path)
        
        if new_name.lower().endswith(('.xlsx', '.xls')): edit_excel(new_path)
        elif new_name.lower().endswith('.pdf'): add_pdf_watermark(new_path)
        elif new_name.lower().endswith('.docx'): edit_docx(new_path)

        cat = "BSB_CHSB" if "bsb" in new_name.lower() or "chsb" in new_name.lower() else \
              ("Yuqori" if any(x in new_name.lower() for x in ["5-","6-","7-","8-","9-","10-","11-"]) else "Boshlang'ich")

        caption_tpl = await db.get_setting('post_caption') or "{name} | @{channel}"
        footer = await db.get_setting('footer_text') or ""
        
        sent = await bot.send_document(
            CH_ID, 
            FSInputFile(new_path), 
            caption=caption_tpl.format(name=new_name, channel=CH_NAME) + f"\n\n{footer}"
        )
        
        await db.add_to_catalog(new_name, cat, f"https://t.me/{CH_NAME}/{sent.message_id}", sent.message_id)
        if os.path.exists(new_path): os.remove(new_path)
    except Exception as e:
        logger.error(f"Fayl yuborishda xatolik: {e}")

# --- HANDLERLAR ---
@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    if m.from_user.id == OWNER_ID or await db.is_admin(m.from_user.id, OWNER_ID):
        await m.answer("🛡 <b>Admin Panel yuklandi.</b>", reply_markup=get_main_kb())

@dp.message(F.text.startswith("/add_admin"))
async def add_admin_handler(m: Message):
    if m.from_user.id != OWNER_ID:
        return await m.answer("❌ Bu buyruq faqat asosiy ega uchun!")
    try:
        new_id = int(m.text.split()[1])
        await db.add_admin(new_id)
        await m.answer(f"✅ Yangi admin qo'shildi! ID: <code>{new_id}</code>")
    except:
        await m.answer("⚠️ Format: <code>/add_admin ID</code>")

# --- SOZLAMALAR CALLBACKLARI ---
@dp.callback_query(F.data == "set_tpl")
async def set_template(call: CallbackQuery, state: FSMContext):
    await call.message.answer("📝 Yangi shablon matnini yuboring.\nNamuna: <code>{name} fayli @{channel} kanalidan</code>")
    await state.set_state(AdminStates.waiting_for_tpl)
    await call.answer()

@dp.callback_query(F.data == "set_footer")
async def set_footer_call(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🖋 Post ostiga qo'shiladigan footer matnini yuboring:")
    await state.set_state(AdminStates.waiting_for_footer)
    await call.answer()

@dp.message(AdminStates.waiting_for_tpl)
async def save_tpl(m: Message, state: FSMContext):
    await db.set_setting('post_caption', m.text)
    await m.answer("✅ Shablon saqlandi!")
    await state.clear()

@dp.message(AdminStates.waiting_for_footer)
async def save_footer(m: Message, state: FSMContext):
    await db.set_setting('footer_text', m.text)
    await m.answer("✅ Footer matni saqlandi!")
    await state.clear()

@dp.callback_query(F.data == "choose_q")
async def choose_quarter(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1-Chorak", callback_data="q_1"), InlineKeyboardButton(text="2-Chorak", callback_data="q_2")],
        [InlineKeyboardButton(text="3-Chorak", callback_data="q_3"), InlineKeyboardButton(text="4-Chorak", callback_data="q_4")]
    ])
    await call.message.edit_text("📅 Chorakni tanlang:", reply_markup=kb)

# --- CHORAK TANLASH HANDLERI ---
@dp.callback_query(F.data.startswith("q_"))
async def set_quarter_handler(call: CallbackQuery):
    q_value = call.data.split("_")[1]
    await db.set_setting('quarter', q_value)
    await call.message.edit_text(f"✅ Chorak muvaffaqiyatli o'zgartirildi: <b>{q_value}-chorak</b>")
    await call.answer()

@dp.callback_query(F.data == "clear_cat")
async def clear_catalog(call: CallbackQuery):
    await db.clear_all()
    await call.message.answer("✅ Katalog muvaffaqiyatli tozalandi!")
    await call.answer()

# --- REJALAR, STATISTIKA VA KATEGORIYALAR ---
@dp.message(F.text == "📅 Rejalarni ko'rish")
async def view_plans(m: Message):
    if not (m.from_user.id == OWNER_ID or await db.is_admin(m.from_user.id, OWNER_ID)): return
    plans = scheduler.get_jobs()
    if not plans: return await m.answer("📭 Hozircha rejalashtirilgan fayllar yo'q.")
    text = "⏳ <b>Kutilayotgan rejalar:</b>\n\n"
    for job in plans:
        text += f"📄 {job.args[1]}\n⏰ {job.next_run_time.strftime('%d.%m.%Y %H:%M')}\n\n"
    await m.answer(text)

@dp.message(F.text == "📈 Batafsil statistika")
async def show_stats(m: Message):
    if not (m.from_user.id == OWNER_ID or await db.is_admin(m.from_user.id, OWNER_ID)): return
    count = await db.get_stats() 
    await m.answer(f"📊 <b>Statistika</b>\n\n✅ Jami fayllar: <b>{count} ta</b>\n📡 Kanal: @{CH_NAME}")

@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(m: Message):
    if m.from_user.id == OWNER_ID or await db.is_admin(m.from_user.id, OWNER_ID):
        await m.answer("⚙️ <b>Sozlamalar bo'limi:</b>", reply_markup=get_settings_kb())

@dp.message(F.text == "💎 Adminlarni boshqarish")
async def manage_admins(m: Message):
    if m.from_user.id != OWNER_ID: return
    admins_list = await db.get_admins()
    if not admins_list:
        await m.answer("👥 Adminlar yo'q.\nAdmin qo'shish: <code>/add_admin ID</code>")
    else:
        text = "👥 <b>Adminlar ro'yxati:</b>\n\n"
        for adm in admins_list: text += f"👤 ID: <code>{adm[0]}</code>\n"
        await m.answer(text)

@dp.message(F.document)
async def handle_doc(m: Message, state: FSMContext):
    if not (m.from_user.id == OWNER_ID or await db.is_admin(m.from_user.id, OWNER_ID)): return
    os.makedirs("downloads", exist_ok=True)
    path = f"downloads/{m.document.file_name}"
    await bot.download(m.document, destination=path)
    await state.update_data(f_path=path, f_name=m.document.file_name)
    await m.answer("📅 Vaqt (DD.MM.YYYY HH:MM) yoki hozir uchun <b>0</b>:")
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
        else:
            await process_and_send(data['f_path'], data['f_name'])
        await m.answer("✅ Bajarildi.")
    else:
        try:
            run_time = datetime.strptime(m.text, "%d.%m.%Y %H:%M")
            scheduler.add_job(process_and_send, 'date', run_date=run_time, args=[data['f_path'], data['f_name']])
            await m.answer(f"⏳ Rejalashtirildi: {m.text}")
        except:
            await m.answer("❌ Xato format. Namuna: 06.01.2025 23:00")
    await state.clear()

@dp.message(F.text == "📁 Kategoriyalar")
async def show_cats(m: Message):
    if not (m.from_user.id == OWNER_ID or await db.is_admin(m.from_user.id, OWNER_ID)): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Boshlang'ich", callback_data="cat_Boshlang'ich")],
        [InlineKeyboardButton(text="Yuqori sinflar", callback_data="cat_Yuqori")],
        [InlineKeyboardButton(text="BSB/CHSB", callback_data="cat_BSB_CHSB")]
    ])
    await m.answer("Kategoriyani tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("cat_"))
async def create_catalog(c: CallbackQuery):
    cat = c.data.split("_", 1)[1]
    items = await db.get_catalog(cat)
    if not items: return await c.answer("Fayllar topilmadi", show_alert=True)
    q = await db.get_setting('quarter') or "3"
    header = await db.get_setting('catalog_header') or "{quarter}-CHORAK REJALARI"
    text = f"<b>{header.format(quarter=q)}</b>\n\n"
    for i, (name, link) in enumerate(items, 1): text += f"{i}. <a href='{link}'>{name}</a>\n"
    await bot.send_message(CH_ID, text, disable_web_page_preview=True)
    await c.answer("Kanalga yuborildi!")

# --- WEB SERVER & MAIN ---
async def handle_root(request): return web.Response(text="Bot Live 🚀")

async def main():
    await db.create_tables()
    scheduler.start()
    app = web.Application()
    app.router.add_get('/', handle_root)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
