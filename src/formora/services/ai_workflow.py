"""AI 辅助工作流服务：把 AI 抽取结果落地到字段映射。

把原本写在 mapping_page 里的业务编排抽成纯函数，供桌面端 UI、
以及未来的后端 API（小程序/App 前端透传 AI 请求）复用。
"""
from __future__ import annotations

from typing import Any

from formora.core.models import FieldMapping


def apply_ai_results(
    mappings: list[FieldMapping],
    ai_result: list[dict],
) -> tuple[int, list[str]]:
    """把 AI 抽取结果写回字段映射。

    规则：
    - 只处理非图片字段（图片字段保持原样）；
    - 对匹配到的字段：source_type 置为 constant，值取 AI 内容；
    - 记录来源依据（source）与「待确认」标记（needs_confirmation）。

    返回：(applied 字段数, confirmed 字段名列表["字段名（待确认）"或"字段名"])
    """
    by_field = {m.template_field: m for m in mappings}
    applied = 0
    confirmed: list[str] = []
    for item in ai_result:
        fname = item.get("field", "")
        value = item.get("value", "")
        needs = bool(item.get("needs_confirmation"))
        m = by_field.get(fname)
        if m is None or m.source_type == "image":
            continue
        m.source_type = "constant"
        m.constant_value = value
        m.source = item.get("source", "")
        m.needs_confirmation = needs
        confirmed.append(f"{fname}" + ("（待确认）" if needs else ""))
        applied += 1
    return applied, confirmed


def build_ai_fields(mappings: list[FieldMapping]) -> list[str]:
    """构造传给 AI 的模板字段名列表（排除图片字段）。"""
    return [m.template_field for m in mappings if m.source_type != "image"]