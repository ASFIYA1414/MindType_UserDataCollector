import tkinter as tk

def show_popup():
    result = {"value": None}

    def set_value(val):
        result["value"] = val
        root.destroy()

    root = tk.Tk()
    root.title("MindType Check-In")
    root.geometry("300x150")

    tk.Label(root, text="How are you feeling right now?",
             font=("Arial", 12)).pack(pady=10)

    tk.Button(root, text="Calm",
              command=lambda: set_value(0),
              width=20).pack(pady=5)

    tk.Button(root, text="Stressed",
              command=lambda: set_value(1),
              width=20).pack(pady=5)

    root.mainloop()

    return result["value"]
