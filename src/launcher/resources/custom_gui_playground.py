"""Status Board - a beginner dashboard built from real launcher data.

Every value on this board comes from the "context" object the launcher
hands to ``main()``. Edit the file, save it, pick this GUI in Settings >
Interface and press "Restart now" to see your changes.

Exercises (do them one at a time!):

1. Change the big title text.
2. Change the color of the square dot (see STATUS_COLOR below).
3. Make the version show a "v" in front: f"v{context.version()}".
4. Rename the "Stop game" button to "Quit game".
5. Slow the automatic refresh down: REFRESH_MS = 5000.
6. Add a label under the buttons showing the game folder:
   tk.Label(root, text=f"Folder: {context.game_path()}").pack()

If the launcher opens the builtin interface instead of yours after a
restart, your file has an error - open logs/launcher.log in the launcher
data folder to read the message.
"""
import threading
import tkinter as tk

GUI_NAME = "My Custom GUI"

STATUS_COLOR = "#26a269"   # exercise 2: try "#c01c28" (red) or "#1c71d8" (blue)
REFRESH_MS = 2000          # exercise 5: how often the board updates (ms)


def main(context):
    root = tk.Tk()
    root.title(GUI_NAME)
    root.minsize(360, 270)

    version_text = tk.StringVar()
    installed_text = tk.StringVar()
    running_text = tk.StringVar()
    latest_text = tk.StringVar(value="Press the button to check for updates")

    def refresh():
        version_text.set(f"Version:    {context.version()}")
        installed_text.set(f"Installed:  {'yes' if context.is_installed() else 'no'}")
        running_text.set("Playing right now" if context.is_running else "Idle")
        root.after(REFRESH_MS, refresh)

    def check_latest():
        latest_text.set("Checking the update server...")

        def work():
            from config import VERSION_URL     # the launcher's version file
            newest = context.network.fetch_text(VERSION_URL)
            root.after(0, lambda: on_reply(newest))

        def on_reply(newest):
            if not newest:
                latest_text.set("Could not reach the update server")
            elif newest.strip() == context.version():
                latest_text.set(f"Up to date ({newest.strip()})")
            else:
                latest_text.set(f"New version available: {newest.strip()}")

        # Network calls can be slow, so they run in a background thread.
        # root.after() brings the result safely back to the window.
        threading.Thread(target=work, daemon=True).start()

    def stop_game():
        context.stop()
        refresh()

    # exercise 1: change this text
    tk.Label(root, text="CrewLauncher Status Board",
             font=("sans", 16, "bold")).pack(pady=(18, 10))

    tk.Label(root, textvariable=version_text).pack(anchor="w", padx=30)
    tk.Label(root, textvariable=installed_text).pack(anchor="w", padx=30)

    row = tk.Frame(root)
    row.pack(anchor="w", padx=30, pady=(2, 0))
    tk.Label(row, text="Status:     ").pack(side="left")
    tk.Frame(row, width=10, height=10, bg=STATUS_COLOR).pack(side="left", padx=(0, 6))
    tk.Label(row, textvariable=running_text).pack(side="left")

    tk.Label(root, textvariable=latest_text, fg="#777777").pack(pady=(14, 0))

    buttons = tk.Frame(root)
    buttons.pack(pady=14)
    tk.Button(buttons, text="Check latest version",
              command=check_latest).pack(side="left", padx=4)
    tk.Button(buttons, text="Stop game", command=stop_game).pack(side="left", padx=4)

    refresh()
    root.mainloop()
