"""数据读取：CSV / XLSX / TXT / Markdown / PDF。

- CSV/XLSX 用 pandas 读取为表格型数据。
- TXT/MD 作为纯文本数据。
- PDF 用 pdfplumber 提取文本（仅机器生成 PDF 可靠；扫描件需 OCR，属可选增强）。
"""
from __future__ import annotations

from pathlib import Path

from .errors import DocumentFormatError, ExternalDependencyError, UserError
from .models import DataSource

# 常见中文编码，依次尝试避免乱码
_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "latin-1")


def _read_text_auto(path: Path) -> str:
    """按常见编码读取文本，返回首个可解码的内容。"""
    for enc in _ENCODINGS:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="latin-1")


def read_data(path: str | Path) -> DataSource:
    path = Path(path)
    if not path.exists():
        raise UserError(f"数据文件不存在: {path}")
    suffix = path.suffix.lower()
    kind_map = {
        ".csv": "csv",
        ".xlsx": "xlsx",
        ".xls": "xlsx",
        ".txt": "txt",
        ".md": "md",
        ".markdown": "md",
        ".pdf": "pdf",
    }
    kind = kind_map.get(suffix, "unknown")
    if kind == "unknown":
        raise DocumentFormatError(
            f"不支持的数据格式 {suffix or '无后缀'}。支持 CSV/XLSX/TXT/Markdown/PDF。"
        )

    if kind in ("csv", "xlsx"):
        return _read_tabular(path, kind)
    if kind == "pdf":
        return _read_pdf(path)
    return _read_text(path, kind)


def _read_tabular(path: Path, kind: str) -> DataSource:
    import io

    try:
        import pandas as pd
    except ImportError:
        raise ExternalDependencyError("pandas 未安装，无法读取表格数据。")
    try:
        if kind == "csv":
            # 先按常见编码解码，避免中文乱码
            df = pd.read_csv(io.StringIO(_read_text_auto(path)))
        else:
            df = pd.read_excel(path)
    except Exception as e:
        raise DocumentFormatError(f"读取表格失败（文件可能损坏或格式异常）: {e}")

    df = df.dropna(how="all")  # 去掉全空行
    columns = [str(c).strip() for c in df.columns]
    rows = df.where(df.notna(), None).to_dict("records")
    # 标准化 key
    norm_rows = []
    for r in rows:
        norm_rows.append({str(k).strip(): v for k, v in r.items()})
    ds = DataSource(path=path, kind=kind, columns=columns, rows=norm_rows)
    ds.summary = f"{len(rows)} 行 × {len(columns)} 列"
    return ds


def _read_text(path: Path, kind: str) -> DataSource:
    text = _read_text_auto(path)
    ds = DataSource(path=path, kind=kind, text=text.strip())
    ds.summary = f"{len(text)} 字符文本"
    return ds


def _read_pdf(path: Path) -> DataSource:
    try:
        import pdfplumber
    except ImportError:
        raise ExternalDependencyError("pdfplumber 未安装，无法读取 PDF。")
    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = []
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
            text = "\n\n".join(pages)
    except Exception as e:
        raise DocumentFormatError(f"读取 PDF 失败: {e}")
    ds = DataSource(path=path, kind="pdf", text=text.strip())
    ds.summary = f"{len(pdf.pages)} 页 PDF 文本"
    return ds