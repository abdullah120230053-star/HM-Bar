from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QSizePolicy


class ElidedLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.full_text = ""
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def setText(self, text):
        self.full_text = text
        self.refresh_text()

    def refresh_text(self):
        text = self.fontMetrics().elidedText(self.full_text, Qt.TextElideMode.ElideRight, self.contentsRect().width())
        if text != self.text():
            super().setText(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_text()
