import sqlite3

class Database:
    def __init__(self, db_name="bot_system.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Adminlar
        self.cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, role TEXT)")
        # Fayllar ombori
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                category TEXT,
                grade TEXT,
                link TEXT
            )
        """)
        # Sozlamalar
        self.cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        self.cursor.execute("INSERT OR IGNORE INTO settings VALUES ('quarter', '2-chorak')")
        self.conn.commit()

    def add_file(self, name, cat, grade, link):
        self.cursor.execute("INSERT INTO file_links (file_name, category, grade, link) VALUES (?, ?, ?, ?)", (name, cat, grade, link))
        self.conn.commit()

    def get_files(self, category):
        return self.cursor.execute("SELECT file_name, grade, link FROM file_links WHERE category = ?", (category,)).fetchall()

    def clear_database(self):
        self.cursor.execute("DELETE FROM file_links")
        self.conn.commit()
