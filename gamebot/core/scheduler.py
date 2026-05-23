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
from gamebot.models import Project, Rule, Task


LogCallback = Callable[[str, str], None]
END_TASK = "__end_task__"


@dataclass
class TaskRuntime:
    running: bool = False
    next_run: float = 0.0
    fail_count: int = 0
    executions: int = 0
    completed: bool = False


@dataclass
class StepResult:
    matched: bool
    next_rule_index: int
    finished: bool = False


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
        self._active_task_index = 0

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
        self._active_task_index = self._find_next_task_index(0)
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

    def run_rule_once(self, task: Task, rule_index: int = 0) -> StepResult:
        state = find_window_state(task.window_title)
        if not state.available:
            self._log("warn", f"Task[{task.name}] {state.reason or '窗口不可用'}，单步执行已暂停")
            return StepResult(matched=False, next_rule_index=rule_index, finished=False)
        if not task.rules:
            self._log("warn", f"Task[{task.name}] 没有可执行规则")
            return StepResult(matched=False, next_rule_index=0, finished=True)
        if rule_index < 0 or rule_index >= len(task.rules):
            rule_index = 0

        rule = task.rules[rule_index]
        self._log("info", f"单步执行 Task[{task.name}] Rule[{rule.name}]")
        if not rule.enabled:
            next_index = rule_index + 1
            finished = next_index >= len(task.rules)
            self._log("skip", f"Task[{task.name}] Rule[{rule.name}] 已禁用")
            return StepResult(matched=False, next_rule_index=0 if finished else next_index, finished=finished)

        rule_positions = self._rule_positions(task)
        try:
            matches = self.matcher.match_rule(rule, task.roi)
        except Exception as exc:
            self._log("error", f"Task[{task.name}] Rule[{rule.name}] {exc}")
            next_index = rule_index + 1
            finished = next_index >= len(task.rules)
            return StepResult(matched=False, next_rule_index=0 if finished else next_index, finished=finished)

        if not matches:
            self._log_not_found(task, rule)
            if rule.next_on_not_found == END_TASK or rule.not_found == "skip_task":
                self._log("info", f"Task[{task.name}] 不成立分支结束本轮任务")
                return StepResult(matched=False, next_rule_index=0, finished=True)
            jump_to = rule_positions.get(rule.next_on_not_found)
            if jump_to is not None:
                self._log_next_step(task, jump_to)
                return StepResult(matched=False, next_rule_index=jump_to)
            next_index = rule_index + 1
            finished = next_index >= len(task.rules)
            self._log_next_step(task, 0 if finished else next_index, finished)
            return StepResult(matched=False, next_rule_index=0 if finished else next_index, finished=finished)

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

        if rule.next_on_found == END_TASK:
            self._log("info", f"Task[{task.name}] 成立分支结束本轮任务")
            return StepResult(matched=True, next_rule_index=0, finished=True)
        jump_to = rule_positions.get(rule.next_on_found)
        if jump_to is not None:
            self._log_next_step(task, jump_to)
            return StepResult(matched=True, next_rule_index=jump_to)
        next_index = rule_index + 1
        finished = next_index >= len(task.rules)
        self._log_next_step(task, 0 if finished else next_index, finished)
        return StepResult(matched=True, next_rule_index=0 if finished else next_index, finished=finished)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.2)
                continue

            task = self._active_task()
            if task is None:
                time.sleep(0.2)
                continue

            runtime = self._runtime.setdefault(task.id, TaskRuntime(next_run=time.monotonic()))
            now = time.monotonic()
            if now >= runtime.next_run:
                self._run_due_task(task, runtime)
            time.sleep(0.05)
        self._log("stop", "调度器已停止")

    def _active_task(self) -> Task | None:
        if self._active_task_index < 0 or self._active_task_index >= len(self.project.tasks):
            return None
        task = self.project.tasks[self._active_task_index]
        runtime = self._runtime.setdefault(task.id, TaskRuntime(next_run=time.monotonic()))
        if task.enabled and not runtime.completed:
            return task
        self._active_task_index = self._find_next_task_index(self._active_task_index + 1)
        if self._active_task_index < 0:
            self._log("stop", "任务队列已完成")
            self._stop_event.set()
            return None
        return self.project.tasks[self._active_task_index]

    def _find_next_task_index(self, start: int) -> int:
        for index in range(max(0, start), len(self.project.tasks)):
            task = self.project.tasks[index]
            runtime = self._runtime.setdefault(task.id, TaskRuntime(next_run=time.monotonic()))
            if task.enabled and not runtime.completed:
                return index
        return -1

    def _advance_to_next_task(self) -> None:
        next_index = self._find_next_task_index(self._active_task_index + 1)
        if next_index < 0:
            self._log("stop", "任务队列已完成")
            self._stop_event.set()
            return
        self._active_task_index = next_index
        task = self.project.tasks[next_index]
        runtime = self._runtime.setdefault(task.id, TaskRuntime())
        runtime.next_run = time.monotonic()
        self._log("info", f"切换到下一个任务: {task.name}")

    def _run_due_task(self, task: Task, runtime: TaskRuntime) -> None:
        if runtime.running:
            self._log("warn", f"Task[{task.name}] 上次执行未完成，本次触发已跳过")
            return
        runtime.running = True
        try:
            matched = self._run_task(task)
            runtime.executions += 1
            if task.max_executions > 0 and runtime.executions >= task.max_executions:
                runtime.completed = True
                self._log("stop", f"Task[{task.name}] 已执行 {runtime.executions}/{task.max_executions} 次，进入下一个任务")
                self._advance_to_next_task()
                return
            runtime.fail_count = 0 if matched else runtime.fail_count + 1
            if runtime.fail_count >= task.max_failures:
                task.enabled = False
                self._log("stop", f"Task[{task.name}] 连续失败 {runtime.fail_count} 次，已自动暂停并进入下一个任务")
                self._advance_to_next_task()
        finally:
            runtime.running = False
            runtime.next_run = time.monotonic() + task.interval_ms / 1000

    def _run_task(self, task: Task) -> bool:
        state = find_window_state(task.window_title)
        if not state.available:
            self._log("warn", f"Task[{task.name}] {state.reason or '窗口不可用'}，暂停本次执行")
            return False

        any_matched = False
        rule_index = 0
        rule_positions = self._rule_positions(task)
        steps = 0
        max_steps = max(1, len(task.rules) * 3)

        while rule_index < len(task.rules) and steps < max_steps:
            steps += 1
            rule = task.rules[rule_index]
            if not rule.enabled:
                rule_index += 1
                continue

            try:
                matches = self.matcher.match_rule(rule, task.roi)
            except Exception as exc:
                self._log("error", f"Task[{task.name}] Rule[{rule.name}] {exc}")
                rule_index += 1
                continue

            if not matches:
                self._log_not_found(task, rule)
                if rule.next_on_not_found == END_TASK:
                    self._log("info", f"Task[{task.name}] 不成立分支结束本轮任务")
                    return any_matched
                jump_to = rule_positions.get(rule.next_on_not_found)
                if jump_to is not None:
                    rule_index = jump_to
                    continue
                if rule.not_found == "skip_task":
                    return any_matched
                rule_index += 1
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

            if rule.next_on_found == END_TASK:
                self._log("info", f"Task[{task.name}] 成立分支结束本轮任务")
                return any_matched
            jump_to = rule_positions.get(rule.next_on_found)
            if jump_to is not None:
                rule_index = jump_to
                continue
            rule_index += 1

        if steps >= max_steps:
            self._log("warn", f"Task[{task.name}] 分支跳转次数过多，已停止本轮任务")
        return any_matched

    @staticmethod
    def _rule_positions(task: Task) -> dict[str, int]:
        return {rule.id: index for index, rule in enumerate(task.rules)}

    def _log_not_found(self, task: Task, rule: Rule) -> None:
        if self.matcher.last_score is None:
            detail = "无可用相似度"
        else:
            location = self.matcher.last_location
            location_text = "未知位置" if location is None else f"位置 ({location[0]}, {location[1]})"
            detail = f"最高相似度 {self.matcher.last_score:.3f}，{location_text}，阈值 {rule.threshold:.3f}"
        target = rule.image or rule.name
        self._log("skip", f"Task[{task.name}] 未找到 {target}（{detail}）-> {rule.not_found}")

    def _log_next_step(self, task: Task, rule_index: int, finished: bool = False) -> None:
        if finished or rule_index >= len(task.rules):
            self._log("info", f"Task[{task.name}] 本轮规则结束，下次单步从第一条规则开始")
            return
        rule = task.rules[rule_index]
        self._log("info", f"Task[{task.name}] 下一步将执行 Rule[{rule.name}]")

    def _log(self, level: str, message: str) -> None:
        stamped = f"{datetime.now().strftime('%H:%M:%S')}  {message}"
        self.on_log(level, stamped)
