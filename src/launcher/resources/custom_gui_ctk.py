"""Modern Panel - a rounded dark CrewLauncher GUI made with customtkinter.

customtkinter is a friendly wrapper around tkinter with modern-looking
widgets. Official CrewLauncher builds include it; if Settings > Interface
shows "(unavailable: missing customtkinter)" you are running from source -
install it with:  pip install customtkinter

Same contract as every custom GUI: ``GUI_NAME`` is shown in Settings and
``main(context)`` is called by the launcher (exiting when it returns).

Try it: change the colors below ("#2ecc71" is green, "#c0392b" is red) or
add a button that calls context.stop().
"""
import threading

import customtkinter as ctk

GUI_NAME = "My Custom GUI"


def main(context):
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title(GUI_NAME)
    root.geometry("400x340")

    title = ctk.CTkLabel(root, text=GUI_NAME,
                         font=ctk.CTkFont(size=20, weight="bold"))
    title.pack(pady=(26, 4))

    version = ctk.CTkLabel(root, text=f"Version: {context.version()}")
    version.pack()

    status = ctk.CTkLabel(root, text="Ready", text_color="#2ecc71")
    status.pack(pady=(6, 14))

    progress = ctk.CTkProgressBar(root, width=310)
    progress.set(0)
    progress.pack(pady=(0, 16))

    def refresh():
        version.configure(text=f"Version: {context.version()}")
        if context.is_running:
            status.configure(text="Playing right now")
        root.after(2000, refresh)

    def install():
        status.configure(text="Installing...")

        def on_progress(pct):
            # callbacks can come from a worker thread; hop back to the GUI
            root.after(0, lambda p=pct: progress.set(p / 100.0))

        def on_status(text, level="info"):
            root.after(0, lambda t=text: status.configure(text=t))

        def work():
            ok = context.install(progress=on_progress, status=on_status)
            done = "Update finished!" if ok else "Install failed - see logs/launcher.log"
            root.after(0, lambda: status.configure(text=done))

        threading.Thread(target=work, daemon=True).start()

    def launch():
        status.configure(text="Launching...")
        root.update_idletasks()
        try:
            ok = context.launch()
        except Exception as e:
            ok = False
            context.log(f"launch failed: {e}")
        if not ok:
            status.configure(text="Launch failed - check Wine in Settings")

    def stop():
        context.stop()
        status.configure(text="Stopped")

    buttons = ctk.CTkFrame(root, fg_color="transparent")
    buttons.pack(pady=(4, 20))
    ctk.CTkButton(buttons, text="Install / Update", width=120,
                  command=install).pack(side="left", padx=5)
    ctk.CTkButton(buttons, text="Launch", width=90,
                  command=launch).pack(side="left", padx=5)
    ctk.CTkButton(buttons, text="Stop", width=90, fg_color="#c0392b",
                  hover_color="#922b21", command=stop).pack(side="left", padx=5)

    refresh()
    root.mainloop()
