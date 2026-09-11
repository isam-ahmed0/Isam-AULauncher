import warnings
import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

import requests

from config import (
    GITHUB_REPO, REQUEST_TIMEOUT, CHUNK_SIZE,
    DISCORD_CLIENT_ID, APP_NAME, LAUNCHER_VERSION
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
        self.session.headers.update({'User-Agent': f'IsamAULauncher/{LAUNCHER_VERSION}'})

    def fetch_text(self, url: str) -> Optional[str]:
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.text.strip()
        except requests.RequestException as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass

    def download_file(self, url: str, output_path, progress_callback=None) -> bool:
        output_path = Path(output_path) if not isinstance(output_path, Path) else output_path
        SEGMENT_COUNT = 8
        SEGMENT_SIZE = 4 * 1024 * 1024  # 4MB per segment (downloaded as chunks within)

        try:
            # HEAD to get total size and check Range support
            head = self.session.head(url, timeout=REQUEST_TIMEOUT)
            head.raise_for_status()
            total = int(head.headers.get("content-length", 0))
            accept_ranges = head.headers.get("accept-ranges", "").lower() == "bytes"

            if not accept_ranges or total < SEGMENT_SIZE * 2:
                return self._download_single_thread(url, output_path, total, progress_callback)

            # Segmented parallel download
            segments = []
            for i in range(SEGMENT_COUNT):
                start = i * (total // SEGMENT_COUNT)
                end = start + (total // SEGMENT_COUNT) - 1 if i < SEGMENT_COUNT - 1 else total - 1
                seg_path = output_path.with_suffix(output_path.suffix + f".part{i}")
                existing = seg_path.stat().st_size if seg_path.exists() else 0
                seg_start = start + existing
                segments.append((i, seg_start, end, seg_path, existing))

            # Check if all segments already complete
            downloaded = sum(s[4] for s in segments)
            if downloaded >= total:
                self._concatenate_segments(segments, output_path)
                if progress_callback:
                    progress_callback(total, total, 0)
                return True

            # Download incomplete segments in parallel
            start_time = time.time()
            completed_lock = threading.Lock()
            completed_bytes = [s[4] for s in segments]  # mutable list for per-segment tracking

            def download_segment(idx, seg_start, seg_end, seg_path, already_done):
                nonlocal completed_bytes
                seg_total = seg_end - seg_start + 1
                if already_done >= seg_total:
                    return True
                try:
                    headers = {"Range": f"bytes={seg_start}-{seg_end}"}
                    seg_session = requests.Session()
                    with seg_session.get(url, headers=headers, stream=True, timeout=REQUEST_TIMEOUT) as r:
                        if r.status_code not in (200, 206):
                            return False
                        mode = "ab" if already_done > 0 else "wb"
                        with open(seg_path, mode) as f:
                            for chunk in r.iter_content(CHUNK_SIZE):
                                if chunk:
                                    f.write(chunk)
                                    with completed_lock:
                                        completed_bytes[idx] += len(chunk)
                                        dl = sum(completed_bytes)
                                        speed = dl / max(time.time() - start_time, 0.001)
                                        if progress_callback:
                                            progress_callback(dl, total, speed)
                    return True
                except Exception as e:
                    logging.error(f"Segment {idx} failed: {e}")
                    return False

            with ThreadPoolExecutor(max_workers=SEGMENT_COUNT) as pool:
                futures = [
                    pool.submit(download_segment, i, s, e, p, d)
                    for i, s, e, p, d in segments
                ]
                results = [f.result() for f in as_completed(futures)]

            if not all(results):
                logging.error("Some segments failed — falling back to single-threaded")
                for s in segments:
                    try:
                        s[3].unlink(missing_ok=True)
                    except OSError:
                        pass
                return self._download_single_thread(url, output_path, total, progress_callback)

            self._concatenate_segments(segments, output_path)
            return True

        except requests.RequestException as e:
            logging.error(f"Download failed: {e}")
            return False

    def _concatenate_segments(self, segments, output_path):
        with open(output_path, "wb") as out:
            for _, _, _, seg_path, _ in sorted(segments, key=lambda s: s[0]):
                if seg_path.exists():
                    with open(seg_path, "rb") as seg:
                        for chunk in iter(lambda: seg.read(CHUNK_SIZE), b""):
                            out.write(chunk)
                    seg_path.unlink(missing_ok=True)

    def _download_single_thread(self, url, output_path, total, progress_callback=None) -> bool:
        try:
            start = time.time()
            with self.session.get(url, stream=True, timeout=REQUEST_TIMEOUT) as r:
                r.raise_for_status()
                if not total:
                    total = int(r.headers.get("content-length", 0))
                dl = 0
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)
                            if progress_callback and total:
                                speed = dl / max(time.time() - start, 0.001)
                                progress_callback(dl, total, speed)
            return True
        except requests.RequestException as e:
            logging.error(f"Download failed: {e}")
            try:
                os.remove(output_path)
            except OSError:
                pass
            return False
        except (IOError, OSError) as e:
            logging.error(f"File write failed: {e}")
            return False

    def get_releases(self) -> List[GameVersion]:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
        try:
            r = requests.get(url, timeout=30,
                             headers={"User-Agent": f"IsamAULauncher/{LAUNCHER_VERSION}"})
            r.raise_for_status()
            versions = []
            for rel in r.json():
                for asset in rel.get("assets", []):
                    if asset["name"] == "app.zip":
                        versions.append(GameVersion(
                            version=rel.get("tag_name"),
                            url=asset["browser_download_url"]
                        ))
            logging.info(f"Fetched {len(versions)} game releases")
            return versions
        except Exception as e:
            logging.error(f"Failed to fetch releases: {e}")
            return []


class DiscordRPC:
    def __init__(self):
        self.rpc = None
        self.connected = False
        self._lock = threading.Lock()

    def connect(self) -> bool:
        if not DISCORD_RPC_AVAILABLE:
            return False
        try:
            if self.connected and self.rpc:
                try:
                    self.rpc.close()
                except Exception:
                    pass
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
        with self._lock:
            if not self.connected or not self.rpc:
                return
            rpc = self.rpc
        def _do():
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    rpc.update(state=state, details=details,
                               large_image="isam_au", large_text=large_text)
            except Exception as e:
                logging.error(f"RPC update failed: {e}")
        threading.Thread(target=_do, daemon=True).start()

    def disconnect(self):
        self.connected = False
        if self.rpc:
            try:
                self.rpc.close()
            except Exception:
                pass
        self.rpc = None
