import os
import requests
import zipfile
import sys
import webbrowser
from colorama import init, Fore, Style
import time
import subprocess
# Initialize colorama
init(autoreset=True)

APP_NAME = "Isam AULauncher"

def download_file(url, local_filename):
    start_time = time.time()
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total_size = int(r.headers.get('content-length', 0))
        chunk_size = 8192
        with open(local_filename, 'wb') as f:
            downloaded_size = 0
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    done = int(50 * downloaded_size / total_size)
                    percent = int(100 * downloaded_size / total_size)
                    elapsed_time = time.time() - start_time
                    speed = (downloaded_size / elapsed_time) / 1024  # KB/s
                    sys.stdout.write(f"\r[{Fore.GREEN}{'=' * done}{' ' * (50-done)}{Fore.RESET}] {percent}% -- {speed:.2f} KB/s")
                    sys.stdout.flush()
    print("\n")

def extract_zip(file_path, extract_to):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        total_files = len(zip_ref.infolist())
        for i, file in enumerate(zip_ref.infolist()):
            zip_ref.extract(file, extract_to)
            done = int(50 * (i + 1) / total_files)
            percent = int(100 * (i + 1) / total_files)
            sys.stdout.write(f"\r[{Fore.BLUE}{'=' * done}{' ' * (50-done)}{Fore.RESET}] {percent}% Extracting")
            sys.stdout.flush()
    print("\n")

def print_colored(text, color):
    colors = {
        "yellow": Fore.YELLOW,
        "green": Fore.GREEN,
        "blue": Fore.BLUE,
        "red": Fore.RED,
        "purple": Fore.MAGENTA,
        "cyan": Fore.CYAN,
        "reset": Style.RESET_ALL
    }
    if color in colors:
        print(f"{colors[color]}{text}{colors['reset']}")
    else:
        print(f"{Fore.RED}[ERROR] Unknown color: {color}{Style.RESET_ALL}")

def print_boxed(text, color):
    border = "+" + "-" * (len(text) + 2) + "+"
    print(f"{color}{border}{Style.RESET_ALL}")
    print(f"{color}| {text} |{Style.RESET_ALL}")
    print(f"{color}{border}{Style.RESET_ALL}")

def get_latest_version():
    version_url = "https://raw.githubusercontent.com/jogamerforgames2021/ShadowScripts/main/Bootstrappers/ShadowTesting/version.txt"
    response = requests.get(version_url)
    response.raise_for_status()
    return response.text.strip()

def read_version_file(file_path):
    try:
        with open(file_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def main():
    print(f"{Fore.CYAN}=========================== ISAM AULAUNCHER BOOTSTRAPPER ==========================={Style.RESET_ALL}\n")

    print_colored("[*] Checking for Updates...", "yellow")

    latest_version_url = "https://raw.githubusercontent.com/jogamerforgames2021/ShadowScripts/main/Bootstrappers/ShadowTesting/app.zip"
    local_zip_file = "app.zip"
    version_file_url = "https://raw.githubusercontent.com/jogamerforgames2021/ShadowScripts/main/Bootstrappers/ShadowTesting/version.txt"
    current_version_file = "APP/current_version.txt"

    if os.path.exists("APP"):
        app_version = read_version_file(current_version_file)
    else:
        app_version = None

    latest_version = get_latest_version()

    if app_version is None:
        print_colored("[!] Downloading descendants...", "green")
        download_file(latest_version_url, local_zip_file)

        # Create "APP" directory if it doesn't exist
        app_dir = "APP"
        if not os.path.exists(app_dir):
            os.makedirs(app_dir)

        print_colored("[#] Extracting files...", "blue")
        extract_zip(local_zip_file, app_dir)

        os.remove(local_zip_file)
        with open(current_version_file, "w") as f:
            f.write(latest_version)
        print_colored("[^] UPDATE SUCCESS", "green")

    elif app_version == latest_version:
        print_colored("[#] Latest version is already installed", "blue")
    else:
        print_colored(f"[!] Update {Fore.MAGENTA}{latest_version}{Fore.GREEN} Found!", "green")
        print_colored("[v] Downloading latest version...", "green")
        download_file(latest_version_url, local_zip_file)

        # Create "APP" directory if it doesn't exist
        app_dir = "APP"
        if not os.path.exists(app_dir):
            os.makedirs(app_dir)

        print_colored("[#] Extracting files...", "blue")
        extract_zip(local_zip_file, app_dir)

        os.remove(local_zip_file)
        with open(current_version_file, "w") as f:
            f.write(latest_version)
        print_colored("[^] UPDATE SUCCESS", "green")

    print(f"\n{Fore.CYAN}============================== OPTIONS ============================== {Style.RESET_ALL}")
    print_boxed("Press 1 to run application", Fore.CYAN)
    print_boxed("Press 2 to exit", Fore.RED)
    print_boxed("Press 3 to join our server (Discord)", Fore.YELLOW)
    print_boxed("Press 4 to teleport to our website", Fore.BLUE)

    choice = input("Enter your choice: ")

    if choice == '1':
        executable_path = os.path.join(os.getcwd(), "APP", "Shadow X.exe")
        subprocess.Popen([executable_path])
    elif choice == '3':
        webbrowser.open("https://discord.gg/AegHT8KGw4")
    elif choice == '4':
        webbrowser.open("https://jogamerforgames2021.github.io/")

    print(f"\n{Fore.GREEN}Thanks for using Isam AULauncher!{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()
