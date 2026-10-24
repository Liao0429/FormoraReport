"""报告生成服务：字段上下文解析、图表生成、单份/批量生成。

把原本集中在 mapping_page 里的生成逻辑抽离到这里，页面只负责 UI 交互与状态同步。
所有函数为纯逻辑（不含 Qt 依赖），便于单元测试与复用。
"""

from __future__ import annotations

from pathlib import Path

from formora.core import chart, generator, mapper
from formora.core.errors import FormoraError
from formora.services.history import record_task

# 图片字段关键字：字段名含这些完整词时按图片处理（避免「地图/图纸/图标/图形」等文本字段误判）
_IMAGE_KEYWORDS = (
    "截图",
    "图表",
    "数据图",
    "结果图",
    "图片",
    "插图",
    "实验图",
    "chart",
    "image",
    "photo",
    "screenshot",
)

# 图表占位符别名：自动图表生成后绑定到这些字段（含「图」且语义为数据图表的字段）
_CHART_KEYWORDS = (
    "图表",
    "数据图",
    "结果图",
    "曲线图",
    "柱状图",
    "折线图",
    "chart",
    "graph",
    "plot",
)

# 误判排除词：字段名包含这些词时，即使含「图」也不当作图片/图表
_NON_IMAGE_EXCLUDE = (
    "地图",
    "图纸",
    "图标",
    "图形",
    "图案",
    "图例",
    "图书",
    "图1",
    "图2",
    "图3",
    "图4",
    "图5",
    "图6",
    "图7",
    "图8",
    "图9",
    "图0",
    "图a",
    "图b",
    "图c",
    "图一",
    "图二",
)


def is_image_field(name: str) -> bool:
    """字段名是否应按图片处理（排除地图/图纸/图标等文本字段）。"""
    low = (name or "").lower()
    if any(k in low for k in _NON_IMAGE_EXCLUDE):
        return False
    return any(k in low for k in _IMAGE_KEYWORDS)


def is_chart_field(name: str) -> bool:
    """字段名是否为数据图表占位符（自动图表可插入）。"""
    low = (name or "").lower()
    if any(k in low for k in _NON_IMAGE_EXCLUDE):
        return False
    return any(k in low for k in _CHART_KEYWORDS)


def materials_text(state) -> str:
    """汇总当前任务可用作 AI 素材的文本（文本型全文 + 表格型前 50 行）。"""
    data = state.data
    if not data:
        return ""
    parts: list[str] = []
    if data.text:
        parts.append(data.text)
    if data.rows:
        for r in data.rows[:50]:
            parts.append("；".join(f"{k}={v}" for k, v in r.items()))
    return "\n".join(parts)


def resolve_context(state, row: dict | None = None) -> dict:
    """根据映射与当前数据行解析模板渲染上下文。

    图片字段在上下文中置 None，由 image_vars 通过 InlineImage 注入；
    表格型数据额外注入 data_rows 供 {% for %} 循环块使用。
    """
    ctx = mapper.resolve_values(state.mappings, row=row)
    for m in state.mappings:
        if m.source_type == "image":
            ctx[m.template_field] = None
    if state.data and state.data.is_tabular:
        # 传入 row 时（生成当前行/批量），data_rows 只含当前行，与批量语义一致；
        # 未传 row 时（如仅校验/预览），注入全表供模板循环展示
        ctx["data_rows"] = (
            [_format_rows([row])[0]]
            if row is not None
            else _format_rows(state.data.rows)
        )
    return ctx


def _chart_placeholders(mappings) -> list[str]:
    return [m.template_field for m in mappings if is_chart_field(m.template_field)]


def auto_chart(state) -> str | None:
    """若数据为表格型且含数值列，自动生成折线图 PNG，返回图片路径；否则返回 None。"""
    data = state.data
    if not data or not data.rows or not data.columns:
        return None
    # 数值列检测：允许文本数字（"12.5"）与百分比（"85%"）——先尝试数值转换
    numeric_cols = []
    for col in data.columns:
        vals = [r.get(col) for r in data.rows]
        if not vals:
            continue
        parsed = True
        for v in vals:
            if v is None:
                continue
            s = str(v).strip().replace("%", "")
            try:
                float(s)
            except (ValueError, TypeError):
                parsed = False
                break
        if parsed and any(v is not None for v in vals):
            numeric_cols.append(col)
    if not numeric_cols:
        return None

    # 轴启发式：含时间/日期/序号语义的列优先作 x 轴；否则首个非数值列作 x
    _X_HINTS = ("时间", "日期", "时刻", "序号", "编号", "time", "date", "s", "min", "h")
    x_col = None
    for col in data.columns:
        low = col.lower()
        if any(h in low for h in _X_HINTS):
            x_col = col
            break
    if x_col is None:
        x_col = next((c for c in data.columns if c != numeric_cols[0]), None)
    y_col = next((c for c in numeric_cols if c != x_col), None) or numeric_cols[0]

    xs = []
    ys = []
    for i, r in enumerate(data.rows):
        xv = r.get(x_col, i + 1)
        xs.append(str(xv) if xv is not None else str(i + 1))
        yv = r.get(y_col)
        if yv is not None:
            s = str(yv).strip().replace("%", "")
            ys.append(float(s))
    if not ys:
        return None
    out_dir = _output_dir(state)
    img = out_dir / f"{sanitize_filename(state.task.name)}_图表.png"
    try:
        chart.generate_line_chart(
            xs, ys, img, title=f"{y_col} 数据图", x_label=x_col or "序号", y_label=y_col
        )
        return str(img)
    except Exception as e:
        # 记录失败原因，避免用户以为图表已插入（H6）
        try:
            import logging

            logging.getLogger("formora").warning("自动图表生成失败: %s", e)
            if hasattr(state, "task") and state.task is not None:
                state.task.log("warning", "bug", f"自动图表生成失败: {e}")
        except Exception:
            pass
        return None


def collect_image_vars(state, auto_chart_enabled: bool) -> dict[str, str]:
    """收集 {占位符: 图片路径}：显式绑定的图片字段 + 自动生成的图表。"""
    image_vars: dict[str, str] = {}
    for m in state.mappings:
        if m.source_type == "image" and m.value:
            image_vars[m.template_field] = m.value
    if auto_chart_enabled:
        img = auto_chart(state)
        if img:
            for ph in _chart_placeholders(state.mappings):
                image_vars[ph] = img
    return image_vars


def image_placeholders(state, auto_chart_enabled: bool) -> set[str]:
    """返回在渲染上下文中应视为图片的占位符集合（校验时跳过）。"""
    s = {m.template_field for m in state.mappings if m.source_type == "image"}
    if auto_chart_enabled:
        s.update(_chart_placeholders(state.mappings))
    return s


def _drop_uncovered_image_fields(context: dict, mappings, image_vars: dict) -> None:
    """把未注入图片的图片字段从渲染上下文移除，避免 docxtpl 渲染出字面量 None。

    当图片字段没有绑定图片、且自动图表未生成时，image_vars 不含该字段，
    而 context 里是 None，jinja 会输出 "None"。这里直接 pop，让占位符保持原样空白。
    """
    covered = set(image_vars.keys())
    for m in mappings:
        if m.source_type == "image" and m.template_field in context:
            if m.template_field not in covered:
                context.pop(m.template_field, None)


def _output_dir(state) -> Path:
    out_dir = Path(state.config.get("output_dir") or "").expanduser()
    if not out_dir.is_absolute() and out_dir == Path("."):
        # 配置为空串时 Path("") == WindowsPath('.')，回退到默认 Documents 目录
        from formora.services.config import OUTPUT_DEFAULT_DIR

        out_dir = OUTPUT_DEFAULT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _format_rows(rows: list[dict]) -> list[dict]:
    """把数据行格式化为适合渲染进报告的值（None→空、85.0→85、日期去时间戳）。

    避免表格循环块中 None 被 jinja 渲染成字面量 "None"，并改善数字美观度。
    """
    from formora.core.mapper import _format_value

    return [{k: _format_value(v) for k, v in row.items()} for row in rows]


def _timestamp() -> str:
    """返回紧凑时间戳，用于输出文件版本化，避免重复生成覆盖旧报告。"""
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d_%H%M%S")


_INVALID_FILENAME_CHARS = set('<>:"/\\|?*')


def sanitize_filename(name: str, fallback: str = "未命名") -> str:
    """过滤 Windows 文件名非法字符，避免任务名含 :?*<>| 等导致 OSError。"""
    cleaned = "".join(
        ch for ch in (name or "").strip() if ch not in _INVALID_FILENAME_CHARS
    )
    cleaned = cleaned.strip(" .")
    return cleaned or fallback


def _versioned_output(state, subdir: str = "", suffix: str = "输出") -> Path:
    """构造带时间戳的输出路径：<outdir>/[subdir/]<task>_<suffix>_<ts>.docx。

    若任务已生成过（state.output_path 存在），沿用其目录但追加新时间戳，
    保证每次生成都是新文件，绝不覆盖旧版。
    """
    base = _output_dir(state)
    if subdir:
        base = base / subdir
        base.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(state.task.name)
    name = f"{safe_name}_{suffix}_{_timestamp()}.docx"
    return base / name


def _auto_chart_enabled(state, explicit: bool | None = None) -> bool:
    """判断是否启用自动图表：优先显式参数，其次 state.config.auto_chart（默认 True）。"""
    if explicit is not None:
        return explicit
    return bool(state.config.get("auto_chart", True))


def generate_single(
    state, row: dict | None = None, auto_chart: bool | None = None
) -> Path:
    """生成当前行的单份报告，更新任务状态并写入历史。返回输出路径。"""
    if not state.template:
        raise FormoraError("请先解析模板。")
    context = resolve_context(state, row=row)
    image_vars = collect_image_vars(state, _auto_chart_enabled(state, auto_chart))
    _drop_uncovered_image_fields(context, state.mappings, image_vars)
    output = _versioned_output(state, suffix="输出")
    out_path = generator.generate_report(
        state.template.path,
        context,
        output,
        image_vars=image_vars,
        template_info=state.template,
    )
    state.output_path = str(out_path)
    state.task.status = "done"
    state.task.output_path = out_path
    state.task.log("success", "system", f"报告已生成: {out_path}")
    record_task(state.task)
    return out_path


def generate_batch(
    state, auto_chart: bool | None = None
) -> tuple[list[str], list[str]]:
    """按数据行批量生成报告。返回 (成功输出列表, 失败信息列表)。"""
    if not state.template:
        raise FormoraError("请先解析模板。")
    data = state.data
    if not data or not data.is_tabular or not data.rows:
        raise FormoraError("当前没有表格型数据，无法批量生成。")

    image_vars = collect_image_vars(state, _auto_chart_enabled(state, auto_chart))
    batch_root = _output_dir(state) / f"{state.task.name}_批量"
    batch_dir = batch_root / _timestamp()
    batch_dir.mkdir(parents=True, exist_ok=True)

    results: list[str] = []
    errors: list[str] = []
    for i, row in enumerate(data.rows):
        # 复用统一映射解析，避免与单份生成逻辑分叉（含 text/constant 等所有类型）
        ctx = mapper.resolve_values(state.mappings, row=row)
        for m in state.mappings:
            if m.source_type == "image":
                ctx[m.template_field] = None
        # 批量时每份报告只含当前行数据，而非整表
        ctx["data_rows"] = _format_rows([row])
        out = batch_dir / f"{sanitize_filename(state.task.name)}_第{i + 1}行.docx"
        try:
            _drop_uncovered_image_fields(ctx, state.mappings, image_vars)
            generator.generate_report(
                state.template.path,
                ctx,
                out,
                image_vars=image_vars,
                template_info=state.template,
            )
            results.append(str(out))
        except FormoraError as e:
            errors.append(f"第{i + 1}行失败: {e}")

    state.task.log(
        "success", "system", f"批量生成 {len(results)} 份，失败 {len(errors)} 份"
    )
    record_task(state.task)
    # 记录最新批次目录，供 UI 展示
    state.last_batch_dir = str(batch_dir)
    return results, errors


def batch_export_pdf(docx_paths: list[str]) -> tuple[int, list[str]]:
    """把多个 DOCX 串行转为 PDF（复用 LibreOffice 互斥锁，单份失败不中断）。

    供桌面端「批量导出 PDF」按钮与后端 API 复用。
    返回：(成功数, 失败信息列表["文件名: 错误"])
    """
    import os

    from formora.core import pdf_exporter

    ok = 0
    failed: list[str] = []
    for docx in docx_paths:
        try:
            out = os.path.splitext(docx)[0] + ".pdf"
            pdf_exporter.export_pdf(docx, out)
            ok += 1
        except FormoraError as e:
            failed.append(f"{os.path.basename(docx)}: {e}")
    return ok, failed
