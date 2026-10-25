"""Full Control - install, launch, stop, profiles, and more.

Uses the expanded AppContext API. Works with tkinter.
"""
import threading
import tkinter as tk
from tkinter import messagebox, filedialog

GUI_NAME = "My Custom GUI"


def main(context):
    root = tk.Tk()
    root.title(GUI_NAME)
    root.minsize(420, 380)
    root.geometry("420x380")

    status_var = tk.StringVar(value="Ready")
    version_var = tk.StringVar(value=f"Version: {context.version()}")
    path_var = tk.StringVar(value=str(context.game_path() or "Not set"))

    def refresh():
        version_var.set(f"Version: {context.version()}")
        path_var.set(str(context.game_path() or "Not set"))
        if context.is_running:
            status_var.set("Playing...")
        root.after(2000, refresh)

    def set_path():
        d = filedialog.askdirectory(title="Select game folder")
        if d:
            if context.set_game_path(d):
                path_var.set(d)
                status_var.set("Game path updated")

    def do_install():
        status_var.set("Installing...")
        root.update_idletasks()

        def progress(pct):
            root.after(0, lambda p=pct: status_var.set(f"Installing... {p:.0f}%"))

        def status_cb(text, level="info"):
            root.after(0, lambda t=text: status_var.set(t))

        def work():
            ok = context.install(progress=progress, status=status_cb)
            root.after(0, lambda: status_var.set("Done" if ok else "Failed"))

        threading.Thread(target=work, daemon=True).start()

    def do_launch():
        try:
            ok = context.launch()
            status_var.set("Launching..." if ok else "Launch failed")
        except Exception as e:
            status_var.set("Error")
            context.log(str(e))

    def do_stop():
        context.stop()
        status_var.set("Stopped")

    def open_logs():
        p = context.get_launcher_log_path()
        if p:
            context.open_folder(p.parent)
        else:
            context.open_folder(context.appdata_dir)

    tk.Label(root, text=GUI_NAME, font=("sans", 16, "bold")).pack(pady=(16, 2))
    tk.Label(root, textvariable=version_var).pack()
    tk.Label(root, textvariable=path_var, wraplength=380).pack(pady=4)

    btns = tk.Frame(root)
    btns.pack(pady=10)
    tk.Button(btns, text="Set Game Path", command=set_path).grid(row=0, column=0, padx=4, pady=2)
    tk.Button(btns, text="Install / Update", command=do_install).grid(row=0, column=1, padx=4, pady=2)
    tk.Button(btns, text="Launch", command=do_launch).grid(row=1, column=0, padx=4, pady=2)
    tk.Button(btns, text="Stop", command=do_stop).grid(row=1, column=1, padx=4, pady=2)
    tk.Button(btns, text="Open Logs", command=open_logs).grid(row=2, column=0, columnspan=2, padx=4, pady=6)

    profiles = tk.LabelFrame(root, text="Profiles")
    profiles.pack(fill="x", padx=16, pady=10)
    profs = context.list_profiles()
    active = context.get_active_profile()
    tk.Label(profiles, text=f"Active: {active} | Profiles: {', '.join(profs) or 'None'}").pack(padx=8, pady=6)

    tk.Label(root, textvariable=status_var).pack(side="bottom", pady=12)

    refresh()
    root.mainloop()
