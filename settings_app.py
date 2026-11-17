import sys

from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, pyqtProperty
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFormLayout, QFrame,
    QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)
from preferences import PROFILE, PREFERENCES, read_json, save_preferences
from themes import THEMES


class IslandPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(174)
        self.surface = QColor("#101116")
        self.accent = QColor("#8bb6ff")
        self.notch = False
        self._progress = 1.0
        self.motion = QPropertyAnimation(self, b"progress")
        self.motion.setDuration(410)
        self.motion.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = value
        self.update()

    def apply(self, surface, accent, shape, animate=True):
        self.surface, self.accent = QColor(surface), QColor(accent)
        self.notch = shape == "Notch Nook"
        self.motion.stop()
        self.progress = 1.0
        if animate:
            self.motion.setStartValue(0.0)
            self.motion.setEndValue(1.0)
            self.motion.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        backdrop = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        backdrop.setColorAt(0, QColor("#283859"))
        backdrop.setColorAt(1, QColor("#151b2b"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(backdrop)
        painter.drawRoundedRect(bounds, 15, 15)
        width = min(bounds.width() - 34, 148 + self.progress * 57)
        body = QRectF((self.width() - width) / 2, 1 if self.notch else 29, width, 43)
        painter.setBrush(self.surface)
        painter.setPen(QPen(self.accent.darker(165), 1))
        if self.notch:
            path = QPainterPath()
            path.moveTo(body.left() - 11, body.top())
            path.quadTo(body.left(), body.top(), body.left(), body.top() + 11)
            path.lineTo(body.left(), body.bottom() - 12)
            path.quadTo(body.left(), body.bottom(), body.left() + 12, body.bottom())
            path.lineTo(body.right() - 12, body.bottom())
            path.quadTo(body.right(), body.bottom(), body.right(), body.bottom() - 12)
            path.lineTo(body.right(), body.top() + 11)
            path.quadTo(body.right(), body.top(), body.right() + 11, body.top())
            path.closeSubpath()
            painter.drawPath(path)
        else:
            painter.drawRoundedRect(body, 21, 21)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.accent)
        painter.drawEllipse(QPointF(body.left() + 20, body.center().y()), 4, 4)
        painter.setPen(QColor("#f7f8ff"))
        painter.drawText(body.adjusted(33, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter, "Now playing")


STYLE = """
QWidget { background: #111521; color: #eef2ff; font: 13px 'Segoe UI'; }
QLabel { background: transparent; }
QLabel#Hero { font-size: 28px; font-weight: 700; }
QLabel#Muted, QLabel#Status { color: #aab6d0; }
QFrame#PreviewCard { background: #1a2132; border: 1px solid #344057; border-radius: 17px; }
QTabWidget::pane { border: 1px solid #344057; border-radius: 13px; top: -1px; background: #1a2132; }
QWidget#Page { background: #1a2132; border-radius: 13px; }
QTabBar::tab { border: 1px solid #344057; padding: 8px 13px; border-radius: 8px;
               background: #192033; color: #bfc9df; margin-right: 4px; }
QTabBar::tab:selected { background: #33466a; color: #fff; border-color: #83adf7; }
QComboBox, QSpinBox, QPushButton {
  background: #242e45; color: #edf2ff; border: 1px solid #425271;
  border-radius: 8px; padding: 6px 9px; min-height: 20px;
}
QComboBox::drop-down { width: 23px; border: 0; }
QComboBox::down-arrow { width: 7px; height: 7px; border-right: 1px solid #bfcaff; border-bottom: 1px solid #bfcaff; }
QComboBox QAbstractItemView { background: #242e45; selection-background-color: #375381; }
QPushButton:hover, QPushButton:focus, QComboBox:focus, QSpinBox:focus { border-color: #9bc0ff; }
QPushButton#Save { background: #9bc0ff; color: #111b30; font-weight: 700; padding: 7px 18px; }
QPushButton#Save:hover { background: #c4dbff; }
QCheckBox { background: transparent; spacing: 10px; padding: 4px 0; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #657694; }
QCheckBox::indicator:checked { background: #8db7ff; border: 3px solid #354b70; }
"""


class Settings(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HM-Bar Settings")
        self.resize(780, 530)
        self.setMinimumSize(690, 480)
        self.setStyleSheet(STYLE)
        self.active = {**read_json(PROFILE / "settings.json"), **read_json(PREFERENCES)}
        self.inputs = {}
        self.accent = self.active.get("custom_accent", "")
        root = QVBoxLayout(self)
        root.setContentsMargins(25, 22, 25, 22)
        root.setSpacing(13)
        root.addWidget(QLabel("HM-Bar", objectName="Hero"))
        root.addWidget(QLabel("Customize your island, launcher, and now playing view.", objectName="Muted"))
        body = QHBoxLayout()
        body.setSpacing(14)
        root.addLayout(body, 1)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        body.addWidget(self.tabs, 3)

        look, look_form = self.page("Appearance")
        self.combo(look_form, "theme", "Theme", list(THEMES), "Obsidian")
        self.combo(look_form, "island_style", "Shape", ["Default", "Liquid Glass", "Notch Nook"], "Default")
        self.accent_button = QPushButton("Choose accent")
        self.accent_button.clicked.connect(self.pick_accent)
        look_form.addRow("Custom accent", self.accent_button)
        reset = QPushButton("Use theme accent")
        reset.clicked.connect(lambda: self.set_accent(""))
        look_form.addRow("", reset)
        self.combo(look_form, "panel_motion", "Panel transitions", ["Smooth", "Fast", "Reduced"], "Smooth")
        look.addStretch()

        media, media_form = self.page("Now playing")
        self.combo(media_form, "media_priority", "Media source", ["Auto", "Spotify first"], "Auto")
        self.combo(media_form, "animation_style", "Media effects", ["Fluid Blobs", "Glow Sweep", "Neon Border", "Off"], "Fluid Blobs")
        intro = QSpinBox()
        intro.setRange(1, 8)
        intro.setSuffix(" sec")
        intro.setValue(self.active.get("cover_intro_seconds", 3))
        media_form.addRow("Cover intro", intro)
        self.inputs["cover_intro_seconds"] = intro
        for key, text in (
            ("show_now_playing", "Show now playing on the collapsed island"),
            ("auto_open_media", "Switch to media when a new session appears"),
            ("lyrics_enabled", "Show synced lyrics"),
            ("animate_artwork", "Animate cover artwork"),
        ):
            self.check(media, key, text)
        media.addStretch()

        launcher, launcher_form = self.page("Launcher")
        self.combo(launcher_form, "default_panel", "Default panel",
                   ["Media", "Performance", "Weather", "Calendar", "Month", "Basics"], "Performance")
        self.check(launcher, "launcher_animations", "Animate the app launcher")
        shortcuts = QLabel("Double-click the island to open apps.\nCtrl+H hides or restores the island.", objectName="Muted")
        launcher.addWidget(shortcuts)
        launcher.addStretch()

        card = QFrame(objectName="PreviewCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 13, 14, 14)
        card_layout.addWidget(QLabel("Live preview"))
        self.preview = IslandPreview()
        card_layout.addWidget(self.preview)
        self.swatches = QHBoxLayout()
        self.swatches.setSpacing(5)
        for name, (surface, accent) in THEMES.items():
            swatch = QPushButton()
            swatch.setFixedSize(28, 28)
            swatch.setToolTip(name)
            swatch.setAccessibleName(name)
            swatch.setStyleSheet(f"background:{surface};border-color:{accent or '#8bb6ff'};border-radius:8px;padding:0;")
            swatch.clicked.connect(lambda _, theme=name: self.inputs["theme"].setCurrentText(theme))
            self.swatches.addWidget(swatch)
        self.swatches.addStretch()
        card_layout.addLayout(self.swatches)
        card_layout.addStretch()
        body.addWidget(card, 2)

        footer = QHBoxLayout()
        self.status = QLabel("Changes apply when you save.", objectName="Status")
        footer.addWidget(self.status, 1)
        save = QPushButton("Save changes", objectName="Save")
        save.clicked.connect(self.save)
        footer.addWidget(save)
        root.addLayout(footer)
        for key in ("theme", "island_style", "panel_motion"):
            self.inputs[key].currentTextChanged.connect(self.update_preview)
        self.tab_animation = None
        self.tabs.currentChanged.connect(self.animate_tab)
        self.set_accent(self.accent)

    def page(self, label):
        page = QWidget(objectName="Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 15, 14, 14)
        layout.setSpacing(9)
        form = QFormLayout()
        form.setVerticalSpacing(9)
        layout.addLayout(form)
        self.tabs.addTab(page, label)
        return layout, form

    def combo(self, form, key, label, values, default):
        value = QComboBox()
        value.addItems(values)
        value.setCurrentText(self.active.get(key, default))
        form.addRow(label, value)
        self.inputs[key] = value

    def check(self, layout, key, label):
        check = QCheckBox(label)
        check.setChecked(self.active.get(key, True))
        layout.addWidget(check)
        self.inputs[key] = check

    def animate_tab(self, index):
        if self.tab_animation:
            self.tab_animation.stop()
            self.tab_animation.targetObject().setOpacity(1)
        if self.inputs["panel_motion"].currentText() == "Reduced":
            return
        page = self.tabs.widget(index)
        effect = page.graphicsEffect()
        if effect is None:
            effect = QGraphicsOpacityEffect(page)
            page.setGraphicsEffect(effect)
        self.tab_animation = QPropertyAnimation(effect, b"opacity")
        self.tab_animation.setDuration(195)
        self.tab_animation.setStartValue(0.4)
        self.tab_animation.setEndValue(1)
        self.tab_animation.start()

    def update_preview(self):
        surface, accent = THEMES[self.inputs["theme"].currentText()]
        self.preview.apply(surface, self.accent or accent or "#8bb6ff",
                           self.inputs["island_style"].currentText(),
                           self.inputs["panel_motion"].currentText() != "Reduced")

    def pick_accent(self):
        color = QColorDialog.getColor(QColor(self.accent or "#8bb6ff"), self)
        if color.isValid():
            self.set_accent(color.name())

    def set_accent(self, value):
        self.accent = value
        self.accent_button.setText(value or "Choose accent")
        self.update_preview()

    def save(self):
        values = {}
        for key, control in self.inputs.items():
            if isinstance(control, QCheckBox):
                values[key] = control.isChecked()
            elif isinstance(control, QSpinBox):
                values[key] = control.value()
            else:
                values[key] = control.currentText()
        try:
            save_preferences({**values, "custom_accent": self.accent})
        except OSError as error:
            QMessageBox.warning(self, "Could not save changes", str(error))
            return
        self.status.setText("Saved. The island will refresh shortly.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Settings()
    window.show()
    sys.exit(app.exec())
