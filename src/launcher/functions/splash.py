def on_splash_done(launcher):
    token = launcher._read_itch_token()
    if token:
        launcher.window.show()
    else:
        from gui_qt.login import LoginWindow
        launcher._login_window = LoginWindow(prefix=launcher.config.get_wine_prefix())
        launcher._login_window.show()


def boot(splash, launcher, qapp):
    splash.update_status("Oh... hi there! who are you?")
    qapp.processEvents()
    launcher._load_itch_profile_sync()
    splash.update_status("Is there new version available?...")
    qapp.processEvents()
    launcher._load_initial_data_sync()

    # username = launcher._itch_profile.get("username") or "User"
    splash.update_status("Ready")
    qapp.processEvents()
    splash.finish()