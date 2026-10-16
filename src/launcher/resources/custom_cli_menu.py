"""Terminal Menu - run CrewLauncher from a text menu, no windows at all.

Perfect for slow machines, servers, and for practising Python basics: a
``while`` loop, ``if`` / ``elif``, and ``input()`` are all this file needs.
It only uses the standard library, so it works on every build.

Start it from a terminal:

    CrewLauncher --ui custom:my_gui

Exercises:

1. Change the banner text.
2. Add an option that prints the game folder: context.game_path().
3. Ask "Are you sure?" before launching (use input() like below).
"""
GUI_NAME = "My Custom GUI"


def ask(prompt):
    """input() that survives being started without a terminal."""
    try:
        return input(prompt)
    except EOFError:
        return None


def show_status(context):
    running = "yes (playing)" if context.is_running else "no"
    print()
    print("--- CrewLauncher status ---")
    print(f"  Version:   {context.version()}")
    print(f"  Installed: {'yes' if context.is_installed() else 'no'}")
    print(f"  Running:   {running}")
    print(f"  Game path: {context.game_path() or 'not set (run setup once)'}")
    print("---------------------------")


def do_install(context):
    print()
    print("Installing / updating the game...")
    last = [-10.0]

    def progress(pct):
        # progress arrives from a worker thread; print every 10%
        if pct - last[0] >= 10:
            last[0] = pct
            print(f"  ... {pct:.0f}%")

    def status(text, level="info"):
        print(f"  {text}")

    ok = context.install(progress=progress, status=status)
    print("Finished!" if ok else "Install failed - see logs/launcher.log")


def main(context):
    print()
    print("==============================")
    print(f"  {GUI_NAME} - terminal edition")
    print("==============================")

    while True:
        show_status(context)
        print()
        print("  1) Install / update game")
        print("  2) Launch game")
        print("  3) Stop game")
        print("  4) Refresh status")
        print("  0) Exit launcher")

        choice = ask("Your choice: ")
        if choice is None:
            print()
            print("No terminal detected. Start CrewLauncher from a terminal:")
            print("  CrewLauncher --ui custom:my_gui")
            break
        choice = choice.strip()

        if choice == "1":
            do_install(context)
        elif choice == "2":
            if not context.is_installed():
                print("Not installed yet - use option 1 first.")
            elif context.launch():
                print("Launched! Have fun.")
            else:
                print("Launch failed - check the Wine setup in Settings.")
        elif choice == "3":
            context.stop()
            print("Game stopped.")
        elif choice == "4":
            continue
        elif choice == "0":
            print("Bye!")
            break
        else:
            print("Please type one of the numbers shown.")
