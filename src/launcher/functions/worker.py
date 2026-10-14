def profile_worker(launcher, profile_done):
    try:
        launcher._load_itch_profile_sync()
    except Exception:
        pass
    launcher._invoke_main(profile_done)

def version_worker(launcher, version_done):
    try:
        launcher._load_initial_data_sync()
    except Exception:
        pass
    launcher._invoke_main(version_done)