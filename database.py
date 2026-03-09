import sqlite3
import os

def get_db_path():
    documents = os.path.join(os.path.expanduser("~"), "Documents")
    os.makedirs(documents, exist_ok=True)
    return os.path.join(documents, "keystrokes.db")


def init_db():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keystrokes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        session_id INTEGER,
        condition TEXT,
        key TEXT,
        event_type TEXT,
        timestamp REAL
    )
    """)
    conn.commit()
    conn.close()
    print("Database path:", get_db_path())
