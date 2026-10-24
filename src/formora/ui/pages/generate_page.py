"""生成结果页：输出路径、日志、操作按钮。"""

from __future__ import annotations

import os

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from formora.core.errors import FormoraError
from formora.ui.widgets import Card, primary_button, secondary_button


class GeneratePage(QWidget):
    def __init__(self, state, navigate):
        super().__init__()
        self.state = state
        self.navigate = navigate
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        title = QLabel("报告生成")
        title.setObjectName("AppTitle")
        lay.addWidget(title)

        out_card = Card("输出文件")
        self.out_edit = QLineEdit()
        self.out_edit.setReadOnly(True)
        out_card.add_widget(self.out_edit)
        lay.addWidget(out_card)

        log_card = Card("处理日志")
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        log_card.add_widget(self.log_text)
        lay.addWidget(log_card, 1)

        ops = QHBoxLayout()
        open_btn = secondary_button("打开输出文件夹")
        open_btn.clicked.connect(self._open_folder)
        preview_btn = primary_button("预览报告")
        preview_btn.clicked.connect(lambda: self.navigate("preview"))
        export_btn = secondary_button("导出 PDF")
        export_btn.clicked.connect(self._export_pdf)
        self.batch_pdf_btn = secondary_button("批量导出 PDF")
        self.batch_pdf_btn.clicked.connect(self._export_batch_pdf)
        self.batch_pdf_btn.setToolTip("把当前批次目录下的所有 DOCX 转为 PDF")
        ops.addWidget(open_btn)
        ops.addWidget(export_btn)
        ops.addWidget(self.batch_pdf_btn)
        ops.addStretch(1)
        ops.addWidget(preview_btn)
        lay.addLayout(ops)

    def refresh(self):
        if self.state.output_path:
            self.out_edit.setText(self.state.output_path)
            logs = self.state.task.logs if self.state.task else []
            self.log_text.setPlainText(
                "\n".join(f"[{l.level}] {l.message}" for l in logs) or "（无日志）"
            )
        # 有批次目录才允许批量导出 PDF
        if hasattr(self, "batch_pdf_btn"):
            has_batch = bool(getattr(self.state, "last_batch_dir", None))
            self.batch_pdf_btn.setEnabled(has_batch)

    def _open_folder(self):
        if not self.state.output_path:
            return
        folder = os.path.dirname(self.state.output_path)
        # 跨平台打开文件夹（Windows 用 explorer，macOS Finder，Linux xdg-open）
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

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

    def _export_batch_pdf(self):
        """把当前批次目录下的所有 DOCX 转为 PDF（串行，避免 LibreOffice 冲突）。"""
        import glob

        batch_dir = getattr(self.state, "last_batch_dir", None)
        if not batch_dir or not os.path.isdir(batch_dir):
            QMessageBox.warning(self, "提示", "没有可用的批次目录。")
            return
        from formora.services.report_service import batch_export_pdf

        docx_files = sorted(glob.glob(os.path.join(batch_dir, "*.docx")))
        if not docx_files:
            QMessageBox.warning(self, "提示", "批次目录里没有 DOCX 文件。")
            return
        ok, failed = batch_export_pdf(docx_files)
        msg = f"✅ 已导出 {ok} 份 PDF"
        if failed:
            msg += f"\n\n失败 {len(failed)} 份：\n" + "\n".join(failed[:5])
        QMessageBox.information(self, "批量导出 PDF", msg)
