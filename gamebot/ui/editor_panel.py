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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gamebot.core.recorder import InputRecorder
from gamebot.models import Action, Rect, Rule, Task
from gamebot.ui.blueprint_view import BlueprintView
from gamebot.ui.coordinate_picker import CoordinatePicker


END_TASK = "__end_task__"


class EditorPanel(QWidget):
    changed = pyqtSignal()
    log_requested = pyqtSignal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.task: Task | None = None
        self.image_root = Path(".")
        self.loading = False
        self.selected_rule_id = ""
        self.recording_rule_id = ""
        self.recorder = InputRecorder()
        self.coordinate_picker = CoordinatePicker(self)

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
        self.max_executions = QSpinBox()
        self.max_executions.setRange(0, 1000000)
        self.max_executions.setSpecialValueText("不限")

        self.roi_label = QLabel("全屏")
        self.set_roi_button = QPushButton("设置 ROI")
        self.clear_roi_button = QPushButton("清除 ROI")

        self.rules = QListWidget()
        self.add_rule_button = QPushButton("+ 添加规则")
        self.remove_rule_button = QPushButton("删除规则")
        self.rule_name = QLineEdit()
        self.rule_enabled = QCheckBox("启用规则")
        self.rule_image = QLineEdit()
        self.pick_image_button = QPushButton("选择图片")
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.1, 1.0)
        self.threshold.setSingleStep(0.01)
        self.threshold.setDecimals(2)
        self.multi = QCheckBox("匹配多个实例")
        self.not_found = QComboBox()
        self.not_found.addItems(["continue", "skip", "skip_task"])
        self.next_on_found = QComboBox()
        self.next_on_not_found = QComboBox()

        self.action_type = QComboBox()
        self.action_type.addItems(["click", "double_click", "right_click", "wait", "key", "drag", "move"])
        self.actions = QListWidget()
        self.actions.setMaximumHeight(110)
        self.add_action_button = QPushButton("+ 动作")
        self.remove_action_button = QPushButton("删除动作")
        self.action_use_match = QCheckBox("使用图片匹配位置")
        self.action_button = QComboBox()
        self.action_button.addItems(["left", "right", "middle"])
        self.action_key = QLineEdit()
        self.action_x = QSpinBox()
        self.action_x.setRange(0, 20000)
        self.action_y = QSpinBox()
        self.action_y.setRange(0, 20000)
        self.pick_coordinate_button = QPushButton("拾取坐标")
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

        self.record_moves = QCheckBox("录制鼠标移动轨迹")
        self.record_button = QPushButton("开始录制 (F7)")
        self.record_status = QLabel("未录制")

        self.blueprint = BlueprintView()
        self.blueprint_rule_name = QLabel("未选择规则")
        self.blueprint_next_on_found = QComboBox()
        self.blueprint_next_on_not_found = QComboBox()

        tabs = QTabWidget()
        form_page = QWidget()
        form_layout = QVBoxLayout(form_page)
        form_layout.addWidget(self._build_task_box())
        form_layout.addWidget(self._build_rule_box(), 1)
        tabs.addTab(form_page, "表单编辑")
        tabs.addTab(self._build_blueprint_page(), "蓝图视图")

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        self._connect()

    def _build_task_box(self) -> QGroupBox:
        box = QGroupBox("任务设置")
        form = QFormLayout(box)
        form.addRow("任务名", self.name)
        form.addRow("", self.enabled)
        form.addRow("间隔 ms", self.interval)
        form.addRow("窗口标题", self.window_title)
        form.addRow("执行策略", self.execute_mode)
        form.addRow("失败策略", self.on_no_match)
        form.addRow("连续失败暂停", self.max_failures)
        form.addRow("最多执行次数", self.max_executions)
        roi_layout = QHBoxLayout()
        roi_layout.addWidget(self.roi_label, 1)
        roi_layout.addWidget(self.set_roi_button)
        roi_layout.addWidget(self.clear_roi_button)
        form.addRow("查找区域", roi_layout)
        return box

    def _build_rule_box(self) -> QGroupBox:
        box = QGroupBox("规则与动作")
        outer = QHBoxLayout(box)
        left = QVBoxLayout()
        left.addWidget(self.rules, 1)
        left.addWidget(self.add_rule_button)
        left.addWidget(self.remove_rule_button)

        form = QFormLayout()
        image_row = QHBoxLayout()
        image_row.addWidget(self.rule_image, 1)
        image_row.addWidget(self.pick_image_button)
        coordinate_row = QHBoxLayout()
        coordinate_row.addWidget(self.action_x)
        coordinate_row.addWidget(self.action_y)
        coordinate_row.addWidget(self.pick_coordinate_button)
        action_list = QVBoxLayout()
        action_list.addWidget(self.actions)
        action_buttons = QHBoxLayout()
        action_buttons.addWidget(self.add_action_button)
        action_buttons.addWidget(self.remove_action_button)
        action_list.addLayout(action_buttons)
        record_row = QHBoxLayout()
        record_row.addWidget(self.record_button)
        record_row.addWidget(self.record_moves)
        record_row.addWidget(self.record_status, 1)

        form.addRow("规则名", self.rule_name)
        form.addRow("", self.rule_enabled)
        form.addRow("图片", image_row)
        form.addRow("阈值", self.threshold)
        form.addRow("", self.multi)
        form.addRow("未找到", self.not_found)
        form.addRow("成立后", self.next_on_found)
        form.addRow("不成立后", self.next_on_not_found)
        form.addRow("动作列表", action_list)
        form.addRow("动作", self.action_type)
        form.addRow("", self.action_use_match)
        form.addRow("固定坐标 X/Y", coordinate_row)
        form.addRow("鼠标按钮", self.action_button)
        form.addRow("按键", self.action_key)
        form.addRow("随机偏移 px", self.offset)
        form.addRow("等待/移动/拖拽时长 ms", self.duration)
        form.addRow("拖拽目标 X", self.to_x)
        form.addRow("拖拽目标 Y", self.to_y)
        form.addRow("动作后等待 ms", self.delay_after)
        form.addRow("录制", record_row)

        outer.addLayout(left, 1)
        outer.addLayout(form, 2)
        return box

    def _build_blueprint_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.blueprint, 1)

        editor = QGroupBox("选中节点")
        form = QFormLayout(editor)
        form.addRow("规则", self.blueprint_rule_name)
        form.addRow("成立后", self.blueprint_next_on_found)
        form.addRow("不成立后", self.blueprint_next_on_not_found)
        layout.addWidget(editor)
        return page

    def _connect(self) -> None:
        for widget in [self.name, self.window_title, self.rule_name, self.rule_image, self.action_key]:
            widget.editingFinished.connect(self._write_back)
        for widget in [self.enabled, self.rule_enabled, self.multi, self.action_use_match]:
            widget.toggled.connect(self._write_back)
        for widget in [
            self.interval,
            self.max_failures,
            self.max_executions,
            self.threshold,
            self.offset,
            self.duration,
            self.action_x,
            self.action_y,
            self.to_x,
            self.to_y,
            self.delay_after,
        ]:
            widget.valueChanged.connect(self._write_back)
        for widget in [
            self.execute_mode,
            self.on_no_match,
            self.not_found,
            self.next_on_found,
            self.next_on_not_found,
            self.action_type,
            self.action_button,
        ]:
            widget.currentTextChanged.connect(self._write_back)
        self.blueprint_next_on_found.currentTextChanged.connect(self._write_blueprint_branches)
        self.blueprint_next_on_not_found.currentTextChanged.connect(self._write_blueprint_branches)
        self.rules.currentRowChanged.connect(self._show_rule)
        self.actions.currentRowChanged.connect(self._show_action)
        self.add_rule_button.clicked.connect(self._add_rule)
        self.remove_rule_button.clicked.connect(self._remove_rule)
        self.add_action_button.clicked.connect(self._add_action)
        self.remove_action_button.clicked.connect(self._remove_action)
        self.pick_image_button.clicked.connect(self._pick_image)
        self.set_roi_button.clicked.connect(self._set_roi)
        self.clear_roi_button.clicked.connect(self._clear_roi)
        self.pick_coordinate_button.clicked.connect(self.show_coordinate_picker)
        self.coordinate_picker.coordinate_selected.connect(self._set_action_coordinate)
        self.record_button.clicked.connect(self.toggle_recording)
        self.recorder.action_recorded.connect(self._append_recorded_action)
        self.recorder.status_changed.connect(self._record_status_changed)
        self.blueprint.rule_selected.connect(self._select_rule_by_id)

    def set_task(self, task: Task | None, image_root: Path) -> None:
        self.loading = True
        self.task = task
        self.image_root = image_root
        self.setEnabled(task is not None)
        if task is None:
            self.blueprint.set_task(None)
            self._refresh_blueprint_editor(None)
            self.loading = False
            return
        self.name.setText(task.name)
        self.enabled.setChecked(task.enabled)
        self.interval.setValue(task.interval_ms)
        self.window_title.setText(task.window_title)
        self.execute_mode.setCurrentText(task.execute_mode)
        self.on_no_match.setCurrentText(task.on_no_match)
        self.max_failures.setValue(task.max_failures)
        self.max_executions.setValue(task.max_executions)
        self._update_roi_label()
        self._refresh_rules()
        self._refresh_blueprint()
        self._refresh_blueprint_editor(self._current_rule())
        self.loading = False

    def show_coordinate_picker(self) -> None:
        self.coordinate_picker.show()
        self.coordinate_picker.raise_()
        self.coordinate_picker.activateWindow()

    def toggle_recording(self) -> None:
        if not self.recorder.recording:
            rule = self._current_rule()
            self.recording_rule_id = rule.id if rule else ""
        recording = self.recorder.toggle(self.record_moves.isChecked())
        if not recording:
            self.recording_rule_id = ""
        self.record_button.setText("停止录制 (F7)" if recording else "开始录制 (F7)")

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
        self.task.max_executions = self.max_executions.value()

        rule = self._current_rule()
        if rule:
            rule.name = self.rule_name.text().strip() or "新规则"
            rule.enabled = self.rule_enabled.isChecked()
            rule.image = self.rule_image.text().strip()
            rule.threshold = self.threshold.value()
            rule.multi = self.multi.isChecked()
            rule.not_found = self.not_found.currentText()
            rule.next_on_found = self.next_on_found.currentData() or ""
            rule.next_on_not_found = self.next_on_not_found.currentData() or ""
            action = self._current_action()
            if action is None:
                action = Action()
                rule.actions.append(action)
            action.type = self.action_type.currentText()
            action.use_match = self.action_use_match.isChecked()
            action.x = self.action_x.value()
            action.y = self.action_y.value()
            action.button = self.action_button.currentText()
            action.key = self.action_key.text().strip()
            action.offset_random = self.offset.value()
            action.duration_ms = self.duration.value()
            action.to_x = self.to_x.value()
            action.to_y = self.to_y.value()
            action.delay_after_ms = self.delay_after.value()
        self._sync_after_change(rule)

    def _write_blueprint_branches(self) -> None:
        if self.loading:
            return
        rule = self._current_rule()
        if not rule:
            return
        rule.next_on_found = self.blueprint_next_on_found.currentData() or ""
        rule.next_on_not_found = self.blueprint_next_on_not_found.currentData() or ""
        self._select_branch_value(self.next_on_found, rule.next_on_found)
        self._select_branch_value(self.next_on_not_found, rule.next_on_not_found)
        self._sync_after_change(rule)

    def _sync_after_change(self, rule: Rule | None = None) -> None:
        self.changed.emit()
        self._refresh_action_labels()
        self._refresh_rule_labels()
        self._refresh_branch_options(rule.id if rule else "")
        self._refresh_blueprint()
        self._refresh_blueprint_editor(rule)

    def _refresh_blueprint(self) -> None:
        self.blueprint.set_task(self.task, self.image_root)

    def _refresh_rules(self) -> None:
        selected_rule_id = self.selected_rule_id
        self.rules.clear()
        if not self.task:
            return
        for rule in self.task.rules:
            self.rules.addItem(QListWidgetItem(self._rule_label(rule)))
        if self.task.rules:
            selected_row = 0
            for index, rule in enumerate(self.task.rules):
                if rule.id == selected_rule_id:
                    selected_row = index
                    break
            self.rules.setCurrentRow(selected_row)
        else:
            self._show_rule(-1)

    def _refresh_rule_labels(self) -> None:
        if not self.task:
            return
        for index, rule in enumerate(self.task.rules):
            item = self.rules.item(index)
            if item:
                item.setText(self._rule_label(rule))

    def _rule_label(self, rule: Rule) -> str:
        target = "匹配点"
        if rule.actions and not rule.actions[0].use_match:
            target = f"{rule.actions[0].x},{rule.actions[0].y}"
        return f"{rule.name}\n{Path(rule.image).name or '未选择图片'} | {rule.threshold:.2f} | {target}"

    def _show_rule(self, row: int) -> None:
        rule = self._current_rule()
        self.loading = True
        self.selected_rule_id = rule.id if rule else ""
        enabled = rule is not None
        for widget in [
            self.rule_name,
            self.rule_enabled,
            self.rule_image,
            self.pick_image_button,
            self.threshold,
            self.multi,
            self.not_found,
            self.next_on_found,
            self.next_on_not_found,
            self.actions,
            self.add_action_button,
            self.remove_action_button,
            self.action_type,
            self.action_use_match,
            self.action_button,
            self.action_key,
            self.action_x,
            self.action_y,
            self.pick_coordinate_button,
            self.offset,
            self.duration,
            self.to_x,
            self.to_y,
            self.delay_after,
            self.remove_rule_button,
            self.record_button,
            self.record_moves,
        ]:
            widget.setEnabled(enabled)
        if not rule:
            self.rule_name.clear()
            self.rule_image.clear()
            self._refresh_blueprint_editor(None)
            self.loading = False
            return
        self.rule_name.setText(rule.name)
        self.rule_enabled.setChecked(rule.enabled)
        self.rule_image.setText(rule.image)
        self.threshold.setValue(rule.threshold)
        self.multi.setChecked(rule.multi)
        self.not_found.setCurrentText(rule.not_found)
        self._refresh_branch_options(rule.id)
        self._select_branch_value(self.next_on_found, rule.next_on_found)
        self._select_branch_value(self.next_on_not_found, rule.next_on_not_found)
        self._refresh_actions()
        self._refresh_blueprint_editor(rule)
        self.loading = False

    def _refresh_actions(self) -> None:
        self.actions.clear()
        rule = self._current_rule()
        if not rule:
            self._show_action(-1)
            return
        if not rule.actions:
            rule.actions.append(Action())
        for index, action in enumerate(rule.actions):
            target = "匹配点" if action.use_match else f"{action.x},{action.y}"
            self.actions.addItem(QListWidgetItem(f"{index + 1}. {action.type} | {target}"))
        self.actions.setCurrentRow(0)

    def _refresh_action_labels(self) -> None:
        rule = self._current_rule()
        if not rule:
            return
        for index, action in enumerate(rule.actions):
            item = self.actions.item(index)
            if item:
                target = "匹配点" if action.use_match else f"{action.x},{action.y}"
                item.setText(f"{index + 1}. {action.type} | {target}")

    def _show_action(self, row: int) -> None:
        was_loading = self.loading
        self.loading = True
        action = self._current_action()
        enabled = action is not None and self._current_rule() is not None
        for widget in [
            self.action_type,
            self.action_use_match,
            self.action_button,
            self.action_key,
            self.action_x,
            self.action_y,
            self.pick_coordinate_button,
            self.offset,
            self.duration,
            self.to_x,
            self.to_y,
            self.delay_after,
            self.remove_action_button,
        ]:
            widget.setEnabled(enabled)
        if not action:
            self.loading = was_loading
            return
        self.action_type.setCurrentText(action.type)
        self.action_use_match.setChecked(action.use_match)
        self.action_x.setValue(action.x)
        self.action_y.setValue(action.y)
        self.action_button.setCurrentText(action.button)
        self.action_key.setText(action.key)
        self.offset.setValue(action.offset_random)
        self.duration.setValue(action.duration_ms)
        self.to_x.setValue(action.to_x)
        self.to_y.setValue(action.to_y)
        self.delay_after.setValue(action.delay_after_ms)
        self.loading = was_loading

    def _refresh_branch_options(self, current_rule_id: str) -> None:
        current_found = self.next_on_found.currentData() or ""
        current_not_found = self.next_on_not_found.currentData() or ""
        self.next_on_found.blockSignals(True)
        self._fill_branch_combo(self.next_on_found, current_rule_id)
        self._select_branch_value(self.next_on_found, current_found)
        self.next_on_found.blockSignals(False)
        self.next_on_not_found.blockSignals(True)
        self._fill_branch_combo(self.next_on_not_found, current_rule_id)
        self._select_branch_value(self.next_on_not_found, current_not_found)
        self.next_on_not_found.blockSignals(False)

    def _refresh_blueprint_editor(self, rule: Rule | None) -> None:
        self.blueprint_rule_name.setText(rule.name if rule else "未选择规则")
        self.blueprint.set_selected_rule(rule.id if rule else "")
        for combo in [self.blueprint_next_on_found, self.blueprint_next_on_not_found]:
            combo.blockSignals(True)
            self._fill_branch_combo(combo, rule.id if rule else "")
        if rule:
            self._select_branch_value(self.blueprint_next_on_found, rule.next_on_found)
            self._select_branch_value(self.blueprint_next_on_not_found, rule.next_on_not_found)
        for combo in [self.blueprint_next_on_found, self.blueprint_next_on_not_found]:
            combo.blockSignals(False)
        self.blueprint_next_on_found.setEnabled(rule is not None)
        self.blueprint_next_on_not_found.setEnabled(rule is not None)

    def _fill_branch_combo(self, combo: QComboBox, current_rule_id: str) -> None:
        combo.clear()
        combo.addItem("按顺序继续", "")
        combo.addItem("结束任务", END_TASK)
        if self.task:
            for rule in self.task.rules:
                if rule.id != current_rule_id:
                    combo.addItem(rule.name, rule.id)

    def _select_branch_value(self, combo: QComboBox, rule_id: str) -> None:
        index = combo.findData(rule_id or "")
        combo.setCurrentIndex(max(0, index))

    def _current_rule(self) -> Rule | None:
        if self.task is None:
            return None
        row = self.rules.currentRow()
        if row < 0 or row >= len(self.task.rules):
            return None
        return self.task.rules[row]

    def _current_action(self) -> Action | None:
        rule = self._current_rule()
        if not rule:
            return None
        row = self.actions.currentRow()
        if row < 0 or row >= len(rule.actions):
            return None
        return rule.actions[row]

    def _select_rule_by_id(self, rule_id: str) -> None:
        if not self.task:
            return
        self.selected_rule_id = rule_id
        for index, rule in enumerate(self.task.rules):
            if rule.id == rule_id:
                self.rules.setCurrentRow(index)
                self._refresh_blueprint_editor(rule)
                break

    def _add_rule(self) -> None:
        if not self.task:
            return
        self.task.rules.append(Rule(name=f"规则 {len(self.task.rules) + 1}"))
        self._refresh_rules()
        self.rules.setCurrentRow(len(self.task.rules) - 1)
        self.changed.emit()
        self._refresh_blueprint()

    def _remove_rule(self) -> None:
        if not self.task:
            return
        row = self.rules.currentRow()
        if row >= 0:
            removed = self.task.rules.pop(row)
            for rule in self.task.rules:
                if rule.next_on_found == removed.id:
                    rule.next_on_found = ""
                if rule.next_on_not_found == removed.id:
                    rule.next_on_not_found = ""
            self._refresh_rules()
            self.changed.emit()
            self._refresh_blueprint()

    def _add_action(self) -> None:
        rule = self._current_rule()
        if not rule:
            return
        rule.actions.append(Action())
        self._refresh_actions()
        self.actions.setCurrentRow(len(rule.actions) - 1)
        self.changed.emit()
        self._refresh_blueprint()

    def _remove_action(self) -> None:
        rule = self._current_rule()
        if not rule:
            return
        row = self.actions.currentRow()
        if row >= 0 and len(rule.actions) > 1:
            rule.actions.pop(row)
            self._refresh_actions()
            self.actions.setCurrentRow(min(row, len(rule.actions) - 1))
            self.changed.emit()
            self._refresh_blueprint()

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

    def _set_action_coordinate(self, x: int, y: int) -> None:
        self.action_use_match.setChecked(False)
        self.action_x.setValue(x)
        self.action_y.setValue(y)
        self._write_back()

    def _append_recorded_action(self, action: Action) -> None:
        if self._is_record_button_click(action):
            self.toggle_recording()
            return
        rule = self._recording_rule()
        if not rule:
            return
        rule.actions.append(action)
        self._select_rule_by_id(rule.id)
        self._refresh_actions()
        self.actions.setCurrentRow(len(rule.actions) - 1)
        self.changed.emit()
        self._refresh_action_labels()
        self._refresh_rule_labels()
        self._refresh_blueprint()
        self.log_requested.emit("info", f"已录制动作: {action.type}")

    def _record_status_changed(self, message: str) -> None:
        self.record_status.setText(message)
        self.log_requested.emit("info", message)

    def _is_record_button_click(self, action: Action) -> bool:
        if not self.recorder.recording or action.type not in {"click", "right_click"}:
            return False
        top_left = self.record_button.mapToGlobal(self.record_button.rect().topLeft())
        bottom_right = self.record_button.mapToGlobal(self.record_button.rect().bottomRight())
        return top_left.x() <= action.x <= bottom_right.x() and top_left.y() <= action.y <= bottom_right.y()

    def _recording_rule(self) -> Rule | None:
        if not self.task:
            return None
        target_id = self.recording_rule_id or self.selected_rule_id
        for rule in self.task.rules:
            if rule.id == target_id:
                return rule
        return self._current_rule()
