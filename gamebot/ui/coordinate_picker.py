from __future__ import annotations

import pyautogui

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QKeyEvent
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class CoordinatePicker(QDialog):
    coordinate_selected = pyqtSignal(int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("坐标拾取")
        self.setMinimumWidth(360)
        self.value_label = QLabel("X: 0  Y: 0")
        self.value_label.setStyleSheet("font-size: 24px; font-weight: 600;")
        self.hint_label = QLabel("移动鼠标查看坐标。按 C 复制，Enter 用于当前动作，Esc 关闭。")

        self.copy_button = QPushButton("复制坐标 (C)")
        self.use_button = QPushButton("用于当前动作 (Enter)")
        self.close_button = QPushButton("关闭 (Esc)")

        button_row = QHBoxLayout()
        button_row.addWidget(self.copy_button)
        button_row.addWidget(self.use_button)
        button_row.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.value_label)
        layout.addWidget(self.hint_label)
        layout.addLayout(button_row)

        self.timer = QTimer(self)
        self.timer.setInterval(80)
        self.timer.timeout.connect(self._update_position)
        self.copy_button.clicked.connect(self._copy)
        self.use_button.clicked.connect(self._use_current)
        self.close_button.clicked.connect(self.close)
        self._update_position()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.timer.start()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def hideEvent(self, event) -> None:
        self.timer.stop()
        super().hideEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key.Key_C:
            self._copy()
            event.accept()
            return
        if key in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self._use_current()
            event.accept()
            return
        if key == Qt.Key.Key_Escape:
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def _current_position(self) -> tuple[int, int]:
        point = pyautogui.position()
        return int(point.x), int(point.y)

    def _update_position(self) -> None:
        x, y = self._current_position()
        self.value_label.setText(f"X: {x}  Y: {y}")

    def _copy(self) -> None:
        x, y = self._current_position()
        QGuiApplication.clipboard().setText(f"{x},{y}")
        self.value_label.setText(f"X: {x}  Y: {y}  已复制")

    def _use_current(self) -> None:
        x, y = self._current_position()
        self.coordinate_selected.emit(x, y)
