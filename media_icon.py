from PyQt6.QtCore import Qt, QEasingCurve, QPointF, QRectF, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QWidget


class MediaIcon(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(26, 26)
        self.pixmap = QPixmap()
        self._reveal = 1.0
        self.animation = QPropertyAnimation(self, b"reveal")
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setDuration(460)

    @pyqtProperty(float)
    def reveal(self):
        return self._reveal

    @reveal.setter
    def reveal(self, value):
        self._reveal = value
        self.update()

    def setPixmap(self, pixmap, animate=False):
        if self.pixmap.cacheKey() == pixmap.cacheKey():
            return
        self.pixmap = pixmap
        self.animation.stop()
        self.reveal = 1.0
        if animate:
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            self.animation.start()
        self.update()

    def paintEvent(self, event):
        if self.pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        progress = self.reveal
        size = 19.0 + 7.0 * progress if self.pixmap.width() >= 26 else 18.0
        box = QRectF(0, 0, size, size)
        box.moveCenter(QPointF(13, 13))
        clip = QPainterPath()
        clip.addRoundedRect(box, 5, 5)
        painter.setClipPath(clip)
        painter.setOpacity(0.25 + 0.75 * progress)
        source = QRectF(self.pixmap.rect())
        side = min(source.width(), source.height())
        square = QRectF(0, 0, side, side)
        square.moveCenter(source.center())
        painter.drawPixmap(box, self.pixmap, square)
