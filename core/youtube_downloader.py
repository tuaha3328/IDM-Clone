import os
from urllib.parse import urlparse

from core.download_paths import get_download_directory


QUALITY_FORMATS = {
    "Best video": (
        "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]"
        "/best[ext=mp4][vcodec^=avc1][acodec^=mp4a]"
    ),
    "1080p": (
        "bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]"
        "/best[height<=1080][ext=mp4][vcodec^=avc1][acodec^=mp4a]"
    ),
    "720p": (
        "bestvideo[height<=720][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]"
        "/best[height<=720][ext=mp4][vcodec^=avc1][acodec^=mp4a]"
    ),
    "480p": (
        "bestvideo[height<=480][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]"
        "/best[height<=480][ext=mp4][vcodec^=avc1][acodec^=mp4a]"
    ),
    "360p": (
        "bestvideo[height<=360][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]"
        "/best[height<=360][ext=mp4][vcodec^=avc1][acodec^=mp4a]"
    ),
    "MP3 audio": "bestaudio/best",
}


def is_youtube_url(url):
    host = (urlparse(url).hostname or "").lower()
    return host in ("youtu.be", "youtube.com", "youtube-nocookie.com") or host.endswith(
        (".youtube.com", ".youtube-nocookie.com")
    )


class YoutubeDownloader:
    def __init__(self, url, quality="Best video"):
        self.url = url
        self.quality = quality if quality in QUALITY_FORMATS else "Best video"
        extension = ".mp3" if self.quality == "MP3 audio" else ".mp4"
        self.download_directory = get_download_directory(extension)
        self.filename = os.path.join(self.download_directory, "youtube_download")
        self.is_paused = False
        self.is_cancelled = False
        self.error_message = ""

    def start_download(self, num_threads=4, progress_callback=None):
        try:
            from yt_dlp import YoutubeDL

            def progress_hook(data):
                if self.is_cancelled:
                    raise RuntimeError("Download cancelled")
                if self.is_paused:
                    raise RuntimeError("Download paused")
                if data.get("status") == "downloading" and progress_callback:
                    downloaded = data.get("downloaded_bytes", 0)
                    total = data.get("total_bytes") or data.get(
                        "total_bytes_estimate", 0
                    )
                    progress_callback(downloaded, total)
                filepath = (data.get("info_dict") or {}).get("filepath")
                if filepath:
                    self.filename = filepath

            options = {
                "format": QUALITY_FORMATS[self.quality],
                "merge_output_format": "mp4",
                "outtmpl": os.path.join(
                    self.download_directory, "%(title)s.%(ext)s"
                ),
                "noplaylist": True,
                "continuedl": True,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [progress_hook],
            }
            if self.quality == "MP3 audio":
                options["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ]

            self.is_paused = False
            self.is_cancelled = False
            self.error_message = ""
            with YoutubeDL(options) as downloader:
                info = downloader.extract_info(self.url, download=True)

            if self.quality == "MP3 audio":
                filepath = info.get("filepath") or downloader.prepare_filename(info)
                self.filename = filepath.rsplit(".", 1)[0] + ".mp3"
            else:
                self.filename = info.get("filepath") or downloader.prepare_filename(
                    info
                )
            return "completed"
        except Exception as error:
            if self.is_cancelled:
                return "cancelled"
            if self.is_paused:
                return "paused"
            self.error_message = str(error) or "The YouTube download failed."
            return "failed"

    def pause(self):
        self.is_paused = True

    def resume(self, num_threads=4, progress_callback=None):
        return self.start_download(
            num_threads=num_threads, progress_callback=progress_callback
        )

    def cancel(self):
        self.is_cancelled = True
