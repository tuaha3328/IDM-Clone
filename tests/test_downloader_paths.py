from core.downloader import Downloader


def test_probe_uses_the_resolved_destination_path(monkeypatch, tmp_path):
    class Response:
        status_code = 200
        headers = {
            "Content-Length": "1024",
            "Content-Disposition": 'attachment; filename="report.pdf"',
        }

    class Session:
        @staticmethod
        def head(*args, **kwargs):
            return Response()

    expected_path = str(tmp_path / "report.pdf")
    monkeypatch.setattr(
        "core.downloader.get_download_path", lambda filename: expected_path
    )
    downloader = Downloader("https://example.test/report")
    downloader.session = Session()

    assert downloader.probe()
    assert downloader.filename == expected_path
    assert downloader.file_size == 1024
