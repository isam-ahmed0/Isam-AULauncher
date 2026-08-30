"""Fix PE checksum of PyInstaller-generated executables.
Run after build: python scripts/fix_pe_checksum.py dist/IsamAULauncher.exe
"""
import sys

try:
    import pefile
except ImportError:
    print("Installing pefile...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pefile", "-q"])
    import pefile


def fix_checksum(path):
    pe = pefile.PE(path)
    pe.OPTIONAL_HEADER.CheckSum = pe.generate_checksum()
    pe.close()
    pe.write(path)
    print(f"Fixed: {path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_pe_checksum.py <exe1> [exe2] ...")
        sys.exit(1)
    for p in sys.argv[1:]:
        fix_checksum(p)
    print("Done.")
