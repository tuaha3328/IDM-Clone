import time
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
from core.downloader import Downloader
from core.download_worker import DownloadWorker
from core.download_paths import get_download_path
from core.youtube_downloader import YoutubeDownloader, is_youtube_url
from ui.styles import DARK_STYLE

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python IDM Clone")
        self.resize(1150, 560)
        
        # Track Downloader instances and Worker instances per row
        self.downloaders = {} 
        self.workers = {} 
        self.row_data = {} 
        
        self.setStyleSheet(DARK_STYLE)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste download URL here...")
        self.url_input.returnPressed.connect(self.handle_add_url)
        self.quality_select = QComboBox()
        self.quality_select.addItems(
            ["Best video", "1080p", "720p", "480p", "360p", "MP3 audio"]
        )
        self.quality_select.setToolTip(
            "YouTube video quality or MP3 audio. Applies to YouTube URLs only. "
            "MP3 extraction requires FFmpeg."
        )
        self.quality_select.setItemData(
            5,
            "MP3 extraction requires FFmpeg installed and available on PATH.",
            Qt.ToolTipRole,
        )
        self.add_btn = QPushButton("Add Download")
        self.add_btn.clicked.connect(self.handle_add_url)
        
        top_layout.addWidget(self.url_input)
        top_layout.addWidget(self.quality_select)
        top_layout.addWidget(self.add_btn)
        main_layout.addLayout(top_layout)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "File Name",
                "Downloaded",
                "Total Size",
                "Progress",
                "Speed",
                "Save Path",
                "Actions",
            ]
        )
        self.table.setColumnWidth(0, 190)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 100)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setColumnWidth(6, 160)
        self.table.verticalHeader().setVisible(False) 
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers) 
        main_layout.addWidget(self.table)

    def format_bytes(self, size):
        if size == 0: return "0 B"
        power = 1024
        n = 0
        dict_suffix = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}
        while size >= power and n < 4:
            size /= power
            n += 1
        return f"{size:.2f} {dict_suffix[n]}"

    def handle_add_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
            
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 40) 
        
        guessed_name = url.split('/')[-1].split('?')[0] or "Downloading..."
            
        self.url_input.clear()
        self.row_data[row] = {"last_bytes": 0, "last_time": time.time()}
        
        # --- MERGED LOGIC: Create Downloader instance first ---
        if is_youtube_url(url):
            downloader = YoutubeDownloader(url, self.quality_select.currentText())
        else:
            downloader = Downloader(url)
        self.downloaders[row] = downloader

        initial_path = (
            downloader.filename
            if is_youtube_url(url)
            else get_download_path(guessed_name)
        )
        self._set_file_name(row, guessed_name)
        self.table.setItem(row, 1, QTableWidgetItem("0 B"))
        self.table.setItem(row, 2, QTableWidgetItem("--"))
        self.table.setItem(row, 3, QTableWidgetItem("0%"))
        self.table.setItem(row, 4, QTableWidgetItem("0 B/s"))
        self._set_save_path(row, initial_path)
        self.table.setCellWidget(row, 6, self.create_action_buttons(row))
        
        # Spawn the worker with the downloader instance
        self._spawn_worker(row)

    def _spawn_worker(self, row):
        """Starts or resumes a download thread for a specific row."""
        worker = DownloadWorker(self.downloaders[row])
        worker.progress.connect(lambda d, t: self.update_progress(row, d, t))
        worker.finished.connect(lambda status: self.on_download_finished(row, status))
        
        self.workers[row] = worker 
        worker.start()

    def create_action_buttons(self, row):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        pause_btn = QPushButton("Pause")
        pause_btn.setObjectName("pauseBtn")
        pause_btn.clicked.connect(lambda: self.handle_pause_resume(row))
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(lambda: self.handle_cancel(row))
        
        layout.addWidget(pause_btn)
        layout.addWidget(cancel_btn)
        layout.addStretch()
        return widget

    def update_progress(self, row, downloaded, total):
        if row not in self.row_data or row not in self.downloaders:
            return

        self.table.setItem(row, 1, QTableWidgetItem(self.format_bytes(downloaded)))
        self._set_file_name(row, os.path.basename(self.downloaders[row].filename))
        self._set_save_path(row, self.downloaders[row].filename)

        if total > 0:
            percent = int((downloaded / total) * 100)
            self.table.setItem(row, 2, QTableWidgetItem(self.format_bytes(total)))
            self.table.setItem(row, 3, QTableWidgetItem(f"{percent}%"))
        else:
            self.table.setItem(row, 2, QTableWidgetItem("Unknown"))

        current_time = time.time()
        time_diff = current_time - self.row_data[row]["last_time"]
        if time_diff >= 1.0:
            bytes_diff = downloaded - self.row_data[row]["last_bytes"]
            speed = bytes_diff / time_diff
            self.table.setItem(
                row, 4, QTableWidgetItem(f"{self.format_bytes(speed)}/s")
            )
            self.row_data[row]["last_time"] = current_time
            self.row_data[row]["last_bytes"] = downloaded

    def handle_pause_resume(self, row):
        if row not in self.downloaders or row not in self.workers:
            return

        btn = self.table.cellWidget(row, 6).findChild(QPushButton, "pauseBtn")
        
        if btn.text() == "Pause":
            # Tell the engine to pause
            self.downloaders[row].pause()
            self.table.setItem(row, 3, QTableWidgetItem("Pausing..."))
        else:
            # Resume: Tell the engine to resume, and spawn a new thread
            btn.setText("Pause")
            self.table.setItem(row, 3, QTableWidgetItem("Resuming..."))
            self._spawn_worker(row)

    def handle_cancel(self, row):
        if row in self.downloaders:
            self.downloaders[row].cancel()
            self.table.setItem(row, 3, QTableWidgetItem("Cancelling..."))

    def on_download_finished(self, row, status):
        """Handles the string status returned by the friend's engine."""
        btn = self.table.cellWidget(row, 6).findChild(QPushButton, "pauseBtn")
        
        if status == "completed":
            filename = self.downloaders[row].filename
            actual_size = os.path.getsize(filename)
            self._set_file_name(row, os.path.basename(filename))
            self._set_save_path(row, filename)
            self.table.setItem(
                row, 1, QTableWidgetItem(self.format_bytes(actual_size))
            )
            self.table.setItem(
                row, 2, QTableWidgetItem(self.format_bytes(actual_size))
            )
            self.table.setItem(row, 3, QTableWidgetItem("100%"))
            self.table.setItem(row, 4, QTableWidgetItem("Complete"))
            self.table.removeCellWidget(row, 6)
            self.cleanup_row(row)
            
        elif status == "paused":
            self.table.setItem(row, 3, QTableWidgetItem("Paused ⏸"))
            if btn: btn.setText("Resume")
            
        elif status == "cancelled":
            self.table.setItem(row, 3, QTableWidgetItem("Cancelled ❌"))
            self.table.removeCellWidget(row, 6)
            self.cleanup_row(row)
            
        elif status == "failed":
            self.table.setItem(row, 3, QTableWidgetItem("Failed ⚠"))
            downloader = self.downloaders[row]
            error_message = getattr(downloader, "error_message", "")
            if error_message:
                QMessageBox.warning(self, "Download failed", error_message)
            self.table.removeCellWidget(row, 6)
            self.cleanup_row(row)

    def _set_file_name(self, row, filename):
        item = QTableWidgetItem(filename)
        item.setToolTip(filename)
        self.table.setItem(row, 0, item)

    def _set_save_path(self, row, path):
        item = QTableWidgetItem(path)
        item.setToolTip(path)
        self.table.setItem(row, 5, item)

    def cleanup_row(self, row):
        if row in self.workers:
            self.workers[row].wait()
            del self.workers[row]
        if row in self.downloaders:
            del self.downloaders[row]
        if row in self.row_data:
            del self.row_data[row]