from __future__ import annotations

from dataclasses import dataclass

import mss
import numpy as np

from gamebot.models import Rect


@dataclass(frozen=True)
class WindowState:
    title: str
    available: bool
    minimized: bool = False
    reason: str = ""


def find_window_state(title: str) -> WindowState:
    if not title:
        return WindowState(title="", available=True)
    try:
        import win32gui

        matches: list[int] = []

        def callback(hwnd: int, _: object) -> None:
            if win32gui.IsWindowVisible(hwnd) and title.lower() in win32gui.GetWindowText(hwnd).lower():
                matches.append(hwnd)

        win32gui.EnumWindows(callback, None)
        if not matches:
            return WindowState(title=title, available=False, reason="未找到窗口")
        minimized = bool(win32gui.IsIconic(matches[0]))
        return WindowState(title=title, available=not minimized, minimized=minimized, reason="窗口已最小化" if minimized else "")
    except Exception as exc:
        return WindowState(title=title, available=True, reason=f"窗口检查不可用: {exc}")


def capture_screen(roi: Rect | None = None) -> tuple[np.ndarray, tuple[int, int]]:
    with mss.mss() as screen:
        if roi and roi.is_valid():
            monitor = {"left": roi.x, "top": roi.y, "width": roi.w, "height": roi.h}
            origin = (roi.x, roi.y)
        else:
            monitor = screen.monitors[0]
            origin = (int(monitor["left"]), int(monitor["top"]))
        shot = screen.grab(monitor)
    frame = np.array(shot)
    return frame[:, :, :3], origin
