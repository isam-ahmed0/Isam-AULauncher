import time
import logging
import threading
from typing import Optional, List
from dataclasses import dataclass

import requests

from config import (
    GITHUB_REPO, REQUEST_TIMEOUT, CHUNK_SIZE,
    DISCORD_CLIENT_ID, APP_NAME
)

try:
    from pypresence import Presence
    DISCORD_RPC_AVAILABLE = True
except ImportError:
    DISCORD_RPC_AVAILABLE = False


@dataclass
class GameVersion:
    version: str
    url: str
    checksum: Optional[str] = None


class NetworkManager:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': f'IsamAULauncher/0.1'})

    def fetch_text(self, url: str) -> Optional[str]:
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.text.strip()
        except requests.RequestException as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None

    def download_file(self, url: str, output_path, progress_callback=None) -> bool:
        try:
            start = time.time()
            with self.session.get(url, stream=True, timeout=REQUEST_TIMEOUT) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                dl = 0
                try:
                    with open(output_path, 'wb') as f:
                        for chunk in r.iter_content(CHUNK_SIZE):
                            if chunk:
                                f.write(chunk)
                                dl += len(chunk)
                                if progress_callback and total:
                                    speed = dl / max(time.time() - start, 0.001)
                                    progress_callback(dl, total, speed)
                except IOError as e:
                    logging.error(f"File write failed: {e}")
                    try:
                        import os
                        os.remove(output_path)
                    except OSError:
                        pass
                    return False
            return True
        except requests.RequestException as e:
            logging.error(f"Download failed: {e}")
            try:
                import os
                os.remove(output_path)
            except (OSError, TypeError):
                pass
            return False

    def get_releases(self) -> List[GameVersion]:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            versions = []
            for rel in r.json():
                for asset in rel.get("assets", []):
                    if asset["name"] == "app.zip":
                        versions.append(GameVersion(
                            version=rel.get("tag_name"),
                            url=asset["browser_download_url"]
                        ))
            return versions
        except Exception as e:
            logging.error(f"Failed to fetch releases: {e}")
            return []


class DiscordRPC:
    def __init__(self):
        self.rpc = None
        self.connected = False

    def connect(self) -> bool:
        if not DISCORD_RPC_AVAILABLE:
            return False
        try:
            if self.connected and self.rpc:
                try:
                    self.rpc.close()
                except Exception:
                    pass
                self.rpc = None
            self.rpc = Presence(DISCORD_CLIENT_ID)
            self.rpc.connect()
            self.connected = True
            self.update_status("In Launcher", "Browsing Menu")
            return True
        except Exception as e:
            logging.error(f"Discord RPC failed: {e}")
            self.connected = False
            self.rpc = None
            return False

    def update_status(self, state: str, details: str, large_text: str = "Isam AU"):
        if self.connected and self.rpc:
            rpc = self.rpc
            def _do():
                try:
                    rpc.update(state=state, details=details,
                                   large_image="isam_au", large_text=large_text)
                except Exception as e:
                    logging.error(f"RPC update failed: {e}")
            threading.Thread(target=_do, daemon=True).start()

    def disconnect(self):
        if self.connected and self.rpc:
            try:
                self.rpc.close()
            except Exception:
                pass
            self.connected = False
            self.rpc = None
