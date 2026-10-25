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
    if suffix == ".xls":
        raise DocumentFormatError(
            "暂不支持旧版 .xls 格式。请在 Excel 中将文件另存为 .xlsx 后重试。"
        )
    kind_map = {
        ".csv": "csv",
        ".tsv": "csv",
        ".xlsx": "xlsx",
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
    import math

    try:
        import pandas as pd
    except ImportError:
        raise ExternalDependencyError("pandas 未安装，无法读取表格数据。")

    def _to_native(v):
        """把 numpy 标量 / Timestamp / NaN 转成 Python 原生可序列化类型。"""
        if v is None:
            return None
        # pandas 缺失值（pd.NA / pd.NaT）与 numpy NaN 统一转 None，
        # 避免 pd.NA 原样返回导致后续 JSON 序列化失败。
        try:
            if pd.isna(v):
                return None
        except (TypeError, ValueError):
            pass
        if isinstance(v, float) and math.isnan(v):
            return None
        # pandas Timestamp / datetime
        if hasattr(v, "isoformat"):
            try:
                return v.isoformat()
            except Exception:
                pass
        # numpy 标量
        if hasattr(v, "item"):
            try:
                item = v.item()
                # np.datetime64 等 item() 后可能是 datetime/date 等非原生类型，
                # 递归再转一次；item 返回自身时停止，避免死循环。
                return _to_native(item) if item is not v else item
            except Exception:
                pass
        return v

    def _sniff_delimiter(text: str, max_lines: int = 100) -> str | None:
        """从前 max_lines 行嗅探 CSV 分隔符；无法可靠确定时返回 None。

        pandas 的 sep=None 只能配合 python 引擎使用，解析超大文件时
        python 引擎比 C 引擎慢一个数量级。这里只取前若干行嗅探，
        得到分隔符后显式传入 sep，让 pandas 走更快的 C 引擎。
        单列文件（不含任何常见分隔符）返回逗号，避免 pandas 误判。
        """
        import csv
        import re

        sample_lines = text.splitlines()[:max_lines]
        if not sample_lines:
            return None
        sample = "\n".join(sample_lines)

        def _delimiter_consistent(delim: str) -> bool:
            """各非空行字段数一致且 > 1，避免把单列文件误判成多列。"""
            counts: set[int] = set()
            for line in sample_lines:
                if not line.strip():
                    continue
                try:
                    row = next(csv.reader([line], delimiter=delim))
                except csv.Error:
                    return False
                counts.add(len(row))
            return len(counts) == 1 and counts.pop() >= 2

        # 1) 常见分隔符（逗号/分号/制表符/竖线）
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            delim = dialect.delimiter
            if _delimiter_consistent(delim):
                return delim
        except csv.Error:
            pass
        # 2) 罕见分隔符（如 ^、空格）；排除字母数字，避免单列文件误判
        try:
            dialect = csv.Sniffer().sniff(sample)
            delim = dialect.delimiter
            if not re.match(r"[A-Za-z0-9]$", delim) and _delimiter_consistent(delim):
                return delim
        except csv.Error:
            pass
        # 3) 前若干行完全不含常见分隔符 -> 单列文件，逗号是安全默认
        if not any(c in sample for c in ",;\t|"):
            return ","
        return None

    try:
        if kind == "csv":
            # 先按常见编码解码，避免中文乱码。
            text = _read_text_auto(path)
            if not text.strip():
                raise DocumentFormatError("文件内容为空，没有可读取的数据。")
            # sep=None 会强制使用 python 引擎解析整个文件，超大 CSV 时明显变慢；
            # 这里只取前 100 行嗅探分隔符再显式传入，让 pandas 使用更快的 C 引擎。
            sep = _sniff_delimiter(text)
            if sep is not None:
                df = pd.read_csv(io.StringIO(text), sep=sep)
            else:
                # 嗅探失败（如字段数不齐/多行引号等模糊情况）回退原逻辑，保持兼容行为。
                df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
        else:
            df = pd.read_excel(path)
    except pd.errors.EmptyDataError:
        raise DocumentFormatError("文件内容为空，没有可读取的数据。")
    except Exception as e:
        raise DocumentFormatError(f"读取表格失败（文件可能损坏或格式异常）: {e}")

    df = df.dropna(how="all")  # 去掉全空行
    # 列名 strip 并处理重复：strip 后同名列追加 _2/_3，避免静默覆盖丢失数据
    seen: dict[str, int] = {}
    columns: list[str] = []
    for raw in df.columns:
        name = str(raw).strip()
        if name == "nan":
            name = "未命名列"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        columns.append(name)

    # 用新列名构建 rows（避免 dict 推导 key 冲突）
    rows: list[dict] = []
    for _, row in df.iterrows():
        d = {}
        for col, name in zip(df.columns, columns):
            d[name] = _to_native(row[col])
        rows.append(d)

    ds = DataSource(path=path, kind=kind, columns=columns, rows=rows)
    ds.summary = f"{len(rows)} 行 × {len(columns)} 列"
    return ds


def _read_text(path: Path, kind: str) -> DataSource:
    text = _read_text_auto(path)
    ds = DataSource(path=path, kind=kind, text=text.strip())
    ds.summary = f"{len(ds.text)} 字符文本"
    return ds


def _read_pdf(path: Path) -> DataSource:
    try:
        import pdfplumber
    except ImportError:
        raise ExternalDependencyError("pdfplumber 未安装，无法读取 PDF。")
    text = ""
    page_count = 0
    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = []
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
            text = "\n\n".join(pages)
            # 在 with 块内取页数，避免文件关闭后再访问 pdf.pages。
            page_count = len(pdf.pages)
    except Exception as e:
        raise DocumentFormatError(f"读取 PDF 失败: {e}")
    ds = DataSource(path=path, kind="pdf", text=text.strip())
    ds.summary = f"{page_count} 页 PDF 文本"
    return ds
