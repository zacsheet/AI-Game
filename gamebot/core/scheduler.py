from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import threading
import time
from typing import Callable

from gamebot.core.executor import ActionExecutor
from gamebot.core.matcher import TemplateMatcher
from gamebot.core.window import find_window_state
from gamebot.models import Project, Task


LogCallback = Callable[[str, str], None]


@dataclass
class TaskRuntime:
    running: bool = False
    next_run: float = 0.0
    fail_count: int = 0
    executions: int = 0


class Scheduler:
    def __init__(self, project: Project, image_root: str | Path, on_log: LogCallback) -> None:
        self.project = project
        self.matcher = TemplateMatcher(image_root)
        self.executor = ActionExecutor()
        self.on_log = on_log
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._runtime: dict[str, TaskRuntime] = {}

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._pause_event.clear()
        now = time.monotonic()
        self._runtime = {task.id: TaskRuntime(next_run=now + task.interval_ms / 1000) for task in self.project.tasks}
        self._thread = threading.Thread(target=self._loop, name="GameBotScheduler", daemon=True)
        self._thread.start()
        self._log("info", "调度器已启动")

    def stop(self) -> None:
        self._stop_event.set()
        self._log("stop", "正在停止所有任务")

    def toggle_pause(self) -> bool:
        if self._pause_event.is_set():
            self._pause_event.clear()
            self._log("info", "已恢复运行")
            return False
        self._pause_event.set()
        self._log("warn", "已暂停运行")
        return True

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.2)
                continue
            for task in list(self.project.tasks):
                if self._stop_event.is_set() or self._pause_event.is_set():
                    break
                now = time.monotonic()
                runtime = self._runtime.setdefault(task.id, TaskRuntime(next_run=now))
                if not task.enabled:
                    runtime.next_run = now + task.interval_ms / 1000
                    continue
                if now >= runtime.next_run:
                    self._run_due_task(task, runtime)
            time.sleep(0.05)
        self._log("stop", "调度器已停止")

    def _run_due_task(self, task: Task, runtime: TaskRuntime) -> None:
        if runtime.running:
            self._log("warn", f"Task[{task.name}] 上次执行未完成，本次触发已跳过")
            return
        runtime.running = True
        try:
            matched = self._run_task(task)
            runtime.executions += 1
            runtime.fail_count = 0 if matched else runtime.fail_count + 1
            if runtime.fail_count >= task.max_failures:
                task.enabled = False
                self._log("stop", f"Task[{task.name}] 连续失败 {runtime.fail_count} 次，已自动暂停")
        finally:
            runtime.running = False
            runtime.next_run = time.monotonic() + task.interval_ms / 1000

    def _run_task(self, task: Task) -> bool:
        state = find_window_state(task.window_title)
        if not state.available:
            self._log("warn", f"Task[{task.name}] {state.reason or '窗口不可用'}，暂停本次执行")
            return False

        any_matched = False
        for rule in task.rules:
            if not rule.enabled:
                continue
            try:
                matches = self.matcher.match_rule(rule, task.roi)
            except Exception as exc:
                self._log("error", f"Task[{task.name}] Rule[{rule.name}] {exc}")
                continue

            if not matches:
                self._log("skip", f"Task[{task.name}] 未找到 {rule.image} -> {rule.not_found}")
                if rule.not_found == "skip_task":
                    return any_matched
                continue

            any_matched = True
            for match in matches:
                self._log("ok", f"Task[{task.name}] 找到 {rule.image} ({match.score:.2f})")
                try:
                    for message in self.executor.execute(rule.actions, match):
                        self._log("ok", f"Task[{task.name}] {message}")
                except Exception as exc:
                    self._log("error", f"Task[{task.name}] 执行动作失败: {exc}")
                if not rule.multi:
                    break
                time.sleep(0.1)
        return any_matched

    def _log(self, level: str, message: str) -> None:
        stamped = f"{datetime.now().strftime('%H:%M:%S')}  {message}"
        self.on_log(level, stamped)
