from pathlib import Path

import core.download_paths as download_paths


def test_file_types_route_to_downloads_subfolders(monkeypatch, tmp_path):
    monkeypatch.setattr(download_paths.Path, "home", lambda: tmp_path)
    downloads = tmp_path / "Downloads"

    for filename, folder in (
        ("report.PDF", "Documents"),
        ("report.docm", "Documents"),
        ("slides.pptm", "Documents"),
        ("book.epub", "Documents"),
        ("clip.mp4", "Video"),
        ("song.mp3", "Video"),
        ("setup.exe", "Programs"),
        ("installer.msix", "Programs"),
        ("mobile.apk", "Programs"),
        ("archive.zip", "Compressed"),
        ("archive.7zip", "Compressed"),
        ("disk-image.iso", "Compressed"),
        ("archive.zip.001", "Compressed"),
        ("archive.z01", "Compressed"),
        ("archive.tar.zst", "Compressed"),
        ("readme.md", "Documents"),
    ):
        expected_directory = downloads / folder
        expected = expected_directory / filename
        assert download_paths.get_download_path(filename) == str(expected)
        assert expected_directory.is_dir()

    assert download_paths.get_download_directory(".mp4") == str(downloads / "Video")
    assert download_paths.get_download_directory(".mp3") == str(downloads / "Video")
    assert download_paths.get_download_directory(".msi") == str(downloads / "Programs")
    assert download_paths.get_download_directory(".7z") == str(
        downloads / "Compressed"
    )
