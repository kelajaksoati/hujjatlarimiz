import aiosqlite

class Database:
    def __init__(self, db_path="bot_database.db"):
        self.db_path = db_path

    async def create_tables(self):
        """Baza jadvallarini yaratish va boshlang'ich sozlamalarni kiritish"""
        async with aiosqlite.connect(self.db_path) as db:
            # Katalog jadvali
            await db.execute("""
                CREATE TABLE IF NOT EXISTS catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    name TEXT, 
                    category TEXT, 
                    link TEXT, 
                    msg_id INTEGER
                )
            """)
            # Sozlamalar jadvali
            await db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            # Adminlar jadvali
            await db.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
            
            # Standart sozlamalar
            defaults = [
                ('quarter', '1-CHORAK'),
                ('post_caption', "📚 <b>{name}</b>\n\n✅ Kanal: @{channel}"),
                ('footer_text', "\n\n📩 Murojaat: @admin_user"),
                ('catalog_header', "📂 <b>FANLARDAN {quarter} ISH REJALARI</b>")
            ]
            
            for key, val in defaults:
                await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))
            
            await db.commit()

    async def get_setting(self, key):
        """Sozlamalarni kalit bo'yicha olish"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else ""

    async def update_setting(self, key, value):
        """Sozlamalarni yangilash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
            await db.commit()

    async def is_admin(self, user_id, owner_id):
        """Foydalanuvchi admin yoki egaligini tekshirish"""
        if user_id == owner_id:
            return True
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cursor:
                res = await cursor.fetchone()
                return res is not None

    async def add_admin(self, user_id):
        """Yangi admin qo'shish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
            await db.commit()

    # --- SIZ QO'SHGAN YANGI FUNKSIYA ---
    async def get_admins(self):
        """Barcha adminlar ID raqamlarini olish"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id FROM admins") as cursor:
                return await cursor.fetchall()

    async def get_stats(self):
        """Katalogdagi fayllar sonini olish"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM catalog") as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 0

    async def add_to_catalog(self, name, category, link, msg_id):
        """Yangi faylni katalogga qo'shish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO catalog (name, category, link, msg_id) VALUES (?, ?, ?, ?)", 
                (name, category, link, msg_id)
            )
            await db.commit()

    async def get_catalog(self, category):
        """Kategoriya bo'yicha barcha fayllarni olish"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT name, link FROM catalog WHERE category = ?", (category,)) as cursor:
                return await cursor.fetchall()

    async def clear_catalog(self):
        """Katalogni tozalash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM catalog")
            await db.commit()
