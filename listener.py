from pynput import keyboard
import time
import sqlite3
from database import get_db_path

# ----------------------------------------
# GLOBAL STATE
# ----------------------------------------

current_session = int(time.time())
user_id = None
listener_instance = None
last_key_time = time.time()

conn = None
cursor = None

IDLE_TIMEOUT = 300


# ----------------------------------------
# INSERT EVENT INTO DATABASE
# ----------------------------------------
def insert_event(user_id, session_id, key, event_type, timestamp):

    global cursor, conn

    cursor.execute("""
        INSERT INTO keystrokes
        (user_id, session_id, condition, key, event_type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, session_id, None, key, event_type, timestamp))

    conn.commit()


# ----------------------------------------
# FORMAT KEY
# ----------------------------------------
def format_key(key):
    try:
        return key.char
    except AttributeError:
        return str(key)


# ----------------------------------------
# CHECK FOR IDLE SESSION
# ----------------------------------------
def check_idle():
    global current_session, last_key_time

    if time.time() - last_key_time > IDLE_TIMEOUT:
        current_session = int(time.time())
        print(f"New session started: {current_session}")
        last_key_time = time.time()


# ----------------------------------------
# KEY PRESS EVENT
# ----------------------------------------
def on_press(key):
    global user_id, current_session, last_key_time

    if user_id is None:
        return

    check_idle()
    last_key_time = time.time()

    insert_event(
        user_id,
        current_session,
        format_key(key),
        "press",
        time.time()
    )


# ----------------------------------------
# KEY RELEASE EVENT
# ----------------------------------------
def on_release(key):
    global user_id, current_session, last_key_time

    if user_id is None:
        return

    last_key_time = time.time()

    insert_event(
        user_id,
        current_session,
        format_key(key),
        "release",
        time.time()
    )


# ----------------------------------------
# START LISTENER
# ----------------------------------------
def start_listener(uid):
    global user_id, listener_instance, conn, cursor

    user_id = uid

    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    cursor = conn.cursor()

    listener_instance = keyboard.Listener(
        on_press=on_press,
        on_release=on_release
    )

    listener_instance.start()


# ----------------------------------------
# STOP LISTENER
# ----------------------------------------
def stop_listener():
    global listener_instance, conn

    if listener_instance:
        listener_instance.stop()

    if conn:
        conn.close()