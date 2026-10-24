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
from formora.ui.widgets import (
    Card,
    file_row,
    hint_label,
    primary_button,
    secondary_button,
)


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
        tpl_hint = hint_label(
            "提示：模板中请用 {{实验名称}}、{{姓名}} 这类标记待填位置，解析后会自动识别。"
        )
        tpl_hint.setWordWrap(True)
        card.add_widget(tpl_hint)

        self.data_edit = QLineEdit()
        self.data_edit.setPlaceholderText(
            "选择 CSV / XLSX / TXT / Markdown / PDF 实验数据"
        )
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
            self,
            "选择实验报告模板",
            str(Path.home()),
            "Word 模板 (*.docx);;所有文件 (*.*)",
        )
        if path:
            self.template_edit.setText(path)

    def _pick_data(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择实验数据",
            str(Path.home()),
            "数据文件 (*.csv *.xlsx *.txt *.md *.pdf);;所有文件 (*.*)",
        )
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
            lines.append(f"✅ 模板解析成功：{Path(tpl).name}")
            if info.placeholders:
                lines.append(
                    f"模板里检测到 {len(info.placeholders)} 个待填的空位（{{{{字段名}}}}）："
                )
                lines.append("　" + "、".join(info.placeholders))
            else:
                lines.append("⚠️ 模板里没有检测到任何 {{字段名}} 标记。")
                lines.append(
                    "请在 Word 中用 {{实验名称}} 这样的标记标出待填位置，再重新导入。"
                )
            if info.loop_blocks:
                lines.append("检测到 1 个数据循环区（用于逐条列出实验数据）：")
                lines.append("　该区域由数据自动填充，无需在右侧单独填写。")
            if info.sections:
                lines.append("识别到的章节：" + "、".join(info.sections.keys()))
            if info.tables:
                lines.append(f"模板含 {len(info.tables)} 个表格，会尽量保留原格式。")
            if info.has_images:
                lines.append("模板包含图片元素（将尽量保留）")
            if info.has_header_footer:
                lines.append("模板包含页眉/页脚（将保留）")
            if ds:
                lines.append(f"\n数据文件：{Path(data).name}（{ds.summary}）")
                if ds.columns:
                    lines.append("数据列：" + "、".join(ds.columns))
            lines.append(
                "\n下一步：点击「下一步：字段映射 →」，把模板空位与数据列对应起来。"
            )
            self.info_text.setPlainText("\n".join(lines))
        except FormoraError as e:
            QMessageBox.critical(self, "解析失败", str(e))
