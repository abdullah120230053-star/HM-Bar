import asyncio
import ctypes
import os
import time
import winreg
from ctypes import wintypes as w
from pathlib import Path
from tempfile import TemporaryDirectory

import psutil
from PyQt6.QtCore import QProcess, QRect, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QCheckBox, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QWidget

from preferences import PREFERENCES, read_json, save_preferences


class ScreenSelection(QWidget):
    selected = pyqtSignal(object)

    def __init__(self, screen, color):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setGeometry(screen.geometry())
        self.pixels = screen.grabWindow(0)
        self.image = self.pixels.toImage()
        self.color = color
        self.start = self.end = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.pixels)
        if self.start is not None:
            painter.setPen(QPen(Qt.GlobalColor.cyan, 2))
            painter.drawRect(QRect(self.start, self.end).normalized())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start = self.end = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self.start is not None:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.start is None:
            return
        end = event.position().toPoint()
        scale = self.pixels.devicePixelRatio()
        if self.color:
            x = min(self.image.width() - 1, max(0, int(end.x() * scale)))
            y = min(self.image.height() - 1, max(0, int(end.y() * scale)))
            self.selected.emit(self.image.pixelColor(x, y).name().upper())
        else:
            area = QRect(self.start, end).normalized().intersected(self.rect())
            if area.width() > 4 and area.height() > 4:
                self.selected.emit(self.image.copy(
                    int(area.x() * scale), int(area.y() * scale),
                    int(area.width() * scale), int(area.height() * scale)))
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


class TextRecognition(QThread):
    completed = pyqtSignal(str, str)

    def __init__(self, image, parent):
        super().__init__(parent)
        self.image = image

    def run(self):
        try:
            text = asyncio.run(self.recognize())
            self.completed.emit(text, "" if text else "No text found in that selection.")
        except Exception as error:
            self.completed.emit("", f"OCR unavailable: {error}")

    async def recognize(self):
        from winsdk.windows.graphics.imaging import BitmapDecoder, BitmapPixelFormat, BitmapAlphaMode
        from winsdk.windows.media.ocr import OcrEngine
        from winsdk.windows.storage import FileAccessMode, StorageFile

        engine = OcrEngine.try_create_from_user_profile_languages()
        if engine is None:
            raise RuntimeError("Install an OCR language in Windows settings.")
        with TemporaryDirectory(prefix="hmbar-ocr-") as folder:
            path = Path(folder) / "selection.png"
            if not self.image.save(str(path)):
                raise RuntimeError("Could not prepare the selected area.")
            file = await StorageFile.get_file_from_path_async(str(path))
            stream = await file.open_async(FileAccessMode.READ)
            try:
                decoder = await BitmapDecoder.create_async(stream)
                bitmap = await decoder.get_software_bitmap_async(BitmapPixelFormat.BGRA8, BitmapAlphaMode.PREMULTIPLIED)
                try:
                    return (await engine.recognize_async(bitmap)).text
                finally:
                    bitmap.close()
            finally:
                stream.close()


class DesktopTools:
    def __init__(self, workspace):
        self.workspace = workspace
        self.user32 = ctypes.WinDLL("user32")
        self.user32.GetForegroundWindow.restype = w.HWND
        self.user32.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
        self.user32.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
        self.user32.SetWindowPos.argtypes = [w.HWND, w.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.UINT]
        self.last_window = None
        self.meeting_started = None
        self.ocr = None
        self.entries = []
        self.snap_timer = QTimer(workspace, interval=400)
        self.snap_timer.timeout.connect(self.remember_window)
        self.snap_timer.start()
        self.build_tools(workspace.tab("Desktop"))
        self.build_clipboard(workspace.tab("Clipboard"))

    def row(self, layout, buttons):
        row = QHBoxLayout()
        for label, callback in buttons:
            button = QPushButton(label)
            button.clicked.connect(lambda _, action=callback: action())
            row.addWidget(button)
        layout.addLayout(row)

    def build_tools(self, layout):
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.battery = QLabel()
        layout.addWidget(self.battery)
        self.privacy = QLabel()
        self.privacy.setWordWrap(True)
        layout.addWidget(self.privacy)
        self.row(layout, (("Audio outputs", lambda: self.open_windows("ms-settings:sound")),
                          ("Power settings", lambda: self.open_windows("ms-settings:batterysaver")),
                          ("Camera privacy", lambda: self.open_windows("ms-settings:privacy-webcam")),
                          ("Mic privacy", lambda: self.open_windows("ms-settings:privacy-microphone"))))
        self.row(layout, (("Pick color", lambda: self.capture(True)), ("Snip text (OCR)", lambda: self.capture(False)),
                          ("Snap left", lambda: self.snap(0)), ("Snap right", lambda: self.snap(1))))
        self.meeting = QLabel("Meeting timer: not running")
        layout.addWidget(self.meeting)
        self.row(layout, (("Start meeting timer", self.start_meeting), ("Stop timer", self.stop_meeting)))
        self.git_label = QLabel("Git Pulse: choose a project")
        self.git_label.setWordWrap(True)
        layout.addWidget(self.git_label)
        self.project = None
        self.git = QProcess(self.workspace)
        self.git.finished.connect(self.git_finished)
        self.git.errorOccurred.connect(lambda _: self.git_label.setText("Git Pulse: could not start Git"))
        self.row(layout, (("Choose Git project", self.choose_project), ("Refresh Git", self.refresh_git)))
        self.build_status = QLabel("Build Pulse: idle")
        self.build_status.setWordWrap(True)
        layout.addWidget(self.build_status)
        self.command = QProcess(self.workspace)
        self.command.finished.connect(self.command_finished)
        self.command.errorOccurred.connect(lambda _: self.build_status.setText("Could not start the selected tool."))
        self.command_kind = ""
        self.row(layout, (("Build npm project", self.start_build), ("Docker status", self.docker_status)))
        layout.addWidget(self.status)
        layout.addStretch()
        self.status_timer = QTimer(self.workspace, interval=1000)
        self.status_timer.timeout.connect(self.tick)
        self.status_timer.start()
        self.tick()

    def build_clipboard(self, layout):
        self.history_enabled = QCheckBox("Keep the last five copies in memory")
        self.history_enabled.setChecked(read_json(PREFERENCES).get("clipboard_history", False))
        self.history_enabled.toggled.connect(self.history_changed)
        layout.addWidget(self.history_enabled)
        self.history = QListWidget()
        self.history.itemDoubleClicked.connect(self.restore_clip)
        layout.addWidget(self.history)
        self.row(layout, (("Copy selected", self.restore_clip), ("Clear history", self.clear_history)))
        QApplication.clipboard().dataChanged.connect(self.record_clip)

    def history_changed(self, checked):
        try:
            save_preferences({"clipboard_history": checked})
        except OSError as error:
            self.status.setText(str(error))
        if not checked:
            self.clear_history()

    def clear_history(self):
        self.entries.clear()
        self.history.clear()

    def record_clip(self):
        if not self.history_enabled.isChecked():
            return
        clipboard = QApplication.clipboard()
        data = clipboard.mimeData()
        if data is None:
            return
        if data.hasImage():
            image = clipboard.image()
            if image.isNull() or image.width() * image.height() > 12_000_000:
                return
            entry = ("image", image)
        elif data.hasText():
            text = data.text()
            if not 0 < len(text) <= 100000:
                return
            entry = ("text", text)
        else:
            return
        self.entries = [entry, *[old for old in self.entries if old != entry]][:5]
        self.history.clear()
        for kind, value in self.entries:
            label = f"Image {value.width()} x {value.height()}" if kind == "image" else " ".join(value.split())[:92]
            self.history.addItem(QListWidgetItem(label or "Whitespace"))

    def restore_clip(self, _item=None):
        row = self.history.currentRow()
        if row >= 0:
            kind, content = self.entries[row]
            clipboard = QApplication.clipboard()
            if kind == "image":
                clipboard.setImage(content)
            else:
                clipboard.setText(content)

    def open_windows(self, uri):
        try:
            os.startfile(uri)
        except OSError:
            self.status.setText("Could not open Windows Settings.")

    def remember_window(self):
        handle = self.user32.GetForegroundWindow()
        if handle:
            pid = w.DWORD()
            self.user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
            if pid.value and pid.value != os.getpid():
                self.last_window = handle, pid.value

    def snap(self, side):
        if self.last_window is None:
            self.status.setText("Select a window before opening Desktop tools.")
            return
        handle, expected_pid = self.last_window
        pid = w.DWORD()
        self.user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        if pid.value != expected_pid:
            self.status.setText("That window is no longer open.")
            return
        from PyQt6.QtCore import QPoint
        rect = w.RECT()
        if not self.user32.GetWindowRect(handle, ctypes.byref(rect)):
            return
        screen = QGuiApplication.screenAt(QPoint((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2))
        screen = screen or self.workspace.screen()
        area = screen.availableGeometry()
        width = area.width() // 2
        ratio = screen.devicePixelRatio()
        if ratio != 1:
            # Qt uses logical coordinates. Leave the scaling to Windows Snap on mixed-DPI displays.
            self.status.setText("Use Win+Left or Win+Right on the target window on a scaled display.")
            return
        self.user32.ShowWindow(handle, 9)
        if self.user32.SetWindowPos(handle, None, area.x() + side * width, area.y(), width, area.height(), 0x14):
            self.status.setText("Window snapped.")

    def capture(self, color):
        if self.ocr and self.ocr.isRunning():
            return
        self.workspace.hide()
        QTimer.singleShot(180, lambda: self.show_selection(color))

    def show_selection(self, color):
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        self.selection = ScreenSelection(screen, color)
        if self.selection.image.isNull():
            self.workspace.show()
            self.status.setText("Windows did not provide a screen image.")
            self.selection.close()
            return
        self.selection.selected.connect(self.copy_color if color else self.start_ocr)
        self.selection.destroyed.connect(lambda: self.workspace.show())
        self.selection.show()
        self.selection.activateWindow()

    def copy_color(self, color):
        QApplication.clipboard().setText(color)
        self.status.setText(f"Copied {color}")

    def start_ocr(self, image):
        self.status.setText("Recognizing text...")
        self.ocr = TextRecognition(image, self.workspace)
        self.ocr.completed.connect(self.ocr_result)
        self.ocr.start()

    def ocr_result(self, text, error):
        if text:
            QApplication.clipboard().setText(text)
        self.status.setText(error or "Copied recognized text")

    def choose_project(self):
        path = QFileDialog.getExistingDirectory(self.workspace, "Choose a Git project")
        if path:
            self.project = path
            self.refresh_git()

    def refresh_git(self):
        if self.project and self.git.state() == QProcess.ProcessState.NotRunning:
            self.git.start("git", ["--no-optional-locks", "-C", self.project, "status", "--short", "--branch", "--untracked-files=no"])

    def git_finished(self, code, _status):
        lines = bytes(self.git.readAllStandardOutput()).decode("utf-8", errors="replace").splitlines()
        if code or not lines:
            self.git_label.setText("Git Pulse: project unavailable")
            return
        conflicts = sum(row[:2] in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"} for row in lines[1:])
        self.git_label.setText(f"Git: {lines[0].removeprefix('## ')} | {len(lines)-1} tracked changes | {conflicts} conflicts")

    def start_build(self):
        if not self.project or not (Path(self.project) / "package.json").is_file():
            self.build_status.setText("Choose an npm project first.")
            return
        if self.command.state() != QProcess.ProcessState.NotRunning:
            return
        from PyQt6.QtWidgets import QMessageBox
        if QMessageBox.question(self.workspace, "Run npm build", f"Run this project's npm build script?\n{self.project}") != QMessageBox.StandardButton.Yes:
            return
        self.command_kind = "build"
        self.build_status.setText("Build Pulse: npm build running...")
        self.command.setWorkingDirectory(self.project)
        shell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "cmd.exe"
        self.command.start(str(shell), ["/d", "/c", "npm.cmd run build"])

    def docker_status(self):
        if self.command.state() != QProcess.ProcessState.NotRunning:
            return
        self.command_kind = "docker"
        self.build_status.setText("Checking running containers...")
        self.command.setWorkingDirectory("")
        self.command.start("docker", ["ps", "--format", "{{.Names}} | {{.Status}}"])

    def command_finished(self, code, _status):
        output = bytes(self.command.readAllStandardOutput()).decode("utf-8", errors="replace").splitlines()
        self.command.readAllStandardError()
        if self.command_kind == "docker":
            self.build_status.setText("Docker unavailable" if code else "\n".join(output[:3]) or "No running containers.")
        else:
            self.build_status.setText("Build Pulse: completed" if code == 0 else f"Build Pulse: failed ({code})")

    def start_meeting(self):
        self.meeting_started = time.monotonic()
        self.tick()

    def stop_meeting(self):
        self.meeting_started = None
        self.tick()

    def meeting_status(self):
        if self.meeting_started is None:
            return ""
        minutes, seconds = divmod(int(time.monotonic() - self.meeting_started), 60)
        return f"Meeting {minutes:02}:{seconds:02}"

    def tick(self):
        battery = psutil.sensors_battery()
        if battery:
            remaining = int(battery.secsleft // 60)
            extra = " | Charging or on AC" if battery.power_plugged else f" | About {remaining} min left" if remaining >= 0 else ""
            self.battery.setText(f"Battery {battery.percent:.0f}%{extra}")
        else:
            self.battery.setText("No battery reported by Windows.")
        self.meeting.setText(self.meeting_status() or "Meeting timer: not running")
        self.privacy.setText(" | ".join(self.privacy_status(kind, title) for kind, title in (("webcam", "Camera"), ("microphone", "Mic"))))

    def privacy_status(self, kind, title):
        root = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore"
        names = []
        def scan(key):
            for index in range(winreg.QueryInfoKey(key)[0]):
                child = winreg.EnumKey(key, index)
                with winreg.OpenKey(key, child) as handle:
                    if child == "NonPackaged":
                        scan(handle)
                    else:
                        try:
                            started = winreg.QueryValueEx(handle, "LastUsedTimeStart")[0]
                            stopped = winreg.QueryValueEx(handle, "LastUsedTimeStop")[0]
                            if started and stopped == 0:
                                names.append(child.split("#")[-1])
                        except FileNotFoundError:
                            continue
        if not self.workspace.isVisible():
            return title + ": see Windows privacy settings"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, root + "\\" + kind) as key:
                scan(key)
        except OSError:
            return title + ": unavailable"
        return f"{title}: {', '.join(names[:2])}" if names else title + ": no activity reported"
