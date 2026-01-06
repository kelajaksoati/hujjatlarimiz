import aiosqlite

class Database:
    def __init__(self, db_path="bot_database.db"):
        self.db_path = db_path

    async def create_tables(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Fayllar va sozlamalar bazasi
            await db.execute("CREATE TABLE IF NOT EXISTS catalog (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT, link TEXT, msg_id INTEGER)")
            await db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            
            # Standart shablonlar
            defaults = [
                ('quarter', '1-CHORAK'),
                ('post_caption', "📚 {name}\n\n#namuna\n#taqvim_mavzu_reja\n📘EMAKTAB.UZ uchun\n✅Kanal: @{channel}"),
                ('catalog_header', "FANLARDAN {quarter} ISH REJALARI\n\n✅Tanlang:")
            ]
            for key, val in defaults:
                await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))
            await db.commit()

    async def get_setting(self, key):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else ""

    async def add_to_catalog(self, name, category, link, msg_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO catalog (name, category, link, msg_id) VALUES (?, ?, ?, ?)", (name, category, link, msg_id))
            await db.commit()

    async def get_catalog(self, category):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id, name, link FROM catalog WHERE category = ?", (category,)) as cursor:
                return await cursor.fetchall()

    async def clear_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM catalog")
            await db.commit()
