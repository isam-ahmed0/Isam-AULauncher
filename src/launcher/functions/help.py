def show_help(argparse):
    parser = argparse.ArgumentParser(description="CrewLauncher")
    parser.add_argument("-tk, --tk, -lite", action="store_true",
                        help="Use Lite GUI (Tkinter) instead of default PySide6 GUI")
    parser.add_argument("--no-splash", action="store_true",
                        help="Skip splash screen")
    parser.add_argument("--splash-2", action="store_true",
                        help="Use animated WebM video splash")
    args, _ = parser.parse_known_args()                       