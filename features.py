import sqlite3
import pandas as pd
import numpy as np
import os
from collections import defaultdict


# -------------------------------------------------
# Safe dataset path (Documents folder)
# -------------------------------------------------
def get_dataset_path():
    documents_path = os.path.join(os.path.expanduser("~"), "Documents")
    os.makedirs(documents_path, exist_ok=True)
    return os.path.join(documents_path, "mindtype_dataset.csv")


# -------------------------------------------------
# Feature Computation (Per Time Window)
# -------------------------------------------------
def compute_and_save_features(user_id, session_id, start_time, end_time):

    conn = sqlite3.connect("keystrokes.db")

    df = pd.read_sql_query("""
        SELECT * FROM keystrokes
        WHERE user_id = ?
        AND timestamp >= ?
        AND timestamp < ?
        ORDER BY timestamp ASC
    """, conn, params=(user_id, start_time, end_time))

    conn.close()

    if len(df) < 5:
        return None

    presses = df[df["event_type"] == "press"].copy()
    releases = df[df["event_type"] == "release"].copy()

    if len(presses) == 0 or len(releases) == 0:
        return None

    # -------------------------------------------------
    # Reliable press-release pairing
    # -------------------------------------------------
    release_dict = defaultdict(list)

    for _, row in releases.iterrows():
        release_dict[row["key"]].append(row["timestamp"])

    dwell_times = []

    for _, row in presses.iterrows():
        key = row["key"]
        press_time = row["timestamp"]

        if key in release_dict and release_dict[key]:
            release_time = release_dict[key].pop(0)

            if release_time > press_time:
                dwell_times.append(release_time - press_time)

    if len(dwell_times) == 0:
        return None

    # -------------------------------------------------
    # Core Features
    # -------------------------------------------------
    avg_hold = float(np.mean(dwell_times))
    hold_variance = float(np.var(dwell_times))

    press_times = presses["timestamp"].values
    pause_times = np.diff(press_times)

    avg_pause = float(np.mean(pause_times)) if len(pause_times) > 0 else 0.0

    duration_minutes = (end_time - start_time) / 60
    kpm = float(len(presses) / duration_minutes) if duration_minutes > 0 else 0.0

    backspace_count = presses["key"].astype(str).str.contains(
        "backspace", case=False
    ).sum()

    backspace_rate = float(backspace_count / len(presses)) if len(presses) > 0 else 0.0

    # -------------------------------------------------
    # Row for dataset
    # -------------------------------------------------
    row = {
        "user_id": user_id,
        "avg_hold": avg_hold,
        "hold_variance": hold_variance,
        "avg_pause": avg_pause,
        "kpm": kpm,
        "backspace_rate": backspace_rate,
        "stress_level": None
    }

    df_out = pd.DataFrame([row])

    file_path = get_dataset_path()
    file_exists = os.path.isfile(file_path)

    try:
        df_out.to_csv(
            file_path,
            mode="a",
            header=not file_exists,
            index=False
        )
    except PermissionError:
        print("⚠ Close mindtype_dataset.csv before running.")
        return None

    return row


# -------------------------------------------------
# Update Last N Rows With Stress Label
# -------------------------------------------------
def update_last_n_labels(label, n=2):

    file_path = get_dataset_path()

    if not os.path.isfile(file_path):
        return

    try:
        df = pd.read_csv(file_path)
    except Exception:
        print("⚠ Could not read dataset file.")
        return

    if len(df) == 0:
        return

    start_index = max(len(df) - n, 0)
    df.loc[start_index:, "stress_level"] = label

    try:
        df.to_csv(file_path, index=False)
    except PermissionError:
        print("⚠ Close mindtype_dataset.csv before updating labels.")
