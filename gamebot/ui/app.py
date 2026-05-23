from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import threading

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolBar,
    QWidget,
)

from gamebot.core.scheduler import Scheduler
from gamebot.models import Project, Task
from gamebot.models.config import new_id
from gamebot.ui.editor_panel import EditorPanel
from gamebot.ui.log_panel import LogPanel
from gamebot.ui.task_panel import TaskPanel


class LogBridge(QObject):
    received = pyqtSignal(str, str)


class ControlBridge(QObject):
    stop_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    coordinate_requested = pyqtSignal()
    record_requested = pyqtSignal()
    step_finished = pyqtSignal()


class GameBotWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GameBot")
        self.project_path = Path("config/project.json")
        self.project = self._initial_project()
        self.scheduler: Scheduler | None = None
        self.step_scheduler: Scheduler | None = None
        self.step_running = False
        self.step_positions: dict[str, int] = {}
        self.bridge = LogBridge()
        self.controls = ControlBridge()

        self.task_panel = TaskPanel()
        self.editor = EditorPanel()
        self.log_panel = LogPanel()

        self._build()
        self._connect()
        self._refresh()
        self._register_hotkeys()

    def _initial_project(self) -> Project:
        if self.project_path.exists():
            return Project.load(self.project_path)
        return Project(tasks=[Task(name="自动战斗")])

    def _build(self) -> None:
        toolbar = QToolBar()
        self.import_button = QPushButton("导入")
        self.export_button = QPushButton("导出")
        self.run_button = QPushButton("运行")
        self.step_button = QPushButton("单步")
        self.stop_button = QPushButton("停止")
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.export_button)
        toolbar.addSeparator()
        toolbar.addWidget(self.step_button)
        toolbar.addWidget(self.run_button)
        toolbar.addWidget(self.stop_button)
        self.addToolBar(toolbar)

        splitter = QSplitter()
        splitter.addWidget(self.task_panel)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.log_panel)
        splitter.setSizes([240, 720, 360])

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(splitter)
        self.setCentralWidget(container)
        self.setStatusBar(QStatusBar())

    def _connect(self) -> None:
        self.task_panel.task_selected.connect(self._select_task)
        self.task_panel.add_task_requested.connect(self._add_task)
        self.task_panel.duplicate_task_requested.connect(self._duplicate_task)
        self.task_panel.delete_task_requested.connect(self._delete_task)
        self.task_panel.move_task_requested.connect(self._move_task)
        self.editor.changed.connect(self._on_changed)
        self.editor.log_requested.connect(self._append_log)
        self.import_button.clicked.connect(self._import_project)
        self.export_button.clicked.connect(self._export_project)
        self.step_button.clicked.connect(self._step_once)
        self.run_button.clicked.connect(self._start)
        self.stop_button.clicked.connect(self._stop)
        self.bridge.received.connect(self._append_log)
        self.controls.stop_requested.connect(self._stop)
        self.controls.pause_requested.connect(self._toggle_pause)
        self.controls.coordinate_requested.connect(self.editor.show_coordinate_picker)
        self.controls.record_requested.connect(self.editor.toggle_recording)
        self.controls.step_finished.connect(self._on_step_finished)

    def _refresh(self) -> None:
        self.task_panel.set_tasks(self.project.tasks)
        row = self.task_panel.list.currentRow()
        self._select_task(row if row >= 0 else 0)
        self.statusBar().showMessage(f"{self.project.name} | {len(self.project.tasks)} 个任务")

    def _select_task(self, row: int) -> None:
        task = self.project.tasks[row] if 0 <= row < len(self.project.tasks) else None
        self.editor.set_task(task, self.project_path.parent)

    def _add_task(self) -> None:
        self.project.tasks.append(Task(name=f"任务 {len(self.project.tasks) + 1}"))
        self._save_silent()
        self._refresh()
        self.task_panel.list.setCurrentRow(len(self.project.tasks) - 1)

    def _duplicate_task(self, row: int) -> None:
        if row < 0 or row >= len(self.project.tasks):
            return
        source = self.project.tasks[row]
        copied = deepcopy(source)
        copied.id = new_id("task")
        copied.name = f"{source.name} 副本"
        copied.enabled = True
        rule_id_map: dict[str, str] = {}
        for rule in copied.rules:
            old_id = rule.id
            rule.id = new_id("rule")
            rule_id_map[old_id] = rule.id
        for rule in copied.rules:
            if rule.next_on_found in rule_id_map:
                rule.next_on_found = rule_id_map[rule.next_on_found]
            if rule.next_on_not_found in rule_id_map:
                rule.next_on_not_found = rule_id_map[rule.next_on_not_found]
        self.project.tasks.insert(row + 1, copied)
        self._save_silent()
        self.task_panel.set_tasks(self.project.tasks)
        self.task_panel.list.setCurrentRow(row + 1)
        self._select_task(row + 1)
        self._append_log("info", f"已复制任务 {source.name}")

    def _delete_task(self, row: int) -> None:
        if row < 0 or row >= len(self.project.tasks):
            return
        task = self.project.tasks[row]
        answer = QMessageBox.question(
            self,
            "删除任务",
            f"确定删除任务“{task.name}”吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.project.tasks.pop(row)
        self._save_silent()
        self.task_panel.set_tasks(self.project.tasks)
        next_row = min(row, len(self.project.tasks) - 1)
        self.task_panel.list.setCurrentRow(next_row)
        self._select_task(next_row)
        self.statusBar().showMessage(f"{self.project.name} | {len(self.project.tasks)} 个任务")
        self._append_log("info", f"已删除任务 {task.name}")

    def _move_task(self, from_row: int, to_row: int) -> None:
        if from_row < 0 or from_row >= len(self.project.tasks):
            return
        if to_row < 0 or to_row >= len(self.project.tasks):
            return
        task = self.project.tasks.pop(from_row)
        self.project.tasks.insert(to_row, task)
        self._save_silent()
        self.task_panel.set_tasks(self.project.tasks)
        self.task_panel.list.setCurrentRow(to_row)
        self._select_task(to_row)
        self._append_log("info", f"任务顺序已更新 {task.name}")

    def _on_changed(self) -> None:
        self._save_silent()
        self.task_panel.set_tasks(self.project.tasks)

    def _import_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "导入项目", "config", "JSON (*.json)")
        if not path:
            return
        try:
            self.project_path = Path(path)
            self.project = Project.load(path)
            self._refresh()
            self._append_log("info", f"已导入 {path}")
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))

    def _export_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出项目", str(self.project_path), "JSON (*.json)")
        if not path:
            return
        try:
            self.project.save(path)
            self.project_path = Path(path)
            self._append_log("info", f"已导出 {path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def _start(self) -> None:
        if self.step_running:
            self._append_log("warn", "单步执行中，暂时不能启动连续运行")
            return
        self._save_silent()
        if self.scheduler and self.scheduler.running:
            return
        self.scheduler = Scheduler(self.project, self.project_path.parent, self.bridge.received.emit)
        self.scheduler.start()
        self.run_button.setEnabled(False)
        self.step_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.statusBar().showMessage("运行中")

    def _stop(self) -> None:
        if self.scheduler:
            self.scheduler.stop()
        self.run_button.setEnabled(True)
        self.step_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.statusBar().showMessage("已停止")

    def _step_once(self) -> None:
        if self.scheduler and self.scheduler.running:
            self._append_log("warn", "连续运行中，暂时不能单步执行")
            return
        if self.step_running:
            return
        row = self.task_panel.list.currentRow()
        task = self.project.tasks[row] if 0 <= row < len(self.project.tasks) else None
        if task is None:
            self._append_log("warn", "请先选择一个任务")
            return
        self._save_silent()
        self.step_running = True
        self.step_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.statusBar().showMessage("单步执行中")
        thread = threading.Thread(target=self._run_step_in_background, args=(task,), name="GameBotStep", daemon=True)
        thread.start()

    def _run_step_in_background(self, task: Task) -> None:
        try:
            self.step_scheduler = Scheduler(self.project, self.project_path.parent, self.bridge.received.emit)
            start_index = self.step_positions.get(task.id, 0)
            result = self.step_scheduler.run_rule_once(task, start_index)
            self.step_positions[task.id] = 0 if result.finished else result.next_rule_index
        finally:
            self.controls.step_finished.emit()

    def _on_step_finished(self) -> None:
        self.step_running = False
        self.step_button.setEnabled(True)
        self.run_button.setEnabled(True)
        self.statusBar().showMessage("单步完成")

    def _toggle_pause(self) -> None:
        if self.scheduler:
            paused = self.scheduler.toggle_pause()
            self.statusBar().showMessage("已暂停" if paused else "运行中")

    def _append_log(self, level: str, text: str) -> None:
        self.log_panel.append(level, text)

    def _save_silent(self) -> None:
        try:
            self.project.save(self.project_path)
        except Exception as exc:
            self._append_log("error", f"保存失败: {exc}")

    def _register_hotkeys(self) -> None:
        try:
            import keyboard

            keyboard.add_hotkey(self.project.hotkeys.get("stop_all", "F9"), self.controls.stop_requested.emit)
            keyboard.add_hotkey(self.project.hotkeys.get("pause_resume", "F8"), self.controls.pause_requested.emit)
            keyboard.add_hotkey(self.project.hotkeys.get("coordinate_picker", "F6"), self.controls.coordinate_requested.emit)
            keyboard.add_hotkey(self.project.hotkeys.get("record_toggle", "F7"), self.controls.record_requested.emit)
            self._append_log("info", "热键已注册：F6 坐标拾取，F7 录制，F8 暂停/恢复，F9 停止")
        except Exception as exc:
            self._append_log("warn", f"热键注册不可用: {exc}")
