"""结果预览页：读取生成的 DOCX 文本并展示；支持导出 PDF。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QVBoxLayout, QWidget

from formora.core.errors import FormoraError
from formora.ui.widgets import Card, primary_button, secondary_button


class PreviewPage(QWidget):
    def __init__(self, state, navigate):
        super().__init__()
        self.state = state
        self.navigate = navigate
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        title = QLabel("结果预览")
        title.setObjectName("AppTitle")
        lay.addWidget(title)

        card = Card("报告内容预览")
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlaceholderText("生成后可在此预览文本内容")
        card.add_widget(self.text_edit)
        lay.addWidget(card, 1)

        ops = QHBoxLayout()
        back_btn = secondary_button("← 返回生成")
        back_btn.clicked.connect(lambda: self.navigate("generate"))
        self.ai_review_btn = secondary_button("✨ AI 审查")
        self.ai_review_btn.clicked.connect(self._ai_review)
        export_btn = primary_button("导出 PDF")
        export_btn.clicked.connect(self._export_pdf)
        ops.addWidget(back_btn)
        ops.addWidget(self.ai_review_btn)
        ops.addStretch(1)
        ops.addWidget(export_btn)
        lay.addLayout(ops)

    def _ai_sources_text(self) -> str:
        """把当前映射中的 AI 来源追踪信息格式化为文本。"""
        sources = [m for m in self.state.mappings if m.source or m.needs_confirmation]
        if not sources:
            return ""
        lines = ["\n【AI 来源追踪】"]
        for m in sources:
            flag = "（待确认）" if m.needs_confirmation else ""
            lines.append(f"- {m.template_field}{flag}: {m.source or '无依据'}")
        return "\n".join(lines)

    def _ai_review(self):
        from formora.ai import client

        if not self.state.output_path or not Path(self.state.output_path).exists():
            QMessageBox.warning(self, "提示", "还没有可审查的输出文件。")
            return
        cfg = self.state.config
        if not client.is_configured(cfg):
            QMessageBox.information(
                self, "AI 模式未启用",
                "AI 审查需要在「设置 → AI 智能模式」中配置 API 地址、模型与密钥。")
            return
        try:
            from docx import Document
            doc = Document(self.state.output_path)
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            for i, table in enumerate(doc.tables):
                parts.append(f"[表格 {i+1}]")
                for row in table.rows:
                    parts.append(" | ".join(c.text.strip() for c in row.cells))
            report_text = "\n".join(parts)
        except Exception as e:
            QMessageBox.warning(self, "读取报告失败", str(e))
            return
        try:
            issues = client.review_report(cfg, report_text)
        except FormoraError as e:
            QMessageBox.critical(self, "AI 审查失败", str(e))
            return
        if not issues:
            QMessageBox.information(self, "AI 审查", "未发现问题。")
            return
        lines = ["AI 审查发现以下问题："]
        for iss in issues:
            lines.append(f"[{iss.get('severity', 'info')}] {iss.get('field', '')}: {iss.get('issue', '')}")
        self.text_edit.setPlainText("\n".join(lines))

    def refresh(self):
        if not self.state.output_path or not Path(self.state.output_path).exists():
            self.text_edit.setPlainText("（还没有可预览的输出文件）")
            return
        try:
            from docx import Document
            doc = Document(self.state.output_path)
            parts = []
            for p in doc.paragraphs:
                if p.text.strip():
                    parts.append(p.text)
            for i, table in enumerate(doc.tables):
                parts.append(f"[表格 {i+1}]")
                for row in table.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
            parts.append(self._ai_sources_text())
            self.text_edit.setPlainText("\n".join(parts))
        except Exception as e:
            self.text_edit.setPlainText(f"读取预览失败：{e}")

    def _export_pdf(self):
        if not self.state.output_path:
            QMessageBox.warning(self, "提示", "还没有输出文件。")
            return
        from formora.core import pdf_exporter
        try:
            out = self.state.output_path.replace(".docx", ".pdf")
            pdf_exporter.export_pdf(self.state.output_path, out)
            QMessageBox.information(self, "导出成功", f"PDF 已导出：\n{out}")
        except FormoraError as e:
            QMessageBox.warning(self, "导出失败", str(e))