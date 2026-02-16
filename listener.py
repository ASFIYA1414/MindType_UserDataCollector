from pynput import keyboard
import time
import sqlite3

current_session = 1
user_id = None
listener_instance = None
last_key_time = time.time()

IDLE_TIMEOUT = 300  # 5 minutes


def insert_event(user_id, session_id, key, event_type, timestamp):
    conn = sqlite3.connect("keystrokes.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO keystrokes
        (user_id, session_id, condition, key, event_type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, session_id, None, key, event_type, timestamp))

    conn.commit()
    conn.close()


def format_key(key):
    try:
        return key.char
    except AttributeError:
        return str(key)


def check_idle():
    global current_session, last_key_time

    if time.time() - last_key_time > IDLE_TIMEOUT:
        current_session += 1
        print(f"New session started: {current_session}")
        last_key_time = time.time()


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


def start_listener(uid):
    global user_id, listener_instance
    user_id = uid

    listener_instance = keyboard.Listener(
        on_press=on_press,
        on_release=on_release
    )

    listener_instance.start()


def stop_listener():
    global listener_instance
    if listener_instance:
        listener_instance.stop()
