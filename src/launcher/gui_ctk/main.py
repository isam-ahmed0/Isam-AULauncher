# Requires CustomTkinter:  pip install customtkinter
import subprocess
import customtkinter as ctk
import tkinter as tk
# Requires Pillow:  pip install pillow
from PIL import Image


THEME_BG = "#2b2b2b"
THEME_FG = "#e8e8e8"
THEME_ACCENT = "#26a269"
THEME_ACCENT_FG = "#ffffff"
THEME_FIELD_BG = "#3c3c3c"
THEME_FONT_FAMILY = "Segoe UI"
THEME_FONT_SIZE = 10

def launch_game(command):
    subprocess.Popen(command)


def apply_theme(root):
    """Apply the project theme to a window. CustomTkinter styles per widget,
    so the widgets themselves carry the rest of the colours."""
    root.configure(fg_color=THEME_BG)


class Main:
    def __init__(self, root):
        self.root = root
        root.title("Main")
        root.geometry("520x380")
        apply_theme(root)

        self.GName = ctk.CTkLabel(root, text="Among Us", text_color=THEME_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=90, height=26)
        self.GName.place(x=0, y=30)

        self.APP_NAME = ctk.CTkTextbox(root, fg_color=THEME_FIELD_BG, text_color=THEME_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=90, height=30)
        self.APP_NAME.place(x=0, y=0)

        # Kept on self, or Python garbage-collects it and the image goes blank.
        #self.IMAGE_image = ctk.CTkImage(Image.open("image.png"), size=(160, 120))
        #self.IMAGE = ctk.CTkLabel(root, text="", image=self.IMAGE_image)
        #self.IMAGE.place(x=340, y=15, width=160, height=120)

        self.LAUNCHBTN = ctk.CTkButton(root, text="Launch", command=lambda: launch_game("lutris"), fg_color=THEME_ACCENT, text_color=THEME_ACCENT_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=96, height=32)
        self.LAUNCHBTN.place(x=10, y=119)

        self.INSTALLBTN = ctk.CTkButton(root, text="Install", command=lambda: launch_game("lutris"), fg_color=THEME_ACCENT, text_color=THEME_ACCENT_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=96, height=32)
        self.INSTALLBTN.place(x=10, y=75)

    def open_settings(self):
        return Settings(self.root)

    def launch_game(self):
        pass

    def insatll_game(self):
        pass


class Settings:
    def __init__(self, master):
        root = ctk.CTkToplevel(master)
        self.root = root
        root.title("Settings")
        root.geometry("520x380")
        apply_theme(root)

        self.launch_with_var = tk.IntVar()
        self.switch2_var = tk.IntVar()
        self.switch3_var = tk.IntVar()
        self.switch4_var = tk.IntVar()

        self.settings = ctk.CTkLabel(root, text="Settings", text_color=THEME_FG, font=ctk.CTkFont(family=THEME_FONT_FAMILY, size=THEME_FONT_SIZE), width=110, height=40)
        self.settings.place(x=200, y=20)

        self.launch_with = ctk.CTkSwitch(root, text="Enabled", variable=self.launch_with_var, command=self.launch_with, width=120, height=28)
        self.launch_with.place(x=30, y=70)

        self.switch2 = ctk.CTkSwitch(root, text="Enabled", variable=self.switch2_var, width=120, height=28)
        self.switch2.place(x=120, y=130)

        self.switch3 = ctk.CTkSwitch(root, text="Enabled", variable=self.switch3_var, width=120, height=28)
        self.switch3.place(x=110, y=200)

        self.switch4 = ctk.CTkSwitch(root, text="Enabled", variable=self.switch4_var, width=120, height=28)
        self.switch4.place(x=240, y=170)

    def launch_with(self):
        pass


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    app = Main(root)
    root.mainloop()
