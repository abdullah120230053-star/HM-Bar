from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, Qt
from PyQt6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget
import qtawesome as qta


class AppLauncher(QWidget):
    def __init__(self, parent, entries):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.surface = QWidget(objectName="LauncherSurface")
        outer.addWidget(self.surface)
        layout = QVBoxLayout(self.surface)
        layout.setContentsMargins(19, 16, 19, 19)
        layout.setSpacing(12)
        title = QLabel("App launcher", objectName="LauncherTitle")
        layout.addWidget(title)
        grid = QGridLayout()
        grid.setSpacing(8)
        layout.addLayout(grid)
        self.tiles = []
        for index, (name, icon, color, action) in enumerate(entries):
            tile = QPushButton(name, icon=qta.icon(icon, color=color), objectName="AppTile")
            tile.setIconSize(QSize(21, 21))
            tile.setMinimumHeight(48)
            tile.setCursor(Qt.CursorShape.PointingHandCursor)
            tile.clicked.connect(lambda _, callback=action: self.run(callback))
            grid.addWidget(tile, index // 3, index % 3)
            self.tiles.append(tile)
        self.setStyleSheet("""
            #LauncherSurface { background: #171b26; border: 1px solid #3a445b; border-radius: 20px; }
            #LauncherTitle { color: #f7f8ff; font: 600 17px 'Segoe UI'; }
            #AppTile {
                text-align: left; padding: 0 9px; border: 1px solid #323c52;
                border-radius: 11px; color: #f1f3fb; background: #222a3b;
                font: 600 12px 'Segoe UI';
            }
            #AppTile:hover, #AppTile:focus { border-color: #8cb5ff; background: #303e57; }
            #AppTile:pressed { background: #3c4c69; }
        """)
        self.fade = QPropertyAnimation(self, b"windowOpacity")
        self.fade.setDuration(200)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide = QPropertyAnimation(self, b"pos")
        self.slide.setDuration(280)
        self.slide.setEasingCurve(QEasingCurve.Type.OutCubic)

    def run(self, action):
        self.close()
        action()

    def open_below(self, anchor, screen, animated=True):
        self.adjustSize()
        x = min(max(anchor.center().x() - self.width() // 2, screen.left() + 8),
                max(screen.left() + 8, screen.right() - self.width() - 7))
        y = anchor.bottom() + 8
        if y + self.height() > screen.bottom():
            y = max(screen.top() + 8, anchor.top() - self.height() - 8)
        end = QPoint(x, y)
        self.slide.stop()
        self.fade.stop()
        self.setWindowOpacity(0.0 if animated else 1.0)
        self.move(end + QPoint(0, -10) if animated else end)
        self.show()
        self.tiles[0].setFocus()
        if animated:
            self.slide.setStartValue(self.pos())
            self.slide.setEndValue(end)
            self.slide.start()
            self.fade.setStartValue(0.0)
            self.fade.setEndValue(1.0)
            self.fade.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
