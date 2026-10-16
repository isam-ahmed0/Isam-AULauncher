"""Python Playground - learn Python by editing this file!

Everything here runs for real. Edit the file, save it, pick this GUI in
Settings > Interface and press "Restart now" to see your changes.

Do the exercises in order, one small change at a time:

1. Change the greeting text below.
2. Press the "+1" button a few times and find where the number is stored.
3. Make the counter start at 10 instead of 0.
4. Make the "+1" button add 5 instead of 1.
5. Type your name in the box and press "Hello!".
6. Uncomment the LOOP EXAMPLE near the bottom to draw many labels at once.

If the launcher opens the builtin interface instead of yours after a
restart, your file has an error - open logs/launcher.log in the launcher
data folder to read the message.
"""
import tkinter as tk

GUI_NAME = "My Custom GUI"   # <- your name here, it shows up in Settings


def main(context):
    root = tk.Tk()
    root.title(GUI_NAME)

    # ---------------------------------------------------------------------
    # Ex. 1: a "label" shows text. Try changing these words:
    greeting = tk.Label(root, text="Hello, Python explorer!", font=("sans", 15))
    greeting.pack(padx=25, pady=(20, 10))

    # ---------------------------------------------------------------------
    # Ex. 2-4: a "variable" remembers a value. This one remembers a number.
    # Change 0 to 10 to start counting from ten:
    count = 0

    # A "StringVar" is a special variable that labels can watch:
    counter_text = tk.StringVar(value=f"Count: {count}")

    def add_one():
        # "global" lets us change the "count" variable from inside a function
        global count
        count = count + 1              # <- Ex. 4: change 1 to 5
        counter_text.set(f"Count: {count}")

    tk.Label(root, textvariable=counter_text).pack()
    tk.Button(root, text="+1", width=10, command=add_one).pack(pady=4)

    # ---------------------------------------------------------------------
    # Ex. 5: an "entry" is a text box. "if / else" makes decisions:
    name_box = tk.Entry(root, width=24)
    name_box.pack(pady=(14, 2))

    answer_text = tk.StringVar(value="")

    def say_hello():
        name = name_box.get().strip()
        if name == "":
            answer_text.set("Please type a name first!")
        else:
            answer_text.set(f"Nice to meet you, {name}!")

    tk.Button(root, text="Hello!", width=10, command=say_hello).pack()
    tk.Label(root, textvariable=answer_text, fg="#26a269").pack(pady=(4, 10))

    # ---------------------------------------------------------------------
    # Bonus: the launcher hands you information through "context". This
    # label shows which game version your launcher manages right now:
    tk.Label(root, text=f"Game version: {context.version()}").pack()

    # ---------------------------------------------------------------------
    # Ex. 6: LOOP EXAMPLE - uncomment (remove the "# ") these two lines:
    # for i in range(5):
    #     tk.Label(root, text=f"Row number {i}").pack()

    # Always leave a way to close your GUI:
    tk.Button(root, text="Close", command=root.destroy).pack(pady=(14, 20))

    root.mainloop()
