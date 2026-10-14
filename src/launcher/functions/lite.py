def ensure_import_path(os, sys):
    """Make the launcher modules importable when run as a script."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


def acquire_single_instance(config, IS_WINDOWS):
    """Cross-platform advisory lock. Returns the open file or None."""
    path = config.appdata_dir / "launcher.lock"
    try:
        f = open(str(path), "w")
        if IS_WINDOWS:
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except OSError:
        return None