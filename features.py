from pynput import keyboard
import time
import sqlite3
import threading
from queue import Queue

# --------------------------------------------
# Global State
# --------------------------------------------
current_session = 1
user_id = None
listener_instance = None
last_key_time = time.time()

IDLE_TIMEOUT = 300  # 5 minutes

event_queue = Queue()
db_thread = None
running = False


# --------------------------------------------
# Database Writer Thread
# --------------------------------------------
def db_writer():
    conn = sqlite3.connect("keystrokes.db", check_same_thread=False)
    cursor = conn.cursor()

    while running or not event_queue.empty():
        try:
            event = event_queue.get(timeout=1)
            cursor.execute("""
                INSERT INTO keystrokes
                (user_id, session_id, condition, key, event_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, event)
            conn.commit()
        except:
            continue

    conn.close()


# --------------------------------------------
# Utility Functions
# --------------------------------------------
def format_key(key):
    try:
        return key.char if key.char is not None else str(key)
    except AttributeError:
        return str(key)


def check_idle():
    global current_session, last_key_time

    if time.time() - last_key_time > IDLE_TIMEOUT:
        current_session += 1
        print(f"New session started: {current_session}")
        last_key_time = time.time()


# --------------------------------------------
# Keyboard Event Handlers
# --------------------------------------------
def on_press(key):
    global user_id, current_session, last_key_time

    if user_id is None:
        return

    check_idle()
    last_key_time = time.time()

    event_queue.put((
        user_id,
        current_session,
        None,
        format_key(key),
        "press",
        time.time()
    ))


def on_release(key):
    global user_id, current_session, last_key_time

    if user_id is None:
        return

    last_key_time = time.time()

    event_queue.put((
        user_id,
        current_session,
        None,
        format_key(key),
        "release",
        time.time()
    ))


# --------------------------------------------
# Start Listener
# --------------------------------------------
def start_listener(uid):
    global user_id, listener_instance, db_thread, running

    user_id = uid
    running = True

    # Start DB writer thread
    db_thread = threading.Thread(target=db_writer, daemon=True)
    db_thread.start()

    # Start keyboard listener
    listener_instance = keyboard.Listener(
        on_press=on_press,
        on_release=on_release
    )
    listener_instance.start()


# --------------------------------------------
# Stop Listener
# --------------------------------------------
def stop_listener():
    global running, listener_instance

    running = False

    if listener_instance:
        listener_instance.stop()

    print("Listener stopped.")
