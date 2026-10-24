"""PDF 导出：优先使用本地 LibreOffice 无头转换，其次 Word COM。

两者都不可用时抛出 ExternalDependencyError，并给出安装建议。
这是诚实边界：不虚拟 PDF 输出。

LibreOffice 单用户 profile 有锁，并发无头转换会互相失败，
因此用进程级文件锁串行化 LibreOffice 转换。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path

from .errors import ExternalDependencyError

_LIBREOFFICE_CANDIDATES = [
    # Windows
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    # macOS
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    # Linux（常见发行版）
    "/usr/bin/soffice",
    "/usr/lib/libreoffice/program/soffice",
    "/snap/bin/soffice",
]

# LibreOffice 转换互斥锁：同进程内串行，避免并发无头转换互相抢占 profile
_lo_lock = threading.Lock()


def find_libreoffice() -> Path | None:
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if exe:
        return Path(exe)
    for c in _LIBREOFFICE_CANDIDATES:
        if os.path.exists(c):
            return Path(c)
    return None


def has_word_com() -> bool:
    import importlib.util

    return importlib.util.find_spec("win32com") is not None


def export_pdf(docx_path: str | Path, output_pdf: str | Path) -> Path:
    """把 .docx 转为 .pdf。返回输出 PDF 路径。"""
    docx_path = Path(docx_path)
    output = Path(output_pdf)
    if not docx_path.exists():
        raise ExternalDependencyError(f"待转换的 DOCX 不存在: {docx_path}")

    lo = find_libreoffice()
    if lo is not None:
        return _export_with_libreoffice(lo, docx_path, output)

    if has_word_com():
        return _export_with_word(docx_path, output)

    raise ExternalDependencyError(
        "未找到 LibreOffice 或 Microsoft Word，无法导出 PDF。"
        "请安装 LibreOffice（免费）后重试，或先导出 DOCX 用 Word 打开。"
    )


def _export_with_libreoffice(soffice: Path, docx_path: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    # 转换到输出目录（LibreOffice 会按原名生成 pdf）
    cmd = [
        str(soffice),
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output.parent),
        str(docx_path),
    ]
    try:
        with _lo_lock:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except subprocess.CalledProcessError as e:
        raise ExternalDependencyError(
            f"LibreOffice 转换失败: {e.stderr.decode('utf-8', 'replace')}"
        )
    except subprocess.TimeoutExpired:
        raise ExternalDependencyError("LibreOffice 转换超时。")

    predicted = output.parent / (docx_path.stem + ".pdf")
    if predicted.exists():
        if predicted != output:
            shutil.move(str(predicted), str(output))
        return output
    raise ExternalDependencyError(
        f"LibreOffice 转换后未找到输出 PDF（预期 {predicted}）。"
    )


def _export_with_word(docx_path: Path, output: Path) -> Path:
    import win32com.client

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(docx_path.resolve()))
        doc.SaveAs(str(output.resolve()), FileFormat=17)  # 17 = wdFormatPDF
        doc.Close(False)
    except Exception as e:
        raise ExternalDependencyError(f"Word 转换 PDF 失败: {e}")
    finally:
        word.Quit()
    return output
