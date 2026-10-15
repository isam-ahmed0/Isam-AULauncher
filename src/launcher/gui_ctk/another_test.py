import subprocess
import customtkinter as ctk


def run_terminal_command(command):
    subprocess.Popen(command)


command = run_terminal_command

ctk.set_appearance_mode("dark")

app = ctk.CTk()
app.title("Hello! Test")
app.geometry("720x500")

label = ctk.CTkLabel(app, text="Helllllllloooo")
label.pack(pady=30)

button = ctk.CTkButton(app, text="Launch lutris", command=lambda: command("lutris"))
button.pack(pady=20)
button.pack()


app.mainloop()