"""图表生成：基于 matplotlib（Agg 后端，无窗口）生成实验数据图表 PNG。"""
from __future__ import annotations

from pathlib import Path

from .errors import DocumentFormatError, ExternalDependencyError

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    _MPL_OK = True
except Exception:  # pragma: no cover
    _MPL_OK = False

# 尝试加载中文字体，避免中文乱码（matplotlib 不可用时跳过）
_FONT_CANDIDATES = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS", "DejaVu Sans"]
if _MPL_OK:
    for _f in _FONT_CANDIDATES:
        try:
            font_manager.findfont(_f, fallback_to_default=False)
            plt.rcParams["font.sans-serif"] = [_f]
            break
        except Exception:
            continue
    plt.rcParams["axes.unicode_minus"] = False


def _require_mpl() -> None:
    if not _MPL_OK:
        raise ExternalDependencyError("matplotlib 不可用，无法生成图表。")


def _render_chart(kind: str, x_values, y_values, output_png, title, x_label, y_label) -> Path:
    """绘制折线/柱状图并保存为 PNG。kind 取值 'line' | 'bar'。"""
    _require_mpl()
    if len(x_values) != len(y_values) or not x_values:
        raise DocumentFormatError("图表数据列长度不一致或为空。")
    output = Path(output_png)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
    xs = list(map(str, x_values))
    if kind == "bar":
        ax.bar(xs, list(y_values), color="#4a90d9")
        ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    else:
        ax.plot(xs, list(y_values), marker="o", linewidth=2)
        ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    fig.tight_layout()
    fig.savefig(str(output))
    plt.close(fig)
    return output


def generate_line_chart(
    x_values: list,
    y_values: list,
    output_png: str | Path,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
) -> Path:
    return _render_chart("line", x_values, y_values, output_png, title, x_label, y_label)


def generate_bar_chart(
    x_values: list,
    y_values: list,
    output_png: str | Path,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
) -> Path:
    return _render_chart("bar", x_values, y_values, output_png, title, x_label, y_label)