from database import init_db
from listener import start_listener, stop_listener
from features import compute_and_save_features, update_last_n_labels
from popup import show_popup

import time
import tkinter as tk


# --------------------------------------------
# USER ID SETUP WINDOW
# --------------------------------------------
def get_user_id():
    result = {"value": None}

    def submit():
        value = entry.get().strip()
        if value:
            result["value"] = value
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


# --------------------------------------------
# MAIN PROGRAM
# --------------------------------------------
def main():
    init_db()

    user_id = get_user_id()

    if not user_id:
        print("Invalid User ID. Exiting.")
        return

    start_listener(user_id)

    print("Monitoring started...")

    session_start = time.time()
    window_index = 0

    # -----------------------------
    # Drift Baseline Initialization
    # -----------------------------
    baseline = {
        "avg_hold": None,
        "avg_pause": None,
        "kpm": None,
        "backspace_rate": None
    }

    BASELINE_ALPHA = 0.2
    DRIFT_THRESHOLD = 1.5   # Adjusted for normalized drift
    last_popup_time = 0
    POPUP_COOLDOWN = 450  # seconds

    try:
        while True:
            current_time = time.time()

            # Every 60 seconds compute features
            if current_time >= session_start + (window_index + 1) * 60:

                window_start = session_start + window_index * 60
                window_end = window_start + 60

                # NOTE: session_id removed (fixes mismatch bug)
                features = compute_and_save_features(
                    user_id,
                    session_id=None,  # ignored internally
                    start_time=window_start,
                    end_time=window_end
                )

                if features is not None:

                    # -----------------------------
                    # Initialize baseline
                    # -----------------------------
                    if baseline["avg_hold"] is None:
                        baseline = {
                            "avg_hold": features["avg_hold"],
                            "avg_pause": features["avg_pause"],
                            "kpm": features["kpm"],
                            "backspace_rate": features["backspace_rate"]
                        }

                    else:
                        # -----------------------------
                        # Normalized Drift Calculation
                        # -----------------------------
                        drift_score = (
                            abs((features["avg_hold"] - baseline["avg_hold"]) / (baseline["avg_hold"] + 1e-6)) +
                            abs((features["avg_pause"] - baseline["avg_pause"]) / (baseline["avg_pause"] + 1e-6)) +
                            abs((features["kpm"] - baseline["kpm"]) / (baseline["kpm"] + 1e-6)) +
                            abs((features["backspace_rate"] - baseline["backspace_rate"]) /
                                (baseline["backspace_rate"] + 1e-6))
                        )

                        print("Drift score:", round(drift_score, 3))

                        # -----------------------------
                        # Update baseline using EMA
                        # -----------------------------
                        for key in baseline:
                            baseline[key] = (
                                BASELINE_ALPHA * features[key] +
                                (1 - BASELINE_ALPHA) * baseline[key]
                            )

                        # -----------------------------
                        # Trigger Popup if drift detected
                        # -----------------------------
                        if drift_score > DRIFT_THRESHOLD and \
                           current_time - last_popup_time > POPUP_COOLDOWN:

                            label = show_popup()

                            if label is not None:
                                update_last_n_labels(label, n=2)

                            last_popup_time = current_time

                window_index += 1

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
        stop_listener()


# --------------------------------------------
# ENTRY POINT
# --------------------------------------------
if __name__ == "__main__":
    main()

