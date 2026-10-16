"""Quick Launch - the friendliest CrewLauncher custom GUI.

One window with one big button that starts the game. Everything on it is
real launcher data, coming from the "context" object the launcher hands to
``main()`` (see DOC/CUSTOM_GUI.md for the full list).

Try it (change one thing, save, then pick this GUI in Settings >
Interface and press "Restart now"):

1. Change the window title text below.
2. Make the button say "Play!" instead of "Launch".
3. Give the button a color: tk.Button(..., bg="#26a269", fg="white").
4. Add a small label showing where the game lives:
   tk.Label(root, text=str(context.game_path())).pack()
"""
import tkinter as tk

GUI_NAME = "My Custom GUI"


def main(context):
    root = tk.Tk()
    root.title(GUI_NAME)                 # try it 1: change this text
    root.minsize(320, 230)

    # A StringVar is a text value the labels below watch and update.
    version_text = tk.StringVar()
    status_text = tk.StringVar()

    def refresh():
        """Update version + status on the window, then look again later."""
        version_text.set(f"Game version: {context.version()}")
        if context.is_running:
            status_text.set("Playing right now")
        elif context.is_installed():
            status_text.set("Installed - ready to launch")
        else:
            status_text.set("Not installed yet")
        root.after(2000, refresh)        # check again in 2 seconds

    def launch():
        if not context.is_installed():
            status_text.set("Install it first in the Launcher Controls GUI")
            return
        status_text.set("Launching...")
        root.update_idletasks()
        try:
            ok = context.launch()
        except Exception as e:
            ok = False
            context.log(f"launch failed: {e}")
        if not ok:
            status_text.set("Launch failed - see logs/launcher.log")

    tk.Label(root, text=GUI_NAME, font=("sans", 15, "bold")).pack(pady=(20, 4))
    tk.Label(root, textvariable=version_text).pack()

    # try it 2 and 3: change the button text and colors here
    tk.Button(root, text="Launch", font=("sans", 12, "bold"),
              command=launch).pack(fill="x", padx=34, pady=16)

    tk.Label(root, textvariable=status_text, fg="#26a269").pack(pady=(0, 12))

    refresh()
    root.mainloop()
