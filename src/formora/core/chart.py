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

# 无配置时的默认图表样式（保持历史行为不变）
_DEFAULT_STYLE = {
    "colors": ["#4a90d9", "#e67e22", "#27ae60", "#e74c3c", "#8e44ad", "#16a085"],
    "figsize": (6.4, 4.0),
    "dpi": 150,
    "grid": True,
    "font_size": 10,
}

# matplotlib 蓝橙序列（设置页「蓝橙」颜色主题）
BLUE_ORANGE_COLORS = ["#1f77b4", "#ff7f0e"]

# 显式注入的图表配置源（Config 实例或 dict）；None 时自动读取全局配置
_chart_config = None


def set_chart_config(config) -> None:
    """设置图表配置源（Config 实例或 dict）。传 None 恢复为自动读取全局配置。"""
    global _chart_config
    _chart_config = config


def _load_chart_config() -> dict:
    """读取 chart 样式配置字典；无配置/读取失败时返回 {}。"""
    cfg = _chart_config
    if cfg is None:
        try:
            from formora.services.config import Config

            cfg = Config()
        except Exception:
            cfg = {}
    try:
        if hasattr(cfg, "get") or isinstance(cfg, dict):
            chart_cfg = cfg.get("chart") or {}
        else:
            chart_cfg = {}
    except Exception:
        chart_cfg = {}
    return chart_cfg if isinstance(chart_cfg, dict) else {}


def _chart_cfg_from(config) -> dict:
    """把调用方传入的配置（Config 实例/dict/None）归一化为 chart 配置字典。"""
    if config is None:
        return _load_chart_config()
    try:
        if hasattr(config, "get") or isinstance(config, dict):
            chart_cfg = config.get("chart") or {}
        else:
            chart_cfg = {}
    except Exception:
        chart_cfg = {}
    return chart_cfg if isinstance(chart_cfg, dict) else {}


def _resolve_style(chart_cfg: dict) -> dict:
    """把 chart 配置解析为实际样式；缺失项回退到无配置时的默认样式。"""
    style = dict(_DEFAULT_STYLE)
    if not isinstance(chart_cfg, dict):
        return style
    colors = chart_cfg.get("colors")
    if isinstance(colors, (list, tuple)) and colors:
        style["colors"] = [str(c) for c in colors]
    figsize = chart_cfg.get("figsize")
    if isinstance(figsize, (list, tuple)) and len(figsize) == 2:
        try:
            style["figsize"] = (float(figsize[0]), float(figsize[1]))
        except (TypeError, ValueError):
            pass
    dpi = chart_cfg.get("dpi")
    if dpi:
        try:
            style["dpi"] = int(dpi)
        except (TypeError, ValueError):
            pass
    if "grid" in chart_cfg:
        style["grid"] = bool(chart_cfg["grid"])
    font_size = chart_cfg.get("font_size")
    if font_size:
        try:
            style["font_size"] = float(font_size)
        except (TypeError, ValueError):
            pass
    return style


def _require_mpl() -> None:
    if not _MPL_OK:
        raise ExternalDependencyError("matplotlib 不可用，无法生成图表。")


def _normalize_x_values(x_values) -> list:
    """x 轴值归一化：若全部为数值（int/float 且非 bool）则保留数值类型，
    使 matplotlib 使用数值/时间轴，避免不等间隔的时间点被等距扭曲；
    否则转字符串作为类别轴。"""
    import numbers

    vals = list(x_values)
    if vals and all(
        isinstance(v, numbers.Real) and not isinstance(v, bool) for v in vals
    ):
        return vals
    return [str(v) for v in vals]


def _render_chart(
    kind: str,
    x_values,
    y_values,
    output_png,
    title,
    x_label,
    y_label,
    config=None,
) -> Path:
    """绘制折线/柱状图并保存为 PNG。kind 取值 'line' | 'bar'。

    config 为可选图表配置（Config 实例或 dict，含 chart 段）；不传时自动读取
    全局配置，仍无配置则保持历史默认样式。
    """
    _require_mpl()
    if len(x_values) != len(y_values) or not x_values:
        raise DocumentFormatError("图表数据列长度不一致或为空。")
    output = Path(output_png)
    output.parent.mkdir(parents=True, exist_ok=True)
    chart_cfg = _chart_cfg_from(config)
    style = _resolve_style(chart_cfg)
    figsize, dpi = style["figsize"], style["dpi"]
    colors = style["colors"]
    grid_enabled = style["grid"]
    font_size = style["font_size"]
    explicit_colors = bool(chart_cfg.get("colors"))
    prev_font_size = plt.rcParams.get("font.size")
    plt.rcParams["font.size"] = font_size
    try:
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        xs = _normalize_x_values(x_values)
        if kind == "bar":
            ax.bar(xs, list(y_values), color=colors[0])
            if grid_enabled:
                ax.grid(True, axis="y", linestyle="--", alpha=0.5)
        else:
            plot_kwargs = {"color": colors[0]} if explicit_colors else {}
            ax.plot(xs, list(y_values), marker="o", linewidth=2, **plot_kwargs)
            if grid_enabled:
                ax.grid(True, linestyle="--", alpha=0.5)
        ax.set_title(title)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        fig.tight_layout()
        try:
            fig.savefig(str(output))
        finally:
            plt.close(fig)
    finally:
        plt.rcParams["font.size"] = prev_font_size
    return output


def generate_line_chart(
    x_values: list,
    y_values: list,
    output_png: str | Path,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    config=None,
) -> Path:
    return _render_chart(
        "line", x_values, y_values, output_png, title, x_label, y_label, config
    )


def generate_bar_chart(
    x_values: list,
    y_values: list,
    output_png: str | Path,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    config=None,
) -> Path:
    return _render_chart(
        "bar", x_values, y_values, output_png, title, x_label, y_label, config
    )


def generate_multi_line_chart(
    x_values: list,
    series: dict[str, list],
    output_png: str | Path,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    config=None,
) -> Path:
    """绘制多系列折线图（每列一条线 + 图例）。series: {系列名: y值列表}。

    config 为可选图表配置（Config 实例或 dict，含 chart 段）；不传时自动读取
    全局配置，仍无配置则保持历史默认样式。
    """
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
    chart_cfg = _chart_cfg_from(config)
    style = _resolve_style(chart_cfg)
    figsize, dpi = style["figsize"], style["dpi"]
    colors = style["colors"]
    grid_enabled = style["grid"]
    font_size = style["font_size"]
    prev_font_size = plt.rcParams.get("font.size")
    plt.rcParams["font.size"] = font_size
    try:
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        xs = _normalize_x_values(x_values)
        for i, (name, ys) in enumerate(series.items()):
            ax.plot(
                xs,
                list(ys),
                marker="o",
                linewidth=2,
                label=name,
                color=colors[i % len(colors)],
            )
        if grid_enabled:
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
    finally:
        plt.rcParams["font.size"] = prev_font_size
    return output
