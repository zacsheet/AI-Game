from __future__ import annotations

import time

from PyQt6.QtCore import QObject, pyqtSignal

from gamebot.models import Action


class InputRecorder(QObject):
    action_recorded = pyqtSignal(object)
    status_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.record_moves = False
        self._mouse_listener = None
        self._keyboard_listener = None
        self._last_move = 0.0
        self._stopping = False

    @property
    def recording(self) -> bool:
        return self._mouse_listener is not None or self._keyboard_listener is not None

    def start(self, record_moves: bool = False) -> None:
        if self.recording:
            return
        self._stopping = False
        try:
            from pynput import keyboard, mouse
        except Exception as exc:
            self.status_changed.emit(f"录制不可用: {exc}")
            return

        self.record_moves = record_moves
        self._mouse_listener = mouse.Listener(on_click=self._on_click, on_move=self._on_move)
        self._keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self._mouse_listener.start()
        self._keyboard_listener.start()
        self.status_changed.emit("正在录制操作")

    def stop(self) -> None:
        if self._stopping:
            return
        self._stopping = True
        mouse_listener = self._mouse_listener
        keyboard_listener = self._keyboard_listener
        self._mouse_listener = None
        self._keyboard_listener = None
        if mouse_listener:
            mouse_listener.stop()
        if keyboard_listener:
            keyboard_listener.stop()
        self._stopping = False
        self.status_changed.emit("录制已停止")

    def toggle(self, record_moves: bool = False) -> bool:
        if self.recording:
            self.stop()
            return False
        self.start(record_moves)
        return self.recording

    def _on_click(self, x: int, y: int, button, pressed: bool) -> None:
        if self._stopping or pressed:
            return
        button_name = getattr(button, "name", "left")
        action_type = "right_click" if button_name == "right" else "click"
        self.action_recorded.emit(Action(type=action_type, use_match=False, x=int(x), y=int(y), button=button_name))

    def _on_move(self, x: int, y: int) -> None:
        if self._stopping or not self.record_moves:
            return
        now = time.monotonic()
        if now - self._last_move < 0.12:
            return
        self._last_move = now
        self.action_recorded.emit(Action(type="move", use_match=False, x=int(x), y=int(y), duration_ms=30))

    def _on_press(self, key) -> None:
        if self._stopping:
            return
        name = getattr(key, "char", None) or getattr(key, "name", None) or str(key).replace("Key.", "")
        if name:
            self.action_recorded.emit(Action(type="key", key=str(name)))
