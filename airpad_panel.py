from pathlib import Path
from queue import Empty, Queue
from threading import Event
from uuid import uuid4

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton
from airpad_bridge import AirPadBridge
from preferences import PROFILE


class AirPadMonitor(QThread):
    dashboard_updated = pyqtSignal(object)
    offer_finished = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = AirPadBridge()
        self.stopped = Event()
        self.outbox = Queue(maxsize=4)

    def run(self):
        previous = ()
        while not self.stopped.is_set():
            try:
                phones = self.client.phones()
            except (OSError, ValueError, RuntimeError):
                phones = None
            try:
                files = sorted(self.client.received_files().items(), key=lambda entry: entry[1][1], reverse=True)[:30]
            except OSError:
                files = []
            state = phones, files
            if state != previous:
                self.dashboard_updated.emit(state)
                previous = state
            try:
                device, paths = self.outbox.get(timeout=1.6)
            except Empty:
                continue
            if self.stopped.is_set():
                break
            try:
                result = self.client.request("offer", timeout=4, device=device, paths=paths, archives=[])
                count = result.get("count", 0) if result else 0
                self.offer_finished.emit(f"Offered {count} file(s). Accept in AirPad." if count else "AirPad did not accept the offer.")
            except (OSError, ValueError, RuntimeError):
                self.offer_finished.emit("AirPad could not send the selected file.")

    def stop(self):
        self.stopped.set()
        self.wait()


class AirPadPage:
    def __init__(self, workspace, layout):
        self.workspace = workspace
        self.last_files = None
        self.linked = False
        self.status = QLabel("Looking for AirPad for Windows...")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.phones = QComboBox()
        self.phones.setAccessibleName("Connected AirPad phone")
        layout.addWidget(self.phones)
        self.files = QListWidget()
        self.files.setAccessibleName("Files received from AirPad")
        self.files.itemDoubleClicked.connect(self.open_file)
        layout.addWidget(self.files, 1)
        row = QHBoxLayout()
        for text, callback in (
            ("Open", self.open_file), ("Add to Shelf", self.add_to_shelf),
            ("Send shelf file", self.send_shelf), ("Send clipboard", self.send_clipboard),
        ):
            button = QPushButton(text)
            button.clicked.connect(lambda _, action=callback: action())
            row.addWidget(button)
        layout.addLayout(row)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        self.monitor = AirPadMonitor(workspace)
        self.monitor.dashboard_updated.connect(self.update)
        self.monitor.offer_finished.connect(self.feedback.setText)
        self.monitor.start()

    def update(self, state):
        phones, files = state
        active = bool(phones)
        if active:
            self.status.setText("AirPad linked through your existing QR pairing.")
        elif phones is not None:
            self.status.setText("AirPad is ready. Scan its pairing QR or reconnect from the phone.")
        else:
            self.status.setText("Open AirPad for Windows to link HM-Bar.")
        if active and not self.linked:
            self.workspace.island.show_notification("AirPad", "Phone linked", "Using your existing pairing")
        self.linked = active
        selected = self.phones.currentData()
        self.phones.clear()
        for key, (name, routes) in (phones or {}).items():
            self.phones.addItem(f"{name} | {' / '.join(routes)}", key)
        index = self.phones.findData(selected)
        if index >= 0:
            self.phones.setCurrentIndex(index)
        paths = [path for path, _ in files]
        if paths != self.last_files:
            selected = self.selected_file()
            self.files.clear()
            for path in paths:
                item = QListWidgetItem(path.name)
                item.setData(Qt.ItemDataRole.UserRole, str(path))
                self.files.addItem(item)
                if str(path) == selected:
                    self.files.setCurrentItem(item)
            if self.last_files is not None and active:
                added = set(paths) - set(self.last_files)
                if added:
                    self.workspace.island.show_notification("AirPad", "File received", next(iter(added)).name)
            self.last_files = paths

    def selected_file(self):
        item = self.files.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def add_to_shelf(self):
        path = self.selected_file()
        if path:
            self.workspace.add_paths([path])
            self.feedback.setText("Added to your File Shelf.")

    def open_file(self, _item=None):
        import os
        path = self.selected_file()
        if path:
            try:
                os.startfile(path)
            except OSError:
                self.feedback.setText("Could not open the file.")

    def offer(self, path):
        from queue import Full
        phone = self.phones.currentData()
        if not phone:
            self.feedback.setText("Connect your phone in AirPad first.")
            return
        try:
            self.monitor.outbox.put_nowait((phone, [str(path)]))
            self.feedback.setText("Sending the offer...")
        except Full:
            self.feedback.setText("Wait for the pending offers to finish.")

    def send_shelf(self):
        item = self.workspace.files.currentItem()
        if item:
            self.offer(Path(item.text()))
        else:
            self.feedback.setText("Select a file in File Shelf first.")

    def send_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        if not self.phones.currentData():
            self.feedback.setText("Connect your phone in AirPad first.")
            return
        clipboard = QApplication.clipboard()
        data = clipboard.mimeData()
        if data is None or not (data.hasText() or data.hasImage()):
            self.feedback.setText("Copy text or an image before sending it.")
            return
        try:
            folder = PROFILE / "AirPadShare" / uuid4().hex
            folder.mkdir(parents=True)
            if data.hasImage():
                image = clipboard.image()
                if image.isNull() or image.width() * image.height() > 30_000_000:
                    self.feedback.setText("This clipboard image is too large to send.")
                    return
                path = folder / "HM-Bar clipboard.png"
                if not image.save(str(path)):
                    raise OSError("Could not save clipboard image")
            else:
                path = folder / "HM-Bar clipboard.txt"
                path.write_text(data.text(), encoding="utf-8")
        except OSError:
            self.feedback.setText("Could not prepare clipboard text.")
            return
        self.offer(path)
