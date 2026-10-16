"""My Custom GUI - CrewLauncher user interface template.

This file runs with the same Python that runs CrewLauncher and receives a
``context`` object with the launcher backends. You may build ANY kind of
interface here: tkinter, a command line tool, a web server... Only the
Python standard library is guaranteed - customtkinter/PySide6 may not be
installed on every machine.

Contract
--------
- ``GUI_NAME``: shown in CrewLauncher's Settings > Interface list.
- ``main(context)``: called by the launcher. When it returns, the app exits.

Context API (see DOC/CUSTOM_GUI.md for details)
-----------------------------------------------
- context.config            : Config (settings, paths, game path...)
- context.network           : NetworkManager (fetch_text, get_releases...)
- context.discord           : DiscordRPC (connect/update_status/disconnect)
- context.game              : GameCore (raw backend)
- context.version()         : installed version string
- context.game_path()       : Path or None
- context.is_installed()    : bool
- context.is_running        : bool
- context.install(progress=, status=) : download/update, bool
- context.launch() / context.stop() / context.poll()
- context.log(message)      : write to the launcher log
"""
import tkinter as tk
from tkinter import messagebox

GUI_NAME = "My Custom GUI"


def main(context):
    root = tk.Tk()
    root.title(GUI_NAME)
    root.minsize(360, 260)

    status = tk.StringVar(value="Ready")
    version = tk.StringVar(value=f"Version: {context.version()}")

    def refresh():
        version.set(f"Version: {context.version()}")
        if context.is_running:
            status.set("Playing...")

    def do_install():
        status.set("Installing...")
        root.update_idletasks()

        def progress(pct):
            root.after(0, lambda p=pct: status.set(f"Installing... {p:.0f}%"))

        def status_cb(text, level="info"):
            root.after(0, lambda t=text: status.set(t))

        def work():
            ok = context.install(progress=progress, status=status_cb)
            root.after(0, lambda: on_done(ok))

        def on_done(ok):
            refresh()
            if not ok:
                messagebox.showerror(GUI_NAME, "Install failed - see the launcher log.")

        import threading
        threading.Thread(target=work, daemon=True).start()

    def do_launch():
        try:
            ok = context.launch()
        except Exception as e:
            ok = False
            context.log(f"launch error: {e}")
        if ok:
            status.set("Launching...")
        else:
            messagebox.showwarning(
                GUI_NAME,
                "Could not launch.\n\nIs the game installed and Wine configured?\n"
                "(Settings > Graphics in the builtin interface.)")

    def do_stop():
        context.stop()
        status.set("Stopped")

    def poll():
        refresh()
        root.after(2000, poll)

    tk.Label(root, text=GUI_NAME, font=("sans", 16)).pack(padx=20, pady=(20, 4))
    tk.Label(root, textvariable=version).pack()
    tk.Button(root, text="Install / Update", command=do_install).pack(fill="x", padx=20, pady=4)
    tk.Button(root, text="Launch", command=do_launch).pack(fill="x", padx=20, pady=4)
    tk.Button(root, text="Stop", command=do_stop).pack(fill="x", padx=20, pady=4)
    tk.Label(root, textvariable=status, fg="#26a269").pack(padx=20, pady=(8, 16))

    poll()
    root.mainloop()


if __name__ == "__main__":
    print("This file is a CrewLauncher custom GUI template.")
    print("Copy it into <appdata>/IsamAULauncher/guis/ and run the launcher.")
