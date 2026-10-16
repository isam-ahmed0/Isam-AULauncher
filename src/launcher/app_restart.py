"""Relaunch the launcher with the same command line arguments."""
import os
import sys


def restart(argv=None):
    """Replace the current process with a fresh launcher instance.

    Never returns on success. POSIX uses ``execv`` (in-place restart, the
    single-instance lock is released automatically because the lock handle
    is close-on-exec). On Windows a new process is spawned and the current
    one exits; the fresh instance is told to retry the single-instance lock
    for a moment while the old process is still winding down.
    """
    if argv is None:
        argv = sys.argv[1:]
    args = [str(a) for a in argv]
    if sys.platform.startswith("win"):
        import subprocess
        env = dict(os.environ)
        env["ISAM_RESTARTING"] = "1"
        subprocess.Popen([sys.executable, *args], env=env)
        os._exit(0)
    os.execv(sys.executable, [sys.executable, *args])
