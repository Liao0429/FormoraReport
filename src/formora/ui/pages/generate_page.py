"""生成结果页：输出路径、日志、操作按钮。"""

from __future__ import annotations

import os

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from formora.core.errors import BatchExportCancelledError
from formora.ui.errors import show_error
from formora.ui.widgets import Card, primary_button, secondary_button


class _BatchPdfWorker(QThread):
    """后台批量 PDF 转换线程：通过信号回传进度/结果/取消，避免阻塞 UI。"""

    progress = Signal(int, int)  # (已完成数, 总数)
    done = Signal(int, object)  # (成功数, 失败列表)
    cancelled = Signal()
    failed = Signal(object)

    def __init__(self, docx_files: list[str]):
        super().__init__()
        self._docx_files = docx_files
        self._cancel_requested = False

    def request_cancel(self) -> None:
        """请求协作式取消：worker 在下一份文件前检查并生效。"""
        self._cancel_requested = True

    def run(self) -> None:
        from formora.services.report_service import batch_export_pdf

        try:
            ok, failed = batch_export_pdf(
                self._docx_files,
                progress_cb=lambda done, total: self.progress.emit(done, total),
                should_cancel=lambda: self._cancel_requested,
            )
            self.done.emit(ok, failed)
        except BatchExportCancelledError:
            self.cancelled.emit()
        except Exception as exc:  # noqa: BLE001 - 统一转用户可读错误
            self.failed.emit(exc)


class _SinglePdfWorker(QThread):
    """后台单份 PDF 转换线程：避免 LibreOffice 转换阻塞 UI。"""

    done = Signal(object)  # 输出 PDF 路径
    failed = Signal(object)  # 异常对象

    def __init__(self, docx_path: str):
        super().__init__()
        self._docx_path = docx_path

    def run(self) -> None:
        from formora.core import pdf_exporter

        try:
            # 用 splitext 而非 replace，避免路径目录名含 ".docx" 时替换错位置
            out = os.path.splitext(self._docx_path)[0] + ".pdf"
            pdf_exporter.export_pdf(self._docx_path, out)
            self.done.emit(out)
        except Exception as exc:  # noqa: BLE001 - 统一转用户可读错误
            self.failed.emit(exc)

class GeneratePage(QWidget):
    def __init__(self, state, navigate):
        super().__init__()
        self.state = state
        self.navigate = navigate
        self._batch_thread: _BatchPdfWorker | None = None
        self._single_thread: _SinglePdfWorker | None = None
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
        self.log_text.setTabChangesFocus(True)
        log_card.add_widget(self.log_text)
        lay.addWidget(log_card, 1)

        ops = QHBoxLayout()
        open_btn = secondary_button("打开输出文件夹")
        open_btn.clicked.connect(self._open_folder)
        preview_btn = primary_button("预览报告")
        preview_btn.clicked.connect(lambda: self.navigate("preview"))
        self.export_btn = secondary_button("导出 PDF")
        self.export_btn.clicked.connect(self._export_pdf)
        self.batch_pdf_btn = secondary_button("批量导出 PDF")
        self.batch_pdf_btn.clicked.connect(self._export_batch_pdf)
        self.batch_pdf_btn.setToolTip("把当前批次目录下的所有 DOCX 转为 PDF")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.hide()
        self.cancel_btn = secondary_button("取消")
        self.cancel_btn.clicked.connect(self._cancel_batch_pdf)
        self.cancel_btn.hide()
        ops.addWidget(self.progress_bar)
        ops.addWidget(self.cancel_btn)
        ops.addWidget(open_btn)
        ops.addWidget(self.export_btn)
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
        else:
            # 新任务尚未生成：清空残留的上一次输出，避免界面与行为矛盾
            self.out_edit.clear()
            self.log_text.setPlainText("（尚未生成报告）")
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
        if self._single_thread is not None and self._single_thread.isRunning():
            return  # 已有单份导出在后台执行，避免重复触发
        self.export_btn.setEnabled(False)
        thread = _SinglePdfWorker(self.state.output_path)
        self._single_thread = thread
        thread.done.connect(self._on_single_pdf_done)
        thread.failed.connect(self._on_single_pdf_failed)
        thread.finished.connect(self._on_single_pdf_thread_finished)
        thread.start()

    def _on_single_pdf_done(self, out: str) -> None:
        QMessageBox.information(self, "导出成功", f"PDF 已导出：\n{out}")

    def _on_single_pdf_failed(self, exc) -> None:
        show_error(self, exc, "导出 PDF 失败，请确认已安装 LibreOffice 且文件未被占用。", title="导出 PDF 失败", prefix="导出 PDF")

    def _on_single_pdf_thread_finished(self) -> None:
        if self._single_thread is not self.sender():
            return  # 过期线程的 finished 信号，忽略以免覆盖新线程状态
        self.export_btn.setEnabled(True)
        self._single_thread = None

    def _export_batch_pdf(self):
        """把当前批次目录下的所有 DOCX 转为 PDF（后台线程执行，可取消）。"""
        import glob

        if self._batch_thread is not None:
            if self._batch_thread.isRunning():
                return  # 已有批次在转换，避免重复触发
            # 上一个线程已结束但 finished 尚未处理：清掉过期引用再启动新线程
            self._batch_thread = None
        batch_dir = getattr(self.state, "last_batch_dir", None)
        if not batch_dir or not os.path.isdir(batch_dir):
            QMessageBox.warning(self, "提示", "没有可用的批次目录。")
            return
        docx_files = sorted(glob.glob(os.path.join(batch_dir, "*.docx")))
        if not docx_files:
            QMessageBox.warning(self, "提示", "批次目录里没有 DOCX 文件。")
            return

        self.batch_pdf_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setRange(0, len(docx_files))
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.cancel_btn.show()

        thread = _BatchPdfWorker(docx_files)
        self._batch_thread = thread
        thread.progress.connect(self._on_batch_progress)
        thread.done.connect(self._on_batch_done)
        thread.cancelled.connect(self._on_batch_cancelled)
        thread.failed.connect(self._on_batch_failed)
        thread.finished.connect(self._on_batch_thread_finished)
        thread.start()

    def _cancel_batch_pdf(self):
        if self._batch_thread is not None:
            self.cancel_btn.setEnabled(False)
            self._batch_thread.request_cancel()

    def _on_batch_progress(self, done: int, total: int) -> None:
        self.progress_bar.setValue(done)

    def _on_batch_done(self, ok: int, failed: list) -> None:
        msg = f"✅ 已导出 {ok} 份 PDF"
        if failed:
            msg += f"\n\n失败 {len(failed)} 份：\n" + "\n".join(failed[:5])
        QMessageBox.information(self, "批量导出 PDF", msg)

    def _on_batch_cancelled(self) -> None:
        QMessageBox.information(self, "批量导出 PDF", "已取消批量导出。")

    def _on_batch_failed(self, exc) -> None:
        show_error(self, exc, "批量导出 PDF 失败，请检查 LibreOffice 是否可用。", title="批量导出 PDF 失败", prefix="批量导出 PDF")

    def _on_batch_thread_finished(self) -> None:
        if self._batch_thread is not self.sender():
            return  # 过期线程的 finished 信号，忽略以免覆盖新线程状态
        self.batch_pdf_btn.setEnabled(True)
        self.progress_bar.hide()
        self.cancel_btn.hide()
        self._batch_thread = None
