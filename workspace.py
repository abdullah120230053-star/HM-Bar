import os
import time
from uuid import uuid4
from airpad_panel import AirPadPage
from desktop_tools import DesktopTools
from preferences import PROFILE
from pathlib import Path

from PyQt6.QtCore import QMimeData, QTimer, Qt, QUrl
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QSpinBox, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from themes import THEMES


class ShelfList(QListWidget):
    def mimeData(self, items):
        urls = []
        for item in items:
            url = QUrl(item.text())
            urls.append(url if url.scheme() in ("http", "https") else QUrl.fromLocalFile(item.text()))
        data = QMimeData()
        data.setUrls(urls)
        return data


class Workspace(QDialog):
    def __init__(self, island):
        super().__init__(island, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.island = island
        self.deadline = None
        self.paused_seconds = 0
        self.finished = False
        self.setWindowTitle("HM-Bar · Workspace")
        self.resize(490, 365)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        focus = self.tab("Focus")
        self.clock = QLabel()
        self.clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock.setStyleSheet("font-size: 48px; font-weight: 600;")
        focus.addWidget(self.clock, 1)
        self.minutes = QSpinBox()
        self.minutes.setRange(1, 180)
        self.minutes.setValue(25)
        self.minutes.setSuffix(" min")
        self.minutes.setAccessibleName("Focus duration")
        presets = QHBoxLayout()
        for value in (5, 25, 50):
            button = QPushButton(f"{value} min")
            button.clicked.connect(lambda _, n=value: self.minutes.setValue(n))
            presets.addWidget(button)
        presets.addWidget(self.minutes)
        focus.addLayout(presets)
        row = QHBoxLayout()
        self.toggle = QPushButton("Start")
        self.toggle.clicked.connect(self.toggle_timer)
        reset = QPushButton("Reset")
        reset.clicked.connect(self.reset_timer)
        row.addWidget(self.toggle)
        row.addWidget(reset)
        focus.addLayout(row)
        self.minutes.valueChanged.connect(self.tick)

        notes = self.tab("Notes")
        self.notes = QTextEdit()
        self.notes.setAcceptRichText(False)
        self.notes.setPlaceholderText("Capture an idea or jot down your next step…")
        self.notes.setPlainText(island.settings.get("scratchpad", ""))
        notes.addWidget(self.notes)
        self.note_timer = QTimer(self, singleShot=True, interval=450)
        self.note_timer.timeout.connect(self.save_notes)
        self.notes.textChanged.connect(self.note_timer.start)

        shelf = self.tab("File shelf")
        shelf.addWidget(QLabel("Drop files on this window or add them below."))
        self.files = ShelfList()
        self.files.setDragEnabled(True)
        self.files.addItems(island.settings.get("file_shelf", []))
        self.files.itemDoubleClicked.connect(self.open_file)
        shelf.addWidget(self.files)
        row = QHBoxLayout()
        for label, callback in [("Add files", self.choose_files), ("Remove", self.remove_file)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            row.addWidget(button)
        shelf.addLayout(row)
        self.feedback = QLabel()
        shelf.addWidget(self.feedback)
        self.setAcceptDrops(True)
        self.airpad = AirPadPage(self, self.tab("AirPad"))
        self.desktop_tools = DesktopTools(self)

        self.timer = QTimer(self, interval=250)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.tick()

    def tab(self, label):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.tabs.addTab(page, label)
        return layout

    def apply_theme(self, surface, accent):
        self.setStyleSheet(f"""
            QDialog {{ background: {surface}; }}
            QLabel {{ color: #f4f5fa; }}
            QTabWidget::pane {{ border: 1px solid #535965; border-radius: 7px; }}
            QTabBar::tab, QPushButton, QSpinBox, QTextEdit, QListWidget {{
                background: #242831; color: #f4f5fa;
                border: 1px solid #535965; border-radius: 6px; padding: 7px;
            }}
            QTabBar::tab:selected, QPushButton:hover {{ border-color: {accent}; }}
            QTextEdit, QListWidget {{ selection-background-color: #46516a; }}
        """)

    def remaining(self):
        if self.deadline is not None:
            return max(0, int(self.deadline - time.monotonic() + 0.999))
        return self.paused_seconds or (0 if self.finished else self.minutes.value() * 60)

    def timer_status(self):
        if self.deadline is None and not self.paused_seconds:
            return ""
        minutes, seconds = divmod(self.remaining(), 60)
        return f"Focus {minutes:02}:{seconds:02}"

    def tick(self):
        seconds = self.remaining()
        minutes, seconds_part = divmod(seconds, 60)
        self.clock.setText(f"{minutes:02}:{seconds_part:02}")
        if self.deadline is not None and seconds == 0:
            self.deadline = None
            self.finished = True
            QApplication.beep()
            self.island.show_notification("Focus", "Session complete", "Time for a break")
        self.toggle.setText("Pause" if self.deadline is not None else "Resume" if self.paused_seconds else "Start")
        self.minutes.setEnabled(self.deadline is None and not self.paused_seconds)

    def toggle_timer(self):
        if self.deadline is not None:
            self.paused_seconds = self.remaining()
            self.deadline = None
        else:
            self.deadline = time.monotonic() + (self.paused_seconds or self.minutes.value() * 60)
            self.paused_seconds = 0
            self.finished = False
        self.tick()

    def reset_timer(self):
        self.deadline = None
        self.paused_seconds = 0
        self.finished = False
        self.tick()

    def save_notes(self):
        self.note_timer.stop()
        self.island.settings["scratchpad"] = self.notes.toPlainText()
        self.island.save_settings()

    def choose_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add to file shelf")
        self.add_paths(paths)

    def add_paths(self, paths):
        current = [self.files.item(i).text() for i in range(self.files.count())]
        known = {os.path.normcase(path) for path in current}
        for path in paths:
            url = QUrl(path)
            is_web = url.isValid() and url.scheme() in ("http", "https") and bool(url.host())
            if (is_web or Path(path).is_file()) and os.path.normcase(path) not in known:
                self.files.addItem(path)
                known.add(os.path.normcase(path))
        self.save_shelf()

    def remove_file(self):
        row = self.files.currentRow()
        if row >= 0:
            self.files.takeItem(row)
            self.save_shelf()

    def save_shelf(self):
        self.island.settings["file_shelf"] = [
            self.files.item(i).text() for i in range(self.files.count())
        ]
        self.island.save_settings()

    def open_file(self, item):
        try:
            url = QUrl(item.text())
            if url.scheme() in ("http", "https"):
                import webbrowser
                webbrowser.open(item.text())
            else:
                os.startfile(item.text())
            self.feedback.clear()
        except OSError as error:
            self.feedback.setText(f"Could not open file: {error.strerror or error}")

    def accepts_stash(self, data):
        return data.hasImage() or any(url.isLocalFile() or url.scheme() in ("http", "https") for url in data.urls())

    def stash(self, data):
        paths = [url.toLocalFile() if url.isLocalFile() else url.toString() for url in data.urls()]
        if data.hasImage() and not paths:
            from PyQt6.QtGui import QImage, QPixmap
            image = data.imageData()
            if isinstance(image, QPixmap):
                image = image.toImage()
            if isinstance(image, QImage) and image.width() * image.height() <= 30_000_000:
                folder = PROFILE / "Stash"
                folder.mkdir(parents=True, exist_ok=True)
                image_path = folder / f"Image-{uuid4().hex[:10]}.png"
                if image.save(str(image_path)):
                    paths.append(str(image_path))
        self.add_paths(paths)
        self.tabs.setCurrentIndex(2)

    def dragEnterEvent(self, event):
        if self.accepts_stash(event.mimeData()):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()

    def dropEvent(self, event):
        try:
            self.stash(event.mimeData())
        except OSError as error:
            self.feedback.setText(str(error))
            return
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()

    def stop_tools(self):
        self.airpad.monitor.stop()
        if self.desktop_tools.ocr:
            self.desktop_tools.ocr.wait()
        if self.desktop_tools.git.state().name != "NotRunning":
            self.desktop_tools.git.kill()
            self.desktop_tools.git.waitForFinished(300)
