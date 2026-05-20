from __future__ import annotations

from PyQt6.QtCore import QRectF, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsTextItem, QGraphicsView

from gamebot.models import Task


END_TASK = "__end_task__"


class BlueprintView(QGraphicsView):
    rule_selected = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self._node_by_item: dict[object, str] = {}
        self._task: Task | None = None
        self._selected_rule_id = ""
        self.setMinimumHeight(360)

    def set_task(self, task: Task | None) -> None:
        self._task = task
        self.scene.clear()
        self._node_by_item.clear()
        if task is None:
            self._selected_rule_id = ""
            return

        positions: dict[str, tuple[float, float]] = {}
        width = 210
        height = 92
        x_gap = 70
        y = 30

        for index, rule in enumerate(task.rules):
            x = 30 + index * (width + x_gap)
            positions[rule.id] = (x, y)
            self._draw_node(rule.id, rule.name, f"{rule.threshold:.2f} | {len(rule.actions)} 个动作", x, y, width, height, rule.enabled)

        if task.rules:
            end_x = 30 + len(task.rules) * (width + x_gap)
            positions[END_TASK] = (end_x, y)
            self._draw_node(END_TASK, "结束任务", "跳出本轮任务", end_x, y, width, height, True, selectable=False)

        for index, rule in enumerate(task.rules):
            start = positions.get(rule.id)
            if start is None:
                continue
            default_next = task.rules[index + 1].id if index + 1 < len(task.rules) else END_TASK
            found_target = rule.next_on_found or default_next
            self._draw_link(start, positions.get(found_target), "成立", QColor("#15803d"), width, height, 0)
            self._draw_link(start, positions.get(rule.next_on_not_found), "不成立", QColor("#b45309"), width, height, 26)

        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-30, -30, 60, 60))

    def set_selected_rule(self, rule_id: str) -> None:
        if self._selected_rule_id == rule_id:
            return
        self._selected_rule_id = rule_id
        self.set_task(self._task)

    def mousePressEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        while item is not None and item.data(0) is None:
            item = item.parentItem()
        if item is not None and item.data(0):
            rule_id = str(item.data(0))
            self.set_selected_rule(rule_id)
            self.rule_selected.emit(rule_id)
        super().mousePressEvent(event)

    def _draw_node(
        self,
        node_id: str,
        title_text: str,
        subtitle_text: str,
        x: float,
        y: float,
        width: float,
        height: float,
        enabled: bool,
        selectable: bool = True,
    ) -> None:
        selected = selectable and node_id == self._selected_rule_id
        color = QColor("#dbeafe") if enabled else QColor("#f1f1f1")
        if node_id == END_TASK:
            color = QColor("#f8fafc")
        if selected:
            color = QColor("#bfdbfe")
        node_path = QPainterPath()
        node_path.addRoundedRect(QRectF(x, y, width, height), 8, 8)
        if selected:
            halo_path = QPainterPath()
            halo_path.addRoundedRect(QRectF(x - 5, y - 5, width + 10, height + 10), 11, 11)
            self.scene.addPath(halo_path, QPen(QColor("#93c5fd"), 2), QBrush(QColor(0, 0, 0, 0)))
        pen = QPen(QColor("#2563eb") if selected else QColor("#6b7280"), 3 if selected else 1)
        node = self.scene.addPath(node_path, pen, QBrush(color))
        if selectable:
            node.setData(0, node_id)
            self._node_by_item[node] = node_id

        title = QGraphicsTextItem(title_text)
        title.setDefaultTextColor(QColor("#111827"))
        title.setPos(x + 12, y + 10)
        title.setTextWidth(width - 24)
        self.scene.addItem(title)

        subtitle = QGraphicsTextItem(subtitle_text)
        subtitle.setDefaultTextColor(QColor("#4b5563"))
        subtitle.setPos(x + 12, y + 48)
        subtitle.setTextWidth(width - 24)
        self.scene.addItem(subtitle)

    def _draw_link(
        self,
        start: tuple[float, float],
        end: tuple[float, float] | None,
        label: str,
        color: QColor,
        width: float,
        height: float,
        offset: float,
    ) -> None:
        if end is None:
            return
        x1, y1 = start[0] + width, start[1] + height / 2 + offset
        x2, y2 = end[0], end[1] + height / 2 + offset
        self.scene.addLine(x1, y1, x2, y2, QPen(color, 2))
        text = QGraphicsTextItem(label)
        text.setDefaultTextColor(color)
        text.setPos((x1 + x2) / 2 - 16, (y1 + y2) / 2 - 24)
        self.scene.addItem(text)
