"""Auto-Update & Launch - hands-free CrewLauncher from the terminal.

A one-shot script for power users: it reports the status, asks the update
server for the newest version, updates if needed, then launches the game.
A nice small script to learn from: one helper function, error checks, and
one if / elif / else chain - all launcher topics.

Start it from a terminal:

    CrewLauncher --ui custom:my_gui
"""
from config import VERSION_URL     # the launcher's "newest version" file

GUI_NAME = "My Custom GUI"


def ask(question):
    """Yes/no question; safe when there is no terminal attached."""
    try:
        answer = input(f"{question} [y/n] ").strip().lower()
    except EOFError:
        return False
    return answer.startswith("y")


def main(context):
    print()
    print("CrewLauncher auto-update")
    print(f"  Installed: {context.version()}")
    print(f"  Folder:    {context.game_path() or 'not set'}")

    if not context.game_path():
        print()
        print("No install folder yet - open the builtin interface and run")
        print("the setup once (Settings > Interface), then try again.")
        return

    latest = context.network.fetch_text(VERSION_URL)
    if latest is None:
        print("Could not reach the update server - skipping update check.")
    elif latest.strip() == context.version():
        print(f"Already up to date ({latest.strip()}).")
    else:
        print(f"New version available: {latest.strip()}")
        if ask("Update now?"):
            print("Updating...")
            last = [-10.0]

            def progress(pct):
                if pct - last[0] >= 10:
                    last[0] = pct
                    print(f"  ... {pct:.0f}%")

            def status(text, level="info"):
                print(f"  {text}")

            ok = context.install(progress=progress, status=status)
            print("Update finished." if ok
                  else "Update failed - see logs/launcher.log.")

    print()
    if ask("Launch the game now?"):
        print("Launching..." if context.launch()
              else "Launch failed - check the Wine setup in Settings.")
    else:
        print("Done. Bye!")
