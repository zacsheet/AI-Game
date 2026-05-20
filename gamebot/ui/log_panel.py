from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QListWidget, QProgressBar, QVBoxLayout, QWidget


class LogPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.timeline = QProgressBar()
        self.timeline.setRange(0, 100)
        self.timeline.setValue(0)
        self.timeline.setTextVisible(True)
        self.timeline.setFormat("运行时间线")

        self.logs = QListWidget()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("时间线"))
        layout.addWidget(self.timeline)
        layout.addWidget(QLabel("运行日志"))
        layout.addWidget(self.logs, 1)

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
