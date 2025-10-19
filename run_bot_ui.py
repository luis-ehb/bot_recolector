# run_bot_ui.py
import os
import tkinter as tk
from bot_ui import BotUI  # tu interfaz que ya integra config y botones

if __name__ == "__main__":
    root = tk.Tk()
    app = BotUI(root)
    root.mainloop()
