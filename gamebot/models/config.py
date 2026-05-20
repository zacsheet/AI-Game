from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4
import json


ActionType = Literal["click", "double_click", "right_click", "wait", "key", "drag"]
ExecuteMode = Literal["sequence", "parallel", "priority"]
NotFoundPolicy = Literal["continue", "skip", "skip_task"]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


@dataclass
class Rect:
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Rect | None":
        if not data:
            return None
        return cls(
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            w=int(data.get("w", 0)),
            h=int(data.get("h", 0)),
        )

    def is_valid(self) -> bool:
        return self.w > 0 and self.h > 0


@dataclass
class Action:
    type: ActionType = "click"
    button: str = "left"
    offset_random: int = 0
    delay_before_ms: int = 0
    delay_after_ms: int = 0
    duration_ms: int = 0
    key: str = ""
    to_x: int = 0
    to_y: int = 0
    curve: str = "bezier"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Action":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        values = {key: value for key, value in data.items() if key in allowed}
        return cls(**values)


@dataclass
class Rule:
    id: str = field(default_factory=lambda: new_id("rule"))
    name: str = "新规则"
    enabled: bool = True
    image: str = ""
    threshold: float = 0.88
    multi: bool = False
    roi_override: Rect | None = None
    actions: list[Action] = field(default_factory=lambda: [Action()])
    not_found: NotFoundPolicy = "continue"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rule":
        return cls(
            id=str(data.get("id") or new_id("rule")),
            name=str(data.get("name") or "新规则"),
            enabled=bool(data.get("enabled", True)),
            image=str(data.get("image") or ""),
            threshold=float(data.get("threshold", 0.88)),
            multi=bool(data.get("multi", False)),
            roi_override=Rect.from_dict(data.get("roi_override")),
            actions=[Action.from_dict(item) for item in data.get("actions", [])] or [Action()],
            not_found=data.get("not_found", "continue"),
        )


@dataclass
class Task:
    id: str = field(default_factory=lambda: new_id("task"))
    name: str = "新任务"
    enabled: bool = True
    interval_ms: int = 3000
    window_title: str = ""
    roi: Rect | None = None
    execute_mode: ExecuteMode = "sequence"
    on_no_match: str = "skip"
    max_failures: int = 5
    rules: list[Rule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            id=str(data.get("id") or new_id("task")),
            name=str(data.get("name") or "新任务"),
            enabled=bool(data.get("enabled", True)),
            interval_ms=int(data.get("interval_ms", 3000)),
            window_title=str(data.get("window_title") or ""),
            roi=Rect.from_dict(data.get("roi")),
            execute_mode=data.get("execute_mode", "sequence"),
            on_no_match=str(data.get("on_no_match", "skip")),
            max_failures=int(data.get("max_failures", 5)),
            rules=[Rule.from_dict(item) for item in data.get("rules", [])],
        )


@dataclass
class Project:
    version: str = "1.0"
    name: str = "我的游戏配置"
    hotkeys: dict[str, str] = field(default_factory=lambda: {"stop_all": "F9", "pause_resume": "F8"})
    tasks: list[Task] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        return cls(
            version=str(data.get("version") or "1.0"),
            name=str(data.get("name") or "我的游戏配置"),
            hotkeys=dict(data.get("hotkeys") or {"stop_all": "F9", "pause_resume": "F8"}),
            tasks=[Task.from_dict(item) for item in data.get("tasks", [])],
        )

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        with Path(path).open("r", encoding="utf-8") as file:
            return cls.from_dict(json.load(file))

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as file:
            json.dump(asdict(self), file, ensure_ascii=False, indent=2)
