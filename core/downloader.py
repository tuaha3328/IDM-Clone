import os
import json
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from core.download_paths import get_download_path


class Downloader:
    def __init__(self, url):
        self.url = url
        self.file_size = 0
        self.supports_ranges = False
        self.filename = "downloaded_file"
        self.session = requests.Session()

        # Thread safety
        self.downloaded_bytes = 0
        self._lock = threading.Lock()

        # Pause / cancel control
        self.is_paused = False
        self.is_cancelled = False

        # Chunk state: {original_start_byte: current_next_byte_to_write}
        self.chunk_offsets = {}

        # Retry config
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    # ---------------------------------------------------------------- probe
    def probe(self):
        try:
            response = self.session.head(
                self.url, allow_redirects=True, timeout=10
            )
            if response.status_code == 405 or "Content-Length" not in response.headers:
                response = self.session.get(
                    self.url,
                    headers={"Range": "bytes=0-0"},
                    stream=True,
                    timeout=10,
                )

            content_length = response.headers.get("Content-Length")
            if content_length:
                self.file_size = int(content_length)

            accept_ranges = response.headers.get("Accept-Ranges")
            if accept_ranges == "bytes" or "Content-Range" in response.headers:
                self.supports_ranges = True

            content_disposition = response.headers.get("Content-Disposition")
            if content_disposition and "filename=" in content_disposition:
                self.filename = (
                    content_disposition.split("filename=")[1].strip('"\'')
                )
            else:
                self.filename = (
                    self.url.split("/")[-1].split("?")[0] or "downloaded_file"
                )

            # Safety: strip any path components from server-supplied filename
            self.filename = os.path.basename(self.filename) or "downloaded_file"
            self.filename = get_download_path(self.filename)
            return True
        except Exception:
            return False

    # -------------------------------------------------------- chunk planning
    def calculate_chunks(self, num_threads=4):
        if not self.supports_ranges or self.file_size == 0:
            return []
        chunk_size = self.file_size // num_threads
        chunks = []
        for i in range(num_threads):
            start = i * chunk_size
            end = (
                self.file_size - 1
                if i == num_threads - 1
                else start + chunk_size - 1
            )
            chunks.append((start, end))
        return chunks

    # ------------------------------------------------- state save / restore
    def _state_path(self):
        return f"{self.filename}.state"

    def _save_state(self):
        state = {
            "url": self.url,
            "file_size": self.file_size,
            "filename": self.filename,
            "chunk_offsets": {str(k): v for k, v in self.chunk_offsets.items()},
        }
        try:
            with open(self._state_path(), "w") as f:
                json.dump(state, f, indent=2)
        except OSError:
            pass  # don't crash a download thread over a state write failure

    def _load_state(self):
        """Return True if valid saved state exists for this exact download."""
        path = self._state_path()
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r") as f:
                state = json.load(f)
            if state.get("url") != self.url:
                return False
            if int(state.get("file_size", 0)) != self.file_size:
                return False
            # JSON keys are strings — convert back to int
            self.chunk_offsets = {
                int(k): int(v) for k, v in state["chunk_offsets"].items()
            }
            # Rebuild progress counter from saved offsets
            self.downloaded_bytes = sum(
                v - k for k, v in self.chunk_offsets.items()
            )
            return True
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def _clear_state(self):
        try:
            os.remove(self._state_path())
        except OSError:
            pass

    # ------------------------------------------------------ single-threaded
    def _download_single_thread(self, progress_callback):
        """Fallback for servers that do not support HTTP Range requests."""
        try:
            response = self.session.get(self.url, stream=True, timeout=15)
            response.raise_for_status()

            if not self.file_size:
                self.file_size = int(response.headers.get("Content-Length", 0))

            with open(self.filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.is_cancelled:
                        return "cancelled"
                    if self.is_paused:
                        return "paused"
                    if not chunk:
                        continue
                    f.write(chunk)
                    with self._lock:
                        self.downloaded_bytes += len(chunk)
                        if progress_callback:
                            progress_callback(
                                self.downloaded_bytes, self.file_size
                            )
            return "completed"
        except Exception:
            return "failed"

    # ---------------------------------------------------- multi-thread chunk
    def _download_chunk(self, start_byte, end_byte, progress_callback):
        """
        Download bytes [start_byte, end_byte] inclusive.
        Resumes from self.chunk_offsets[start_byte] if present.
        Returns one of: 'completed' | 'paused' | 'cancelled' | 'failed'
        """
        current = self.chunk_offsets.get(start_byte, start_byte)

        attempt = 0
        while attempt < self.max_retries:
            if self.is_cancelled:
                return "cancelled"
            if self.is_paused:
                return "paused"
            if current > end_byte:
                return "completed"

            headers = {"Range": f"bytes={current}-{end_byte}"}
            try:
                response = self.session.get(
                    self.url, headers=headers, stream=True, timeout=15
                )
                response.raise_for_status()

                with open(self.filename, "r+b") as f:
                    f.seek(current)
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            with self._lock:
                                self.chunk_offsets[start_byte] = current
                                self._save_state()
                            return "cancelled"
                        if self.is_paused:
                            with self._lock:
                                self.chunk_offsets[start_byte] = current
                                self._save_state()
                            return "paused"
                        if not chunk:
                            continue

                        f.write(chunk)
                        current += len(chunk)
                        with self._lock:
                            self.downloaded_bytes += len(chunk)
                            self.chunk_offsets[start_byte] = current
                            if progress_callback:
                                progress_callback(
                                    self.downloaded_bytes, self.file_size
                                )

                if current > end_byte:
                    with self._lock:
                        self.chunk_offsets[start_byte] = current
                    return "completed"

                # Server closed stream without error before we got all bytes
                raise IOError("Stream ended prematurely")

            except Exception:
                attempt += 1
                with self._lock:
                    self.chunk_offsets[start_byte] = current
                    self._save_state()

                if attempt >= self.max_retries:
                    return "failed"

                # Interruptible sleep so pause/cancel is responsive
                for _ in range(self.retry_delay * 10):
                    if self.is_paused:
                        return "paused"
                    if self.is_cancelled:
                        return "cancelled"
                    time.sleep(0.1)

        return "failed"

    # --------------------------------------------------------- public entry
    def start_download(self, num_threads=4, progress_callback=None):
        """
        Returns: 'completed' | 'paused' | 'cancelled' | 'failed'
        """
        if not self.probe():
            return "failed"

        # Reset control flags on each start/resume call
        self.is_paused = False
        self.is_cancelled = False

        # Fallback for servers without Range support
        if not self.supports_ranges:
            return self._download_single_thread(progress_callback)

        chunks = self.calculate_chunks(num_threads)
        if not chunks:
            return self._download_single_thread(progress_callback)

        resumed = self._load_state()

        if not resumed or not os.path.exists(self.filename):
            # Fresh start — pre-allocate sparse file
            self.chunk_offsets = {start: start for start, _ in chunks}
            self.downloaded_bytes = 0
            with open(self.filename, "wb") as f:
                f.seek(self.file_size - 1)
                f.write(b"\0")
        else:
            # Resume — do NOT truncate; just ensure all chunk keys exist
            for start, _ in chunks:
                if start not in self.chunk_offsets:
                    self.chunk_offsets[start] = start

        self._save_state()

        results = []
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(
                    self._download_chunk, start, end, progress_callback
                )
                for start, end in chunks
            ]
            for future in futures:
                results.append(future.result())

        if "cancelled" in results:
            self._clear_state()
            return "cancelled"
        if "paused" in results:
            return "paused"
        if "failed" in results:
            return "failed"

        self._clear_state()
        return "completed"

    # ------------------------------------------------------ control methods
    def pause(self):
        """Request the download to pause at the next safe checkpoint."""
        self.is_paused = True

    def resume(self, num_threads=4, progress_callback=None):
        """Resume a paused download. Spawn a new DownloadWorker to call this."""
        self.is_paused = False
        self.is_cancelled = False
        return self.start_download(
            num_threads=num_threads, progress_callback=progress_callback
        )

    def cancel(self):
        """Request the download to cancel and delete its state file."""
        self.is_cancelled = True