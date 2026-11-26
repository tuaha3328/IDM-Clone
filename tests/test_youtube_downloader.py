import sys
from types import ModuleType

from core.youtube_downloader import YoutubeDownloader, is_youtube_url


def _stub_ffmpeg(monkeypatch):
    module = ModuleType("imageio_ffmpeg")
    module.get_ffmpeg_exe = lambda: "bundled-ffmpeg"
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", module)


def test_is_youtube_url_matches_supported_hosts_only():
    assert is_youtube_url("https://www.youtube.com/watch?v=example")
    assert is_youtube_url("https://youtu.be/example")
    assert not is_youtube_url("https://youtube.com.example.org/video")
    assert not is_youtube_url("https://example.com/video")


def test_video_quality_is_passed_to_yt_dlp(monkeypatch, tmp_path):
    captured = {}
    _stub_ffmpeg(monkeypatch)
    monkeypatch.setattr(
        "core.youtube_downloader.get_download_directory",
        lambda filename: str(tmp_path),
    )

    class FakeYoutubeDL:
        def __init__(self, options):
            captured["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download):
            assert url == "https://youtu.be/example"
            assert download
            return {"filepath": "download.mp4"}

    monkeypatch.setitem(
        sys.modules, "yt_dlp", ModuleType("yt_dlp")
    )
    sys.modules["yt_dlp"].YoutubeDL = FakeYoutubeDL

    downloader = YoutubeDownloader("https://youtu.be/example", "720p")
    assert downloader.start_download() == "completed"
    assert captured["options"]["format"] == (
        "bestvideo[height<=720][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]"
        "/best[height<=720][ext=mp4][vcodec^=avc1][acodec^=mp4a]"
    )
    assert captured["options"]["merge_output_format"] == "mp4"
    assert captured["options"]["ffmpeg_location"] == "bundled-ffmpeg"
    assert captured["options"]["outtmpl"] == str(tmp_path / "%(title)s.%(ext)s")
    assert "postprocessors" not in captured["options"]
    assert downloader.filename == "download.mp4"


def test_mp3_quality_enables_audio_extraction(monkeypatch, tmp_path):
    captured = {}
    _stub_ffmpeg(monkeypatch)
    monkeypatch.setattr(
        "core.youtube_downloader.get_download_directory",
        lambda filename: str(tmp_path),
    )

    class FakeYoutubeDL:
        def __init__(self, options):
            captured["options"] = options

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download):
            return {"filepath": "download.webm"}

        def prepare_filename(self, info):
            return "download.webm"

    module = ModuleType("yt_dlp")
    module.YoutubeDL = FakeYoutubeDL
    monkeypatch.setitem(sys.modules, "yt_dlp", module)

    downloader = YoutubeDownloader("https://youtu.be/example", "MP3 audio")
    assert downloader.start_download() == "completed"
    assert captured["options"]["postprocessors"] == [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }
    ]
    assert captured["options"]["outtmpl"] == str(tmp_path / "%(title)s.%(ext)s")
    assert captured["options"]["ffmpeg_location"] == "bundled-ffmpeg"
    assert downloader.filename == "download.mp3"
