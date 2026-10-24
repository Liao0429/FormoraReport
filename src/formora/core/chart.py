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
# 候选覆盖 Windows（微软雅黑/黑体/宋体）与 Linux/服务端（Noto Sans CJK）等平台
_FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "SimSun",
    "Arial Unicode MS",
    "Noto Sans CJK SC",
    "Noto Sans CJK",
    "WenQuanYi Zen Hei",
    "DejaVu Sans",
]
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


def _render_chart(
    kind: str, x_values, y_values, output_png, title, x_label, y_label
) -> Path:
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
    try:
        fig.savefig(str(output))
    finally:
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
    return _render_chart(
        "line", x_values, y_values, output_png, title, x_label, y_label
    )


def generate_bar_chart(
    x_values: list,
    y_values: list,
    output_png: str | Path,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
) -> Path:
    return _render_chart("bar", x_values, y_values, output_png, title, x_label, y_label)


def generate_multi_line_chart(
    x_values: list,
    series: dict[str, list],
    output_png: str | Path,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
) -> Path:
    """绘制多系列折线图（每列一条线 + 图例）。series: {系列名: y值列表}。"""
    _require_mpl()
    if not x_values or not series:
        raise DocumentFormatError("多系列图表数据为空。")
    n = len(x_values)
    for name, ys in series.items():
        if len(ys) != n:
            raise DocumentFormatError(
                f"图表数据列长度不一致：{name} ({len(ys)}) != x ({n})"
            )
    output = Path(output_png)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
    xs = list(map(str, x_values))
    colors = ["#4a90d9", "#e67e22", "#27ae60", "#e74c3c", "#8e44ad", "#16a085"]
    for i, (name, ys) in enumerate(series.items()):
        ax.plot(
            xs,
            list(ys),
            marker="o",
            linewidth=2,
            label=name,
            color=colors[i % len(colors)],
        )
    ax.grid(True, linestyle="--", alpha=0.5)
    if title:
        ax.set_title(title)
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    if len(series) > 1:
        ax.legend()
    fig.tight_layout()
    try:
        fig.savefig(str(output))
    finally:
        plt.close(fig)
    return output
