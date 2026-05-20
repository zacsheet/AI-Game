from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from gamebot.models import Task


class TaskPanel(QWidget):
    task_selected = pyqtSignal(int)
    add_task_requested = pyqtSignal()
    delete_task_requested = pyqtSignal(int)
    move_task_requested = pyqtSignal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self.list = QListWidget()
        self.move_up_button = QPushButton("上移")
        self.move_down_button = QPushButton("下移")
        self.add_button = QPushButton("+ 新建任务")
        self.delete_button = QPushButton("删除任务")

        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        move_layout = QHBoxLayout()
        move_layout.addWidget(self.move_up_button)
        move_layout.addWidget(self.move_down_button)
        layout.addLayout(move_layout)
        layout.addWidget(self.add_button)
        layout.addWidget(self.delete_button)

        self.list.currentRowChanged.connect(self.task_selected.emit)
        self.list.currentRowChanged.connect(self._update_buttons)
        self.move_up_button.clicked.connect(lambda: self._request_move(-1))
        self.move_down_button.clicked.connect(lambda: self._request_move(1))
        self.add_button.clicked.connect(self.add_task_requested.emit)
        self.delete_button.clicked.connect(self._request_delete)

    def set_tasks(self, tasks: list[Task]) -> None:
        current = self.list.currentRow()
        self.list.clear()
        for task in tasks:
            status = "启用" if task.enabled else "暂停"
            item = QListWidgetItem(f"{task.name}\n{task.interval_ms / 1000:g}s · {status}")
            item.setData(32, task.id)
            self.list.addItem(item)
        if tasks:
            self.list.setCurrentRow(min(max(current, 0), len(tasks) - 1))
        self._update_buttons(self.list.currentRow())
        self.delete_button.setEnabled(bool(tasks))

    def _request_delete(self) -> None:
        self.delete_task_requested.emit(self.list.currentRow())

    def _request_move(self, direction: int) -> None:
        row = self.list.currentRow()
        self.move_task_requested.emit(row, row + direction)

    def _update_buttons(self, row: int) -> None:
        count = self.list.count()
        self.move_up_button.setEnabled(count > 1 and row > 0)
        self.move_down_button.setEnabled(count > 1 and 0 <= row < count - 1)
