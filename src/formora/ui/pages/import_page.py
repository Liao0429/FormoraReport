"""文档导入页：选择模板 + 数据，解析并展示结构化信息。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from formora.core import data_reader, template_parser
from formora.core.errors import FormoraError
from formora.ui.widgets import Card, file_row, primary_button, secondary_button


class ImportPage(QWidget):
    def __init__(self, state, navigate):
        super().__init__()
        self.state = state
        self.navigate = navigate
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        title = QLabel("文档导入")
        title.setObjectName("AppTitle")
        lay.addWidget(title)

        card = Card("选择文件")
        self.template_edit = QLineEdit()
        self.template_edit.setPlaceholderText("选择 .docx 实验报告模板")
        tpl_btn = secondary_button("浏览…")
        tpl_btn.clicked.connect(self._pick_template)
        card.add_widget(file_row("实验模板", self.template_edit, tpl_btn))

        self.data_edit = QLineEdit()
        self.data_edit.setPlaceholderText("选择 CSV / XLSX / TXT / Markdown / PDF 实验数据")
        data_btn = secondary_button("浏览…")
        data_btn.clicked.connect(self._pick_data)
        card.add_widget(file_row("实验数据", self.data_edit, data_btn))

        parse_btn = primary_button("解析模板与数据")
        parse_btn.clicked.connect(self._parse)
        card.add_widget(parse_btn)
        lay.addWidget(card)

        info_card = Card("解析结果")
        self.info_text = QPlainTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setPlaceholderText("解析后显示占位符、章节、表格等信息")
        info_card.add_widget(self.info_text)
        lay.addWidget(info_card, 1)

        bottom = QHBoxLayout()
        next_btn = primary_button("下一步：字段映射 →")
        next_btn.clicked.connect(lambda: self.navigate("mapping"))
        bottom.addStretch(1)
        bottom.addWidget(next_btn)
        lay.addLayout(bottom)

    def _pick_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择实验报告模板", str(Path.home()),
            "Word 模板 (*.docx);;所有文件 (*.*)")
        if path:
            self.template_edit.setText(path)

    def _pick_data(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择实验数据",
            str(Path.home()),
            "数据文件 (*.csv *.xlsx *.txt *.md *.pdf);;所有文件 (*.*)")
        if path:
            self.data_edit.setText(path)

    def _parse(self):
        tpl = self.template_edit.text().strip()
        data = self.data_edit.text().strip()
        if not tpl:
            QMessageBox.warning(self, "提示", "请先选择实验报告模板。")
            return
        try:
            info = template_parser.parse_template(tpl)
            self.state.new_task(name=Path(tpl).stem)
            self.state.task.template_path = Path(tpl)
            self.state.template = info

            ds = None
            if data:
                ds = data_reader.read_data(data)
                self.state.data = ds
                self.state.task.data_source = ds

            lines = []
            lines.append(f"模板：{tpl}")
            lines.append(f"占位符（{len(info.placeholders)}）：{', '.join(info.placeholders)}")
            if info.loop_blocks:
                lines.append(f"循环块：{', '.join(info.loop_blocks)}")
            if info.sections:
                lines.append("识别章节：" + "、".join(info.sections.keys()))
            if info.tables:
                lines.append(f"表格数：{len(info.tables)}")
                for t in info.tables[:3]:
                    lines.append(f"  表格{t.index}: {t.col_count}列×{t.row_count}行 表头={t.header}")
            if info.has_images:
                lines.append("模板包含图片元素（将尽量保留）")
            if info.has_header_footer:
                lines.append("模板包含页眉/页脚")
            if ds:
                lines.append(f"\n数据：{data}（{ds.summary}）")
                if ds.columns:
                    lines.append(f"数据列：{', '.join(ds.columns)}")
                if ds.text:
                    lines.append(f"\n文本前 200 字：\n{ds.text[:200]}")
            self.info_text.setPlainText("\n".join(lines))
        except FormoraError as e:
            QMessageBox.critical(self, "解析失败", str(e))