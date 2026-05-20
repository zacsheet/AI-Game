from __future__ import annotations

import random
import time

import pyautogui

from gamebot.core.matcher import Match
from gamebot.models import Action
from gamebot.utils.mouse_utils import bezier_path, random_offset


class ActionExecutor:
    def __init__(self) -> None:
        pyautogui.PAUSE = 0

    def execute(self, actions: list[Action], match: Match | None = None) -> list[str]:
        messages: list[str] = []
        for action in actions:
            if action.delay_before_ms:
                time.sleep(action.delay_before_ms / 1000)
            messages.append(self._execute_one(action, match))
            if action.delay_after_ms:
                time.sleep(action.delay_after_ms / 1000)
        return messages

    def _execute_one(self, action: Action, match: Match | None) -> str:
        if action.type == "wait":
            time.sleep(max(0, action.duration_ms) / 1000)
            return f"等待 {action.duration_ms}ms"
        if action.type == "key":
            pyautogui.press(action.key)
            return f"按键 {action.key}"

        point = self._target_point(action, match)
        if point is None:
            return "无可用坐标，已跳过动作"

        x, y = point
        self._validate_screen_point(x, y)
        if action.type == "move":
            pyautogui.moveTo(x=x, y=y, duration=max(0, action.duration_ms) / 1000)
            return f"移动到 ({x}, {y})"
        if action.type == "click":
            pyautogui.click(x=x, y=y, button=action.button or "left")
            return f"点击 ({x}, {y})"
        if action.type == "double_click":
            pyautogui.doubleClick(x=x, y=y, button=action.button or "left")
            return f"双击 ({x}, {y})"
        if action.type == "right_click":
            pyautogui.click(x=x, y=y, button="right")
            return f"右键 ({x}, {y})"
        if action.type == "drag":
            self._drag((x, y), (action.to_x, action.to_y), action.duration_ms)
            return f"拖拽 ({x}, {y}) -> ({action.to_x}, {action.to_y})"
        return f"未知动作 {action.type}"

    def _target_point(self, action: Action, match: Match | None) -> tuple[int, int] | None:
        if action.use_match:
            if match is None:
                return None
            return random_offset(match.center, action.offset_random)
        return action.x, action.y

    def _drag(self, start: tuple[int, int], end: tuple[int, int], duration_ms: int) -> None:
        self._validate_screen_point(*end)
        points = bezier_path(start, end)
        pyautogui.moveTo(*points[0])
        pyautogui.mouseDown()
        delay = max(0.002, duration_ms / 1000 / max(1, len(points)))
        for point in points[1:]:
            pyautogui.moveTo(*point, duration=delay * random.uniform(0.75, 1.25))
        pyautogui.mouseUp()

    @staticmethod
    def _validate_screen_point(x: int, y: int) -> None:
        width, height = pyautogui.size()
        if x < 0 or y < 0 or x >= width or y >= height:
            raise ValueError(f"坐标越界: ({x}, {y}) 不在屏幕范围 {width}x{height} 内")
