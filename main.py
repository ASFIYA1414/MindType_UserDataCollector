from database import init_db
from listener import start_listener
from features import compute_and_save_features, update_last_n_labels
from popup import show_popup
import time
import tkinter as tk

def get_user_id():
    result = {"value": None}

    def submit():
        result["value"] = entry.get()
        root.destroy()

    root = tk.Tk()
    root.title("MindType Setup")
    root.geometry("300x150")

    tk.Label(root, text="Enter your User ID:").pack(pady=10)

    entry = tk.Entry(root)
    entry.pack(pady=5)

    tk.Button(root, text="Start Monitoring", command=submit).pack(pady=10)

    root.mainloop()

    return result["value"]


def main():
    init_db()

    user_id = get_user_id()
    session_id = 1

    start_listener(user_id)

    print("Monitoring started...")

    session_start = time.time()
    window_index = 0

    # Drift system
    baseline = {
        "avg_hold": None,
        "avg_pause": None,
        "kpm": None,
        "backspace_rate": None
    }

    BASELINE_ALPHA = 0.2
    DRIFT_THRESHOLD = 0.5
    last_popup_time = 0
    POPUP_COOLDOWN = 120  # seconds

    try:
        while True:
            current_time = time.time()

            if current_time >= session_start + (window_index + 1) * 60:
                window_start = session_start + window_index * 60
                window_end = window_start + 60

                features = compute_and_save_features(
                    user_id,
                    session_id,
                    window_start,
                    window_end
                )

                if features is not None:

                    # Initialize baseline
                    if baseline["avg_hold"] is None:
                        baseline["avg_hold"] = features["avg_hold"]
                        baseline["avg_pause"] = features["avg_pause"]
                        baseline["kpm"] = features["kpm"]
                        baseline["backspace_rate"] = features["backspace_rate"]

                    # Compute drift score
                    drift_score = (
                        abs(features["avg_hold"] - baseline["avg_hold"]) +
                        abs(features["avg_pause"] - baseline["avg_pause"]) +
                        abs(features["kpm"] - baseline["kpm"]) / 100 +
                        abs(features["backspace_rate"] - baseline["backspace_rate"])
                    )

                    print("Drift score:", drift_score)

                    # Update baseline (EMA)
                    baseline["avg_hold"] = (
                        BASELINE_ALPHA * features["avg_hold"] +
                        (1 - BASELINE_ALPHA) * baseline["avg_hold"]
                    )

                    baseline["avg_pause"] = (
                        BASELINE_ALPHA * features["avg_pause"] +
                        (1 - BASELINE_ALPHA) * baseline["avg_pause"]
                    )

                    baseline["kpm"] = (
                        BASELINE_ALPHA * features["kpm"] +
                        (1 - BASELINE_ALPHA) * baseline["kpm"]
                    )

                    baseline["backspace_rate"] = (
                        BASELINE_ALPHA * features["backspace_rate"] +
                        (1 - BASELINE_ALPHA) * baseline["backspace_rate"]
                    )

                    # Drift-triggered popup
                    if drift_score > DRIFT_THRESHOLD and \
                       current_time - last_popup_time > POPUP_COOLDOWN:

                        label = show_popup()
                        update_last_n_labels(label, n=2)
                        last_popup_time = current_time

                window_index += 1

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


if __name__ == "__main__":
    main()
