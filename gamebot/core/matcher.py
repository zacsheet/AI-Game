from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from gamebot.core.window import capture_screen
from gamebot.models import Rect, Rule


@dataclass(frozen=True)
class Match:
    x: int
    y: int
    w: int
    h: int
    score: float

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)


class TemplateMatcher:
    def __init__(self, image_root: str | Path = ".") -> None:
        self.image_root = Path(image_root)
        self.last_score: float | None = None
        self.last_location: tuple[int, int] | None = None

    def match_rule(self, rule: Rule, task_roi: Rect | None = None) -> list[Match]:
        self.last_score = None
        self.last_location = None
        if not rule.image:
            return []
        image_path = Path(rule.image)
        if not image_path.is_absolute():
            image_path = self.image_root / image_path
        template = self._read_image(image_path)
        if template is None:
            raise FileNotFoundError(f"图片不存在或无法读取: {image_path}")

        roi = rule.roi_override or task_roi
        frame, origin = capture_screen(roi)
        if frame.shape[0] < template.shape[0] or frame.shape[1] < template.shape[1]:
            return []

        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        h, w = template.shape[:2]
        _, score, _, loc = cv2.minMaxLoc(result)
        self.last_score = float(score)
        self.last_location = (loc[0] + origin[0], loc[1] + origin[1])
        if rule.multi:
            return self._multi_matches(result, w, h, rule.threshold, origin)

        if score < rule.threshold:
            return []
        return [Match(x=loc[0] + origin[0], y=loc[1] + origin[1], w=w, h=h, score=float(score))]

    def _multi_matches(
        self,
        result: np.ndarray,
        width: int,
        height: int,
        threshold: float,
        origin: tuple[int, int],
    ) -> list[Match]:
        points = np.where(result >= threshold)
        candidates = [
            Match(x=int(x) + origin[0], y=int(y) + origin[1], w=width, h=height, score=float(result[y, x]))
            for y, x in zip(*points)
        ]
        candidates.sort(key=lambda item: item.score, reverse=True)
        selected: list[Match] = []
        for match in candidates:
            if all(not self._overlaps(match, existing) for existing in selected):
                selected.append(match)
        return selected

    @staticmethod
    def _overlaps(a: Match, b: Match) -> bool:
        return not (a.x + a.w < b.x or b.x + b.w < a.x or a.y + a.h < b.y or b.y + b.h < a.y)

    @staticmethod
    def _read_image(path: Path) -> np.ndarray | None:
        if not path.exists():
            return None
        data = np.fromfile(str(path), dtype=np.uint8)
        if data.size == 0:
            return None
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
