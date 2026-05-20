from __future__ import annotations

import math
import random


def random_offset(point: tuple[int, int], radius: int) -> tuple[int, int]:
    if radius <= 0:
        return point
    return (point[0] + random.randint(-radius, radius), point[1] + random.randint(-radius, radius))


def bezier_path(start: tuple[int, int], end: tuple[int, int], steps: int = 24) -> list[tuple[int, int]]:
    sx, sy = start
    ex, ey = end
    distance = max(1.0, math.dist(start, end))
    bend = min(120.0, max(20.0, distance * 0.2))
    c1 = (sx + (ex - sx) * 0.35 + random.uniform(-bend, bend), sy + random.uniform(-bend, bend))
    c2 = (sx + (ex - sx) * 0.65 + random.uniform(-bend, bend), ey + random.uniform(-bend, bend))
    points: list[tuple[int, int]] = []
    for index in range(steps + 1):
        t = index / steps
        x = (1 - t) ** 3 * sx + 3 * (1 - t) ** 2 * t * c1[0] + 3 * (1 - t) * t**2 * c2[0] + t**3 * ex
        y = (1 - t) ** 3 * sy + 3 * (1 - t) ** 2 * t * c1[1] + 3 * (1 - t) * t**2 * c2[1] + t**3 * ey
        points.append((int(x), int(y)))
    return points
