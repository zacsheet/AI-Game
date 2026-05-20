from __future__ import annotations

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QProgressBar, QPushButton, QVBoxLayout, QWidget


class LogPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.timeline = QProgressBar()
        self.timeline.setRange(0, 100)
        self.timeline.setValue(0)
        self.timeline.setTextVisible(True)
        self.timeline.setFormat("运行时间线")

        self.logs = QListWidget()
        self.copy_button = QPushButton("复制")
        self.clear_button = QPushButton("清空")

        header = QHBoxLayout()
        header.addWidget(QLabel("运行日志"), 1)
        header.addWidget(self.copy_button)
        header.addWidget(self.clear_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("时间线"))
        layout.addWidget(self.timeline)
        layout.addLayout(header)
        layout.addWidget(self.logs, 1)

        self.copy_button.clicked.connect(self.copy_all)
        self.clear_button.clicked.connect(self.clear)

    def append(self, level: str, text: str) -> None:
        prefix = {
            "ok": "[OK]",
            "skip": "[SKIP]",
            "warn": "[WARN]",
            "error": "[ERROR]",
            "stop": "[STOP]",
            "info": "[INFO]",
        }.get(level, "[LOG]")
        self.logs.addItem(f"{prefix} {text}")
        self.logs.scrollToBottom()

    def clear(self) -> None:
        self.logs.clear()

    def copy_all(self) -> None:
        lines = [self.logs.item(index).text() for index in range(self.logs.count())]
        QGuiApplication.clipboard().setText("\n".join(lines))
