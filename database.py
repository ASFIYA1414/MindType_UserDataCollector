import sqlite3

def init_db():
    conn = sqlite3.connect("keystrokes.db")
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
