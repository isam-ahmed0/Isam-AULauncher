import time
import os
import sys

def main(context):
    NAME = context.APP_NAME

    def clear_c():
        os.system("cls" if os.name == "nt" else "clear")

    while True:
        clear_c()
        # context.discord.connect()
        # context.discord.update_status(state=NAME, details="In CLI")
        print(NAME)
        print("1. Launch")
        print("2. Install")
        print("0. Exit")
        choose = input("Choose: ")

        if choose == "1":
            clear_c()
            if context.is_installed() == False:
                print("Install the game..")
            else: 
                print("Launching...")
                context.launch()
            input("Enter to continue")
            
        elif choose == "2":
            pass

        elif choose == "3":
            print("Stopping...")
            if context.is_running == True:
                context.stop()
                print("stopped")
            else:
                print("not running")
            input("Enter to continue")
        
        elif choose == "0":
            break