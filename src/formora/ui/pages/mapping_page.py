"""字段映射页：自动映射 + 手动编辑（文本/常量/图片）+ 校验 + 生成/批量生成。

生成、图表、AI 素材等纯逻辑已抽到 services/report_service.py，本页只负责 UI 交互。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from formora.core import mapper, validator
from formora.core.errors import FormoraError
from formora.services import report_service
from formora.services.report_service import is_image_field
from formora.ui.widgets import Card, hint_label, primary_button, secondary_button


class MappingPage(QWidget):
    def __init__(self, state, navigate):
        super().__init__()
        self.state = state
        self.navigate = navigate
        self._val_edits: dict[int, QLineEdit] = {}
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        title = QLabel("字段映射与填写")
        title.setObjectName("AppTitle")
        lay.addWidget(title)

        hint = hint_label(
            "自动将模板占位符与数据列匹配。文本字段填内容；字段名含「截图/图/图表」的"
            "可绑定本地图片，生成时会插入到原模板对应位置。")
        lay.addWidget(hint)

        card = Card("字段映射")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["模板字段", "来源类型", "来源/数据列", "值（文本/图片路径）"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        card.add_widget(self.table)

        opts = QHBoxLayout()
        opts.addWidget(QLabel("数据行:"))
        self.row_combo = QComboBox()
        opts.addWidget(self.row_combo)
        self.chart_check = QCheckBox("自动生成实验数据图表并插入到「图表」占位符")
        self.chart_check.setChecked(True)
        opts.addWidget(self.chart_check)
        opts.addStretch(1)
        card.add_layout(opts)
        lay.addWidget(card)

        ops = QHBoxLayout()
        self.validate_btn = secondary_button("校验")
        self.validate_btn.clicked.connect(self._validate)
        self.ai_btn = secondary_button("✨ AI 辅助填写")
        self.ai_btn.clicked.connect(self._ai_assist)
        self.batch_btn = secondary_button("批量生成全部数据行")
        self.batch_btn.clicked.connect(self._generate_batch)
        self.gen_btn = primary_button("生成当前行报告 →")
        self.gen_btn.clicked.connect(self._generate)
        ops.addWidget(self.validate_btn)
        ops.addWidget(self.ai_btn)
        ops.addWidget(self.batch_btn)
        ops.addStretch(1)
        ops.addWidget(self.gen_btn)
        lay.addLayout(ops)

        result_card = Card("校验结果")
        self.issues_text = QPlainTextEdit()
        self.issues_text.setReadOnly(True)
        self.issues_text.setMaximumHeight(160)
        result_card.add_widget(self.issues_text)
        lay.addWidget(result_card)

    # ---------- 状态与表格填充 ----------

    def refresh(self):
        """从 state 重建映射表。无模板时非阻塞提示。"""
        state = self.state
        if not state.template:
            self.table.setRowCount(0)
            self.issues_text.setPlainText("⚠️ 请先在「文档导入」页选择并解析实验报告模板。")
            return
        state.mappings = mapper.auto_map(state.template, state.data)

        self.row_combo.clear()
        if state.data and state.data.is_tabular:
            for i, r in enumerate(state.data.rows):
                label = f"第 {i + 1} 行：" + " ".join(f"{k}={v}" for k, v in list(r.items())[:3])
                self.row_combo.addItem(label)
            self.row_combo.setCurrentIndex(0)
        else:
            self.row_combo.addItem("（无表格数据）")

        self._fill_table()

    def _fill_table(self):
        self._val_edits.clear()
        self.table.setRowCount(0)
        for m in self.state.mappings:
            row = self.table.rowCount()
            self.table.insertRow(row)

            field_item = QTableWidgetItem(m.template_field)
            field_item.setFlags(field_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, field_item)

            # 默认类型：图片字段 -> 图片；有列匹配 -> 数据列；否则常量
            default_type = "图片" if is_image_field(m.template_field) else (
                "数据列" if m.source_type == "column" else "常量")
            type_combo = QComboBox()
            type_combo.addItems(["数据列", "常量", "图片"])
            type_combo.setCurrentText(default_type)
            type_combo.currentIndexChanged.connect(lambda _, r=row: self._type_changed(r))
            self.table.setCellWidget(row, 1, type_combo)

            col_combo = QComboBox()
            if self.state.data and self.state.data.columns:
                col_combo.addItems(self.state.data.columns)
            col_combo.setCurrentText(m.source_column or "")
            col_combo.currentTextChanged.connect(lambda _, r=row: self._col_changed(r))
            self.table.setCellWidget(row, 2, col_combo)

            self._set_value_cell(row, default_type)
            col_combo.setEnabled(default_type == "数据列")

        self._sync_row_combo()

    def _set_value_cell(self, row: int, source_type: str):
        """在「值」单元格放置文本编辑框或图片选择框。"""
        m = self.state.mappings[row]
        if source_type == "图片":
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            val_edit = QLineEdit()
            val_edit.setPlaceholderText("选择一张图片（截图/图表）…")
            val_edit.setText(str(m.value or ""))
            browse = secondary_button("选择图片…")
            browse.clicked.connect(lambda _, r=row: self._pick_image(r))
            h.addWidget(val_edit, 1)
            h.addWidget(browse)
            self._val_edits[row] = val_edit
            self.table.setCellWidget(row, 3, container)
        else:
            val_edit = QLineEdit()
            if source_type == "数据列" and m.source_column:
                val_edit.setText(str(self._current_row().get(m.source_column, "")))
            elif source_type == "常量":
                val_edit.setText(m.constant_value or "")
            val_edit.textChanged.connect(lambda _, r=row: self._value_changed(r))
            self._val_edits[row] = val_edit
            self.table.setCellWidget(row, 3, val_edit)

    def _current_type(self, row: int) -> str:
        return self.table.cellWidget(row, 1).currentText()

    def _current_col(self, row: int) -> str:
        return self.table.cellWidget(row, 2).currentText()

    def _value_edit(self, row: int) -> QLineEdit | None:
        return self._val_edits.get(row)

    # ---------- 交互回调 ----------

    def _sync_row_combo(self):
        if not self.state.data or not self.state.data.is_tabular:
            return
        for row in range(self.table.rowCount()):
            if self._current_type(row) != "数据列":
                continue
            col = self._current_col(row)
            edit = self._value_edit(row)
            if edit:
                edit.setText(str(self._current_row().get(col, "")))

    def _current_row(self) -> dict:
        if self.state.data and self.state.data.is_tabular:
            idx = max(0, self.row_combo.currentIndex())
            if idx < len(self.state.data.rows):
                return self.state.data.rows[idx]
        return {}

    def _type_changed(self, row: int):
        t = self._current_type(row)
        col_combo = self.table.cellWidget(row, 2)
        col_combo.setEnabled(t == "数据列")
        m = self.state.mappings[row]
        if t == "图片":
            m.source_type = "image"
            self._set_value_cell(row, "图片")
        elif t == "数据列":
            m.source_type = "column"
            self._set_value_cell(row, "数据列")
            self._sync_row_combo()
        else:
            m.source_type = "constant"
            self._set_value_cell(row, "常量")

    def _col_changed(self, row: int):
        if self._current_type(row) == "数据列":
            self._sync_row_combo()

    def _value_changed(self, row: int):
        m = self.state.mappings[row]
        t = self._current_type(row)
        edit = self._value_edit(row)
        text = edit.text() if edit else ""
        if t == "数据列":
            m.source_type = "column"
            m.source_column = self._current_col(row)
            m.value = text
        elif t == "常量":
            m.source_type = "constant"
            m.constant_value = text
        elif t == "图片":
            m.source_type = "image"
            m.value = text

    def _pick_image(self, row: int):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", str(Path.home()),
            "图片 (*.png *.jpg *.jpeg *.gif *.bmp);;所有文件 (*.*)")
        if path:
            m = self.state.mappings[row]
            m.source_type = "image"
            m.value = path
            edit = self._value_edit(row)
            if edit:
                edit.setText(path)

    def _collect_mappings(self):
        for row in range(self.table.rowCount()):
            self._value_changed(row)
        return self.state.mappings

    # ---------- 生成（逻辑在 report_service） ----------

    def _image_vars(self) -> dict[str, str]:
        """收集图片字段 -> 图片路径（含自动图表）。"""
        return report_service.collect_image_vars(self.state, self.chart_check.isChecked())

    def _image_placeholders(self) -> set[str]:
        return report_service.image_placeholders(self.state, self.chart_check.isChecked())

    def _validate(self):
        try:
            context = report_service.resolve_context(self.state, self._current_row())
            issues = validator.validate_context(
                context, self.state.template,
                image_placeholders=self._image_placeholders())
            lines = [f"[{iss.severity}] {iss.field}: {iss.message}" for iss in issues]
            self.issues_text.setPlainText("\n".join(lines) if lines else "✅ 未发现明显问题。")
        except FormoraError as e:
            self.issues_text.setPlainText(f"校验出错：{e}")

    def _generate(self):
        state = self.state
        if not state.template:
            QMessageBox.warning(self, "提示", "请先解析模板。")
            return
        try:
            out_path = report_service.generate_single(state, row=self._current_row())
            self.issues_text.setPlainText(f"✅ 报告已生成：\n{out_path}")
            self.navigate("generate")
        except FormoraError as e:
            QMessageBox.critical(self, "生成失败", str(e))

    def _generate_batch(self):
        state = self.state
        if not state.template:
            QMessageBox.warning(self, "提示", "请先解析模板。")
            return
        if not state.data or not state.data.is_tabular or not state.data.rows:
            QMessageBox.warning(self, "提示", "当前没有表格型数据，无法批量生成。")
            return
        self._collect_mappings()
        try:
            results, errors = report_service.generate_batch(state)
        except FormoraError as e:
            QMessageBox.critical(self, "批量生成失败", str(e))
            return
        output_dir = Path(state.config.get("output_dir")) / f"{state.task.name}_批量"
        summary = [f"✅ 批量生成完成：成功 {len(results)} 份，失败 {len(errors)} 份。",
                   f"输出目录：{output_dir}"]
        summary.extend(f"  - {p}" for p in results[:20])
        if errors:
            summary.append("\n失败：")
            summary.extend(errors[:10])
        self.issues_text.setPlainText("\n".join(summary))

    # ---------- AI 辅助（可选） ----------

    def _materials_text(self) -> str:
        return report_service.materials_text(self.state)

    def _ai_assist(self):
        from formora.ai import client

        cfg = self.state.config
        if not client.is_configured(cfg):
            QMessageBox.information(
                self, "AI 模式未启用",
                "AI 辅助需要你主动启用并在「设置 → AI 智能模式」中配置 API 地址、模型与密钥。\n"
                "未配置时，无 AI 模式仍可正常完成全部基础功能。")
            return

        # 隐私确认
        if not cfg.get("privacy", {}).get("upload_warning_shown"):
            ret = QMessageBox.question(
                self, "隐私提示",
                "AI 辅助会把当前模板字段名与实验素材文本发送到你配置的模型 API。\n"
                "请确认你信任该 API 服务商。是否继续？")
            if ret != QMessageBox.StandardButton.Yes:
                return
            cfg.set("privacy", {**cfg.get("privacy", {}), "upload_warning_shown": True})
            cfg.save()

        self._collect_mappings()
        fields = [m.template_field for m in self.state.mappings
                  if m.source_type != "image"]
        materials = self._materials_text()
        if not materials.strip():
            QMessageBox.warning(self, "提示", "当前没有可用的实验素材文本。请先在「文档导入」页导入 TXT/MD/PDF 或表格数据。")
            return

        self.issues_text.setPlainText("⏳ AI 正在根据素材提取字段内容，请稍候…")
        QMessageBox.information(
            self, "提示",
            "AI 只会依据素材生成内容；无依据的字段会标记为「待补充」，生成后请逐项检查再导出。")
        try:
            result = client.extract_fields(cfg, materials, fields)
        except FormoraError as e:
            self.issues_text.setPlainText(f"AI 请求失败：{e}")
            QMessageBox.critical(self, "AI 失败", str(e))
            return

        by_field = {m.template_field: m for m in self.state.mappings}
        applied = 0
        confirmed = []
        for item in result:
            fname = item.get("field", "")
            value = item.get("value", "")
            needs = bool(item.get("needs_confirmation"))
            m = by_field.get(fname)
            if m is None or m.source_type == "image":
                continue
            m.source_type = "constant"
            m.constant_value = value
            # 来源追踪：记录 AI 依据与「待确认」标记
            m.source = item.get("source", "")
            m.needs_confirmation = needs
            confirmed.append(f"{fname}" + ("（待确认）" if needs else ""))
            applied += 1

        self.state.task.log("info", "system", f"AI 辅助填充 {applied} 个字段")
        self._fill_table()
        note = [
            f"✅ AI 已填充 {applied} 个字段。",
            "标记「待确认」的字段请务必人工核对后补全。",
            "已处理字段：" + ("、".join(confirmed[:20]) if confirmed else "无"),
        ]
        self.issues_text.setPlainText("\n".join(note))