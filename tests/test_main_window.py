import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def test_completed_download_shows_actual_total_file_size(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    output_file = tmp_path / "video.mp4"
    output_file.write_bytes(b"x" * (2 * 1024 * 1024))

    row = 0
    window.table.insertRow(row)
    window.table.setCellWidget(row, 6, window.create_action_buttons(row))
    window.row_data[row] = {"last_bytes": 0, "last_time": 0}
    window.downloaders[row] = type(
        "Downloader", (), {"filename": str(output_file)}
    )()

    class Worker:
        @staticmethod
        def wait():
            return True

    window.workers[row] = Worker()

    window.on_download_finished(row, "completed")
    app.processEvents()

    assert window.table.item(row, 1).text() == "2.00 MB"
    assert window.table.item(row, 2).text() == "2.00 MB"
    assert window.table.item(row, 3).text() == "100%"
    window.close()
