"""数据读取：CSV / XLSX / TXT / Markdown / PDF。

- CSV/XLSX 用 pandas 读取为表格型数据。
- TXT/MD 作为纯文本数据。
- PDF 用 pdfplumber 提取文本（仅机器生成 PDF 可靠；扫描件需 OCR，属可选增强）。
"""

from __future__ import annotations

import math

from pathlib import Path

from .errors import DocumentFormatError, ExternalDependencyError, UserError
from .models import DataSource

# 常见中文编码，依次尝试避免乱码
_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "latin-1")

# 大文件阈值：超过该字节数的 CSV 进入预览模式（只读前 _PREVIEW_ROWS 行）
LARGE_FILE_BYTES = 20 * 1024 * 1024
_PREVIEW_ROWS = 200
_CSV_CHUNK_SIZE = 10_000
_HEADER_PROBE_BYTES = 256 * 1024


def _read_text_auto(path: Path) -> tuple[str, str]:
    """按常见编码读取文本，返回 (内容, 实际使用的编码)。"""
    for enc in _ENCODINGS:
        try:
            return path.read_text(encoding=enc), enc
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="latin-1"), "latin-1"


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


def _to_native(v):
    """把 numpy 标量 / Timestamp / NaN 转成 Python 原生可序列化类型。

    pandas 缺失值（pd.NA / pd.NaT）与 numpy NaN 统一转 None，
    避免 pd.NA 原样返回导致后续 JSON 序列化失败。
    """
    if v is None:
        return None
    # dtype=str 读取时绝大多数值是 str/int，直接返回，避免每值 import pandas
    if isinstance(v, (str, int, bool)):
        return v
    try:
        import pandas as pd

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


def _detect_csv_header(path: Path) -> tuple[str, str | None]:
    """只读文件头 256KB，探测 CSV 编码与分隔符，返回 (encoding, sep)。

    大文件预览模式使用，避免整文件解码与嗅探的开销。
    """
    with path.open("rb") as f:
        raw = f.read(_HEADER_PROBE_BYTES)
    if not raw:
        raise DocumentFormatError("文件内容为空，没有可读取的数据。")
    text = None
    encoding = "latin-1"
    for enc in _ENCODINGS:
        # 256KB 截断可能切在多字节字符中间，导致整段解码失败；
        # 依次尝试去掉末尾 1-3 字节再解码，避免把 utf-8 文件误判为 latin-1。
        for cut in range(4):
            sample = raw if cut == 0 else raw[:-cut]
            try:
                text = sample.decode(enc)
                encoding = enc
                break
            except UnicodeDecodeError:
                continue
        if text is not None:
            break
    if text is None:
        text = raw.decode("latin-1", errors="replace")
        encoding = "latin-1"
    return encoding, _sniff_delimiter(text)


def _read_csv_preview(path, encoding: str, sep: str | None):
    """大文件预览：只读取前 _PREVIEW_ROWS 行（dtype=str 保持原始文本）。"""
    import pandas as pd

    if sep is not None:
        return pd.read_csv(
            path, nrows=_PREVIEW_ROWS, sep=sep, encoding=encoding, dtype=str
        )
    return pd.read_csv(
        path,
        nrows=_PREVIEW_ROWS,
        sep=None,
        engine="python",
        encoding=encoding,
        dtype=str,
    )


def _count_csv_rows(path, encoding: str, sep: str | None) -> int:
    """精确统计 CSV 数据行数（usecols=[0] 只读首列，避免全表载入内存）。"""
    import pandas as pd

    if sep is not None:
        df = pd.read_csv(path, sep=sep, encoding=encoding, dtype=str, usecols=[0])
    else:
        df = pd.read_csv(
            path,
            sep=None,
            engine="python",
            encoding=encoding,
            dtype=str,
            usecols=[0],
        )
    return len(df)


def iter_csv_rows(
    path,
    encoding: str = "utf-8-sig",
    sep: str = ",",
    chunksize: int = _CSV_CHUNK_SIZE,
):
    """流式迭代 CSV 全部数据行（chunksize 分批，dtype=str），每次 yield 一个 dict。

    大文件批量生成时使用，避免把整表载入内存。
    """
    import pandas as pd

    reader = pd.read_csv(
        path,
        sep=sep,
        encoding=encoding,
        dtype=str,
        chunksize=chunksize,
    )
    for chunk in reader:
        columns = _clean_columns(chunk)
        mapping = {raw: clean for raw, clean in zip(chunk.columns, columns)}
        for rec in chunk.to_dict(orient="records"):
            yield {mapping[k]: _to_native(v) for k, v in rec.items()}


def load_row(
    path,
    encoding: str = "utf-8-sig",
    sep: str = ",",
    row_index: int = 0,
) -> dict:
    """跳过前 row_index 条数据行，只读取指定的一行（0 为第一条数据行）。"""
    import pandas as pd

    df = pd.read_csv(
        path,
        sep=sep,
        encoding=encoding,
        dtype=str,
        header=0,
        skiprows=lambda i: 0 < i <= row_index,
        nrows=1,
    )
    if df.empty:
        raise IndexError(f"行索引越界: {row_index}")
    rec = df.to_dict(orient="records")[0]
    columns = _clean_columns(df)
    mapping = {raw: clean for raw, clean in zip(df.columns, columns)}
    return {mapping[k]: _to_native(v) for k, v in rec.items()}


def _clean_columns(df) -> list[str]:
    """列名 strip 并处理重复：strip 后同名列追加 _2/_3，避免静默覆盖丢数据。"""
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
    return columns


def _df_to_rows(df, columns: list[str]) -> list[dict]:
    """用 to_dict(orient='records') 快速把 DataFrame 转为 [{列名: 原生值}]。

    相比逐行 iterrows 快一个数量级；列名映射保证清洗后的列名生效。
    """
    mapping = {raw: clean for raw, clean in zip(df.columns, columns)}
    return [
        {clean: _to_native(rec[raw]) for raw, clean in mapping.items()}
        for rec in df.to_dict(orient="records")
    ]


def _read_tabular(path: Path, kind: str) -> DataSource:
    import io

    try:
        import pandas as pd
    except ImportError:
        raise ExternalDependencyError("pandas 未安装，无法读取表格数据。")

    try:
        if kind == "csv":
            if path.stat().st_size >= LARGE_FILE_BYTES:
                # 大文件：预览模式，只读前 _PREVIEW_ROWS 行；row_count 为全量精确值
                encoding, sep = _detect_csv_header(path)
                df = _read_csv_preview(path, encoding, sep)
                truncated = True
                row_count = _count_csv_rows(path, encoding, sep)
            else:
                # 小文件：走原全量逻辑（整文件解码 + 嗅探分隔符）
                text, encoding = _read_text_auto(path)
                if not text.strip():
                    raise DocumentFormatError("文件内容为空，没有可读取的数据。")
                sep = _sniff_delimiter(text)
                if sep is not None:
                    df = pd.read_csv(io.StringIO(text), sep=sep)
                else:
                    # 嗅探失败（如字段数不齐/多行引号等模糊情况）回退原逻辑，保持兼容行为。
                    df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
                truncated = False
                row_count = 0  # 全量读取后以实际行数回填
        else:
            df = pd.read_excel(path)
            encoding = ""
            sep = ""
            truncated = False
            row_count = 0
    except pd.errors.EmptyDataError:
        raise DocumentFormatError("文件内容为空，没有可读取的数据。")
    except DocumentFormatError:
        raise
    except Exception as e:
        raise DocumentFormatError(f"读取表格失败（文件可能损坏或格式异常）: {e}")

    df = df.dropna(how="all")  # 去掉全空行
    columns = _clean_columns(df)
    rows = _df_to_rows(df, columns)
    if kind == "csv" and truncated:
        row_count = max(row_count, len(rows))
        summary = (
            f"{row_count} 行 × {len(columns)} 列"
            f"（文件过大，仅载入前 {len(rows)} 行预览）"
        )
    else:
        row_count = len(rows)
        summary = f"{row_count} 行 × {len(columns)} 列"

    ds = DataSource(
        path=path,
        kind=kind,
        columns=columns,
        rows=rows,
        summary=summary,
        row_count=row_count,
        truncated=truncated,
        encoding=encoding,
        sep=sep or "",
    )
    return ds


def _read_text(path: Path, kind: str) -> DataSource:
    text, encoding = _read_text_auto(path)
    ds = DataSource(path=path, kind=kind, text=text.strip(), encoding=encoding)
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
