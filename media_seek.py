from dataclasses import dataclass
import time

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSlider, QStyle, QStyleOptionSlider, QWidget


@dataclass(frozen=True)
class TrackTimeline:
    track_id: int
    start_ms: int
    end_ms: int
    position_ms: int
    seek_from_ms: int
    seek_to_ms: int
    seek_enabled: bool


class PositionSlider(QSlider):
    committed = pyqtSignal(int)

    def __init__(self):
        super().__init__(Qt.Orientation.Horizontal)

    def position_at(self, x):
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        style = self.style()
        groove = style.subControlRect(QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderGroove, self)
        handle = style.subControlRect(QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderHandle, self)
        offset = groove.left() + handle.width() // 2
        return QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), round(x) - offset, max(1, groove.width() - handle.width()), option.upsideDown
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.setSliderDown(True)
            self.setValue(self.position_at(event.position().x()))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown():
            self.setValue(self.position_at(event.position().x()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isSliderDown():
            self.setValue(self.position_at(event.position().x()))
            self.setSliderDown(False)
            self.committed.emit(self.value())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        before = self.value()
        super().keyPressEvent(event)
        if self.value() != before:
            self.committed.emit(self.value())

    def wheelEvent(self, event):
        event.ignore()


class MediaSeekBar(QWidget):
    seek_requested = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(27)
        self.timeline = None
        self.hold_until = 0.0
        row = QHBoxLayout(self)
        row.setContentsMargins(22, 0, 22, 4)
        row.setSpacing(8)
        self.elapsed = QLabel("--:--")
        self.duration = QLabel("--:--")
        for label in (self.elapsed, self.duration):
            label.setMinimumWidth(36)
            label.setStyleSheet("font-size: 10px; color: #d3d8e5;")
        self.duration.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.slider = PositionSlider()
        self.slider.setAccessibleName("Song position")
        self.slider.setSingleStep(5000)
        self.slider.setPageStep(15000)
        self.slider.valueChanged.connect(self.show_elapsed)
        self.slider.committed.connect(self.commit)
        row.addWidget(self.elapsed)
        row.addWidget(self.slider, 1)
        row.addWidget(self.duration)
        self.set_accent("#8bb6ff")
        self.update_timeline(None)

    def set_accent(self, accent):
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ background: #465168; height: 4px; border-radius: 2px; }}
            QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: #f2f5ff; width: 11px; margin: -4px 0; border-radius: 5px; }}
            QSlider::handle:horizontal:hover, QSlider::handle:horizontal:focus {{ background: {accent}; }}
            QSlider::sub-page:horizontal:disabled {{ background: #64728c; }}
            QSlider::handle:horizontal:disabled {{ background: #64728c; }}
        """)

    @staticmethod
    def format_time(ms):
        minutes, seconds = divmod(max(0, ms) // 1000, 60)
        return f"{minutes}:{seconds:02d}"

    def show_elapsed(self, position):
        if self.timeline:
            self.elapsed.setText(self.format_time(position - self.timeline.start_ms))

    def update_timeline(self, timeline):
        previous = self.timeline
        self.timeline = timeline
        if timeline is None or previous is None or timeline.track_id != previous.track_id:
            self.slider.setSliderDown(False)
            self.hold_until = 0.0
        if timeline is None:
            self.slider.setEnabled(False)
            self.slider.setToolTip("Timeline unavailable for this player")
            self.slider.setRange(0, 100)
            self.slider.setValue(0)
            self.elapsed.setText("--:--")
            self.duration.setText("--:--")
            return
        if not timeline.seek_enabled:
            self.slider.setSliderDown(False)
        self.slider.setEnabled(timeline.seek_enabled)
        self.slider.setToolTip("Click or drag to seek" if timeline.seek_enabled else "This player does not allow seeking")
        self.slider.setRange(timeline.start_ms, timeline.end_ms)
        self.duration.setText(self.format_time(timeline.end_ms - timeline.start_ms))
        if not self.slider.isSliderDown() and time.monotonic() >= self.hold_until:
            self.slider.setValue(timeline.position_ms)
            self.show_elapsed(self.slider.value())

    def commit(self, position):
        timeline = self.timeline
        if timeline and timeline.seek_enabled:
            position = min(timeline.seek_to_ms, max(timeline.seek_from_ms, position))
            self.slider.setValue(position)
            self.hold_until = time.monotonic() + 1.1
            self.seek_requested.emit(timeline.track_id, position)

    def seek_finished(self, track_id, success):
        if self.timeline and self.timeline.track_id == track_id and not success:
            self.hold_until = 0.0
            self.update_timeline(self.timeline)
            self.slider.setToolTip("The player did not accept the seek")
