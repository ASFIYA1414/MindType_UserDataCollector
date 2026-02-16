import sqlite3
import pandas as pd
import numpy as np
import os


def compute_and_save_features(user_id, session_id, start_time, end_time):
    conn = sqlite3.connect("keystrokes.db")

    df = pd.read_sql_query("""
        SELECT * FROM keystrokes
        WHERE user_id = ?
        AND session_id = ?
        AND timestamp >= ?
        AND timestamp < ?
        ORDER BY timestamp ASC
    """, conn, params=(user_id, session_id, start_time, end_time))

    conn.close()

    if len(df) < 5:
        return None

    presses = df[df["event_type"] == "press"].copy()
    releases = df[df["event_type"] == "release"].copy()

    dwell_times = []

    for i in range(len(presses)):
        key = presses.iloc[i]["key"]
        press_time = presses.iloc[i]["timestamp"]

        matching_release = releases[
            (releases["key"] == key) &
            (releases["timestamp"] > press_time)
        ]

        if not matching_release.empty:
            release_time = matching_release.iloc[0]["timestamp"]
            dwell_times.append(release_time - press_time)

    if len(dwell_times) == 0:
        return None

    avg_hold = np.mean(dwell_times)
    hold_variance = np.var(dwell_times)

    press_times = presses["timestamp"].values
    pause_times = np.diff(press_times)

    avg_pause = np.mean(pause_times) if len(pause_times) > 0 else 0

    duration_minutes = (end_time - start_time) / 60
    kpm = len(presses) / duration_minutes if duration_minutes > 0 else 0

    backspace_count = presses["key"].astype(str).str.contains("backspace", case=False).sum()
    backspace_rate = backspace_count / len(presses)

    row = {
        "user_id": user_id,
        "session_id": session_id,
        "avg_hold": avg_hold,
        "hold_variance": hold_variance,
        "avg_pause": avg_pause,
        "kpm": kpm,
        "backspace_rate": backspace_rate,
        "stress_level": None
    }

    df_out = pd.DataFrame([row])

    file_exists = os.path.isfile("mindtype_dataset.csv")

    df_out.to_csv(
        "mindtype_dataset.csv",
        mode="a",
        header=not file_exists,
        index=False
    )

    return row


def update_last_n_labels(label, n=2):
    df = pd.read_csv("mindtype_dataset.csv")

    if len(df) == 0:
        return

    start_index = max(len(df) - n, 0)

    df.loc[start_index:, "stress_level"] = label

    df.to_csv("mindtype_dataset.csv", index=False)
