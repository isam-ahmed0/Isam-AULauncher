import customtkinter as ctk

ctk.set_appearance_mode("dark")

app = ctk.CTk()
app.title("CustomTkinter Test")
app.geometry("400x300")

label = ctk.CTkLabel(app, text="Hello, CustomTkinter!")
label.pack(pady=20)

button = ctk.CTkButton(app, text="Click Me", command=lambda: print("Button Clicked!"))
button.pack(pady=20)
button.pack()

app.mainloop()