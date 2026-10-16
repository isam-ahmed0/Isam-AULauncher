"""Minimal Starter - the simplest possible CrewLauncher custom GUI.

First exercises (change one thing at a time, save, then pick this GUI in
Settings > Interface and press "Restart now"):

1. Change the text on the label below.
2. Change the button text from "Quit" to "Goodbye".
3. Add a second label that shows context.version().

See DOC/CUSTOM_GUI.md for the full context API.
"""
import tkinter as tk

GUI_NAME = "My Custom GUI"


def main(context):
    root = tk.Tk()
    root.title(GUI_NAME)

    tk.Label(
        root,
        text="Hello! I made my own launcher GUI.",
        font=("sans", 14),
    ).pack(padx=30, pady=(30, 10))

    tk.Button(root, text="Quit", command=root.destroy).pack(pady=(0, 30))

    root.mainloop()
