from pathlib import Path

import core.download_paths as download_paths


def test_video_directory_is_created_under_downloads(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    videos_path = tmp_path / "Downloads" / "Video"
    assert not videos_path.exists()
    assert download_paths.get_download_directory("clip.mp4") == str(videos_path)
    assert videos_path.is_dir()
