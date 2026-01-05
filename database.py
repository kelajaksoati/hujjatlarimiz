import aiosqlite

class Database:
    def __init__(self, db_path="bot_database.db"):
        self.db_path = db_path

    async def create_tables(self):
        """Ma'lumotlar bazasi jadvallarini yaratish."""
        async with aiosqlite.connect(self.db_path) as db:
            # Fayllar mundarijasi uchun jadval
            await db.execute("""
                CREATE TABLE IF NOT EXISTS catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    category TEXT,
                    link TEXT
                )
            """)
            # Sozlamalar (chorak va h.k.) uchun jadval
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            # Standart chorakni o'rnatish
            await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('quarter', '2-CHORAK')")
            await db.commit()

    async def add_to_catalog(self, name, category, link):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO catalog (name, category, link) VALUES (?, ?, ?)", 
                             (name, category, link))
            await db.commit()

    async def get_catalog(self, category):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT name, link FROM catalog WHERE category = ?", (category,)) as cursor:
                return await cursor.fetchall()

    async def set_quarter(self, quarter_name):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE settings SET value = ? WHERE key = 'quarter'", (quarter_name,))
            await db.commit()

    async def get_quarter(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT value FROM settings WHERE key = 'quarter'") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else "3-CHORAK"
