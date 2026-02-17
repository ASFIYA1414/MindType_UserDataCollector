import tkinter as tk


def show_popup():

    result = {"value": None}

    def set_value(val):
        result["value"] = val
        root.destroy()

    root = tk.Tk()
    root.title("MindType Check-In")
    root.geometry("350x250")
    root.resizable(False, False)

    tk.Label(
        root,
        text="How are you feeling right now?",
        font=("Arial", 12)
    ).pack(pady=15)

    buttons = [
        ("Very Calm", 1),
        ("Slightly Calm", 2),
        ("Neutral", 3),
        ("Stressed", 4),
        ("Very Stressed", 5),
    ]

    for text, value in buttons:
        tk.Button(
            root,
            text=text,
            width=25,
            command=lambda v=value: set_value(v)
        ).pack(pady=4)

    # Optional: auto-close after 30 seconds (avoid hanging)
    root.after(30000, root.destroy)

    root.mainloop()

    return result["value"]

