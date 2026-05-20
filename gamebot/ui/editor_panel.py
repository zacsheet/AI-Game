from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

from gamebot.models import Action, Rect, Rule, Task


class EditorPanel(QWidget):
    changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.task: Task | None = None
        self.image_root = Path(".")
        self.loading = False

        self.name = QLineEdit()
        self.enabled = QCheckBox("启用任务")
        self.interval = QSpinBox()
        self.interval.setRange(100, 24 * 60 * 60 * 1000)
        self.interval.setSingleStep(100)
        self.window_title = QLineEdit()
        self.execute_mode = QComboBox()
        self.execute_mode.addItems(["sequence", "parallel", "priority"])
        self.on_no_match = QComboBox()
        self.on_no_match.addItems(["skip", "continue"])
        self.max_failures = QSpinBox()
        self.max_failures.setRange(1, 100)

        self.roi_label = QLabel("全屏")
        self.set_roi_button = QPushButton("设置 ROI")
        self.clear_roi_button = QPushButton("清除 ROI")

        self.rules = QListWidget()
        self.add_rule_button = QPushButton("+ 添加图片规则")
        self.remove_rule_button = QPushButton("删除规则")
        self.rule_name = QLineEdit()
        self.rule_enabled = QCheckBox("启用规则")
        self.rule_image = QLineEdit()
        self.pick_image_button = QPushButton("选择图片")
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.1, 1.0)
        self.threshold.setSingleStep(0.01)
        self.threshold.setDecimals(2)
        self.multi = QCheckBox("多实例匹配")
        self.not_found = QComboBox()
        self.not_found.addItems(["continue", "skip", "skip_task"])
        self.action_type = QComboBox()
        self.action_type.addItems(["click", "double_click", "right_click", "wait", "key", "drag"])
        self.action_button = QComboBox()
        self.action_button.addItems(["left", "right", "middle"])
        self.action_key = QLineEdit()
        self.offset = QSpinBox()
        self.offset.setRange(0, 200)
        self.duration = QSpinBox()
        self.duration.setRange(0, 600000)
        self.to_x = QSpinBox()
        self.to_x.setRange(0, 20000)
        self.to_y = QSpinBox()
        self.to_y.setRange(0, 20000)
        self.delay_after = QSpinBox()
        self.delay_after.setRange(0, 600000)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_task_box())
        layout.addWidget(self._build_rule_box(), 1)

        self._connect()

    def _build_task_box(self) -> QGroupBox:
        box = QGroupBox("基础设置")
        form = QFormLayout(box)
        form.addRow("任务名", self.name)
        form.addRow("", self.enabled)
        form.addRow("间隔 ms", self.interval)
        form.addRow("窗口标题", self.window_title)
        form.addRow("执行策略", self.execute_mode)
        form.addRow("失败策略", self.on_no_match)
        form.addRow("连续失败暂停", self.max_failures)
        roi_layout = QHBoxLayout()
        roi_layout.addWidget(self.roi_label, 1)
        roi_layout.addWidget(self.set_roi_button)
        roi_layout.addWidget(self.clear_roi_button)
        form.addRow("查找区域", roi_layout)
        return box

    def _build_rule_box(self) -> QGroupBox:
        box = QGroupBox("图片规则")
        outer = QHBoxLayout(box)
        left = QVBoxLayout()
        left.addWidget(self.rules, 1)
        left.addWidget(self.add_rule_button)
        left.addWidget(self.remove_rule_button)

        form = QFormLayout()
        image_row = QHBoxLayout()
        image_row.addWidget(self.rule_image, 1)
        image_row.addWidget(self.pick_image_button)
        form.addRow("规则名", self.rule_name)
        form.addRow("", self.rule_enabled)
        form.addRow("图片", image_row)
        form.addRow("阈值", self.threshold)
        form.addRow("", self.multi)
        form.addRow("未找到", self.not_found)
        form.addRow("动作", self.action_type)
        form.addRow("鼠标按钮", self.action_button)
        form.addRow("按键", self.action_key)
        form.addRow("随机偏移 px", self.offset)
        form.addRow("等待/拖拽时长 ms", self.duration)
        form.addRow("拖拽目标 X", self.to_x)
        form.addRow("拖拽目标 Y", self.to_y)
        form.addRow("动作后等待 ms", self.delay_after)

        outer.addLayout(left, 1)
        outer.addLayout(form, 2)
        return box

    def _connect(self) -> None:
        for widget in [
            self.name,
            self.window_title,
            self.rule_name,
            self.rule_image,
            self.action_key,
        ]:
            widget.editingFinished.connect(self._write_back)
        for widget in [self.enabled, self.rule_enabled, self.multi]:
            widget.toggled.connect(self._write_back)
        for widget in [self.interval, self.max_failures, self.threshold, self.offset, self.duration, self.to_x, self.to_y, self.delay_after]:
            widget.valueChanged.connect(self._write_back)
        for widget in [self.execute_mode, self.on_no_match, self.not_found, self.action_type, self.action_button]:
            widget.currentTextChanged.connect(self._write_back)
        self.rules.currentRowChanged.connect(self._show_rule)
        self.add_rule_button.clicked.connect(self._add_rule)
        self.remove_rule_button.clicked.connect(self._remove_rule)
        self.pick_image_button.clicked.connect(self._pick_image)
        self.set_roi_button.clicked.connect(self._set_roi)
        self.clear_roi_button.clicked.connect(self._clear_roi)

    def set_task(self, task: Task | None, image_root: Path) -> None:
        self.loading = True
        self.task = task
        self.image_root = image_root
        self.setEnabled(task is not None)
        if task is None:
            self.loading = False
            return
        self.name.setText(task.name)
        self.enabled.setChecked(task.enabled)
        self.interval.setValue(task.interval_ms)
        self.window_title.setText(task.window_title)
        self.execute_mode.setCurrentText(task.execute_mode)
        self.on_no_match.setCurrentText(task.on_no_match)
        self.max_failures.setValue(task.max_failures)
        self._update_roi_label()
        self._refresh_rules()
        self.loading = False

    def _write_back(self) -> None:
        if self.loading or self.task is None:
            return
        self.task.name = self.name.text().strip() or "新任务"
        self.task.enabled = self.enabled.isChecked()
        self.task.interval_ms = self.interval.value()
        self.task.window_title = self.window_title.text().strip()
        self.task.execute_mode = self.execute_mode.currentText()
        self.task.on_no_match = self.on_no_match.currentText()
        self.task.max_failures = self.max_failures.value()

        rule = self._current_rule()
        if rule:
            rule.name = self.rule_name.text().strip() or "新规则"
            rule.enabled = self.rule_enabled.isChecked()
            rule.image = self.rule_image.text().strip()
            rule.threshold = self.threshold.value()
            rule.multi = self.multi.isChecked()
            rule.not_found = self.not_found.currentText()
            if not rule.actions:
                rule.actions.append(Action())
            action = rule.actions[0]
            action.type = self.action_type.currentText()
            action.button = self.action_button.currentText()
            action.key = self.action_key.text().strip()
            action.offset_random = self.offset.value()
            action.duration_ms = self.duration.value()
            action.to_x = self.to_x.value()
            action.to_y = self.to_y.value()
            action.delay_after_ms = self.delay_after.value()
        self.changed.emit()
        self._refresh_rule_labels()

    def _refresh_rules(self) -> None:
        self.rules.clear()
        if not self.task:
            return
        for rule in self.task.rules:
            self.rules.addItem(QListWidgetItem(f"{rule.name}\n{Path(rule.image).name or '未选择图片'} · {rule.threshold:.2f}"))
        if self.task.rules:
            self.rules.setCurrentRow(0)
        else:
            self._show_rule(-1)

    def _refresh_rule_labels(self) -> None:
        if not self.task:
            return
        for index, rule in enumerate(self.task.rules):
            item = self.rules.item(index)
            if item:
                item.setText(f"{rule.name}\n{Path(rule.image).name or '未选择图片'} · {rule.threshold:.2f}")

    def _show_rule(self, row: int) -> None:
        rule = self._current_rule()
        self.loading = True
        enabled = rule is not None
        for widget in [
            self.rule_name,
            self.rule_enabled,
            self.rule_image,
            self.pick_image_button,
            self.threshold,
            self.multi,
            self.not_found,
            self.action_type,
            self.action_button,
            self.action_key,
            self.offset,
            self.duration,
            self.to_x,
            self.to_y,
            self.delay_after,
            self.remove_rule_button,
        ]:
            widget.setEnabled(enabled)
        if not rule:
            self.rule_name.clear()
            self.rule_image.clear()
            self.loading = False
            return
        self.rule_name.setText(rule.name)
        self.rule_enabled.setChecked(rule.enabled)
        self.rule_image.setText(rule.image)
        self.threshold.setValue(rule.threshold)
        self.multi.setChecked(rule.multi)
        self.not_found.setCurrentText(rule.not_found)
        action = rule.actions[0] if rule.actions else Action()
        self.action_type.setCurrentText(action.type)
        self.action_button.setCurrentText(action.button)
        self.action_key.setText(action.key)
        self.offset.setValue(action.offset_random)
        self.duration.setValue(action.duration_ms)
        self.to_x.setValue(action.to_x)
        self.to_y.setValue(action.to_y)
        self.delay_after.setValue(action.delay_after_ms)
        self.loading = False

    def _current_rule(self) -> Rule | None:
        if self.task is None:
            return None
        row = self.rules.currentRow()
        if row < 0 or row >= len(self.task.rules):
            return None
        return self.task.rules[row]

    def _add_rule(self) -> None:
        if not self.task:
            return
        self.task.rules.append(Rule(name=f"规则 {len(self.task.rules) + 1}"))
        self._refresh_rules()
        self.rules.setCurrentRow(len(self.task.rules) - 1)
        self.changed.emit()

    def _remove_rule(self) -> None:
        if not self.task:
            return
        row = self.rules.currentRow()
        if row >= 0:
            self.task.rules.pop(row)
            self._refresh_rules()
            self.changed.emit()

    def _pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择模板图片", str(self.image_root), "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        try:
            text = str(Path(path).resolve().relative_to(self.image_root.resolve()))
        except ValueError:
            text = path
        self.rule_image.setText(text)
        self._write_back()

    def _set_roi(self) -> None:
        if not self.task:
            return
        text, ok = QInputDialog.getText(self, "设置 ROI", "输入 x,y,w,h，例如 0,0,960,540")
        if not ok:
            return
        parts = [part.strip() for part in text.split(",")]
        if len(parts) != 4:
            return
        self.task.roi = Rect(*(int(part) for part in parts))
        self._update_roi_label()
        self.changed.emit()

    def _clear_roi(self) -> None:
        if self.task:
            self.task.roi = None
            self._update_roi_label()
            self.changed.emit()

    def _update_roi_label(self) -> None:
        if not self.task or not self.task.roi:
            self.roi_label.setText("全屏")
            return
        roi = self.task.roi
        self.roi_label.setText(f"{roi.x}, {roi.y}, {roi.w}, {roi.h}")
