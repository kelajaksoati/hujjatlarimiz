import sqlite3

class Database:
    def __init__(self, db_name="bot_system.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, role TEXT DEFAULT 'admin')")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        # Mundarija uchun yangi jadval
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                category TEXT,
                link TEXT
            )
        """)
        self.cursor.execute("INSERT OR IGNORE INTO settings VALUES ('quarter', '2-chorak')")
        self.conn.commit()

    def add_to_catalog(self, name, cat, link):
        self.cursor.execute("INSERT INTO catalog (file_name, category, link) VALUES (?, ?, ?)", (name, cat, link))
        self.conn.commit()

    def get_catalog(self, cat):
        return self.cursor.execute("SELECT file_name, link FROM catalog WHERE category = ?", (cat,)).fetchall()

    def clear_all_data(self):
        self.cursor.execute("DELETE FROM catalog")
        self.conn.commit()

    def is_admin(self, user_id, super_admin):
        if user_id == super_admin: return True
        res = self.cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return res is not None

    def get_quarter(self):
        return self.cursor.execute("SELECT value FROM settings WHERE key = 'quarter'").fetchone()[0]
