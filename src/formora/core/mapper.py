"""字段映射：把模板占位符与数据列/常量/文本关联起来。

自动映射策略（归一化名称匹配）：
- 去掉空格、下划线、括号；
- 小写化；
- 常见同义：姓名/学生姓名/名字；学号/ID/student_id 等。
"""

from __future__ import annotations

import re

from .models import DataSource, FieldMapping, TemplateInfo

_ALIASES = {
    "姓名": ["姓名", "学生姓名", "名字", "name", "studentname"],
    "学号": ["学号", "学生学号", "id", "studentid", "number", "学号id"],
    "班级": ["班级", "专业班级", "class", "classname"],
    "日期": ["日期", "时间", "date", "time", "年月日"],
    "学院": ["学院", "院系", "college", "department"],
    "指导教师": ["指导教师", "老师", "教师", "teacher", "instructor"],
    "成绩": ["成绩", "分数", "grade", "score"],
}


def _normalize(s: str) -> str:
    return re.sub(r"[\s_\-()（）]", "", s or "").lower()


def auto_map(template: TemplateInfo, data: DataSource | None) -> list[FieldMapping]:
    """根据模板占位符与数据列自动生成映射。"""
    mappings: list[FieldMapping] = []
    columns = data.columns if data and data.is_tabular else []
    norm_cols = {_normalize(c): c for c in columns}

    # 预定义字段：优先匹配别名
    known = {}
    for canonical, aliases in _ALIASES.items():
        for alias in aliases:
            known[_normalize(alias)] = canonical

    for ph in template.placeholders:
        np = _normalize(ph)
        matched_col = None
        # 1) 精确列名匹配
        if np in norm_cols:
            matched_col = norm_cols[np]
        # 2) 别名匹配
        elif np in known:
            canonical = known[np]
            # 在列中找该 canonical 的别名对应列
            for alias in _ALIASES[canonical]:
                if _normalize(alias) in norm_cols:
                    matched_col = norm_cols[_normalize(alias)]
                    break
        # 3) 包含匹配：某列名包含占位符名，或占位符名包含某列名
        if matched_col is None:
            for col in norm_cols.values():
                if np and (np in col or col in np):
                    matched_col = col
                    break

        if matched_col:
            mappings.append(
                FieldMapping(
                    template_field=ph,
                    source_type="column",
                    source_column=matched_col,
                    required=True,
                )
            )
        else:
            mappings.append(
                FieldMapping(
                    template_field=ph, source_type="constant", constant_value=""
                )
            )

    return mappings


def apply_ai_suggestions(
    mappings: list[FieldMapping],
    ai_result: list[dict],
    protected_fields: set[str] | None = None,
) -> tuple[int, list[str], list[str]]:
    """把 AI 抽取结果写回字段映射，但跳过用户已手动填写的字段。

    与 ai_workflow.apply_ai_results 的区别：
    - 用户手动填写/编辑过的字段（protected_fields）优先保留，AI 建议不覆盖；
    - 图片字段始终跳过；
    - 返回被保留的用户字段名，便于 UI 提示「已保留手动填写」。

    返回：(applied 字段数, confirmed 字段名列表["字段名（待确认）"], 保留的用户字段名列表)
    """
    protected = set(protected_fields or ())
    by_field = {m.template_field: m for m in mappings}
    applied = 0
    confirmed: list[str] = []
    preserved: list[str] = []
    for item in ai_result:
        fname = item.get("field", "")
        value = item.get("value", "")
        needs = bool(item.get("needs_confirmation"))
        m = by_field.get(fname)
        if m is None or m.source_type == "image":
            continue
        if fname in protected:
            preserved.append(fname)
            continue
        m.source_type = "constant"
        m.constant_value = value
        m.source = item.get("source", "")
        m.needs_confirmation = needs
        confirmed.append(f"{fname}" + ("（待确认）" if needs else ""))
        applied += 1
    return applied, confirmed, preserved


def fallback_to_rule_mapping(
    mappings: list[FieldMapping],
    template: TemplateInfo | None,
    data: DataSource | None,
    protected_fields: set[str] | None = None,
) -> tuple[int, list[str]]:
    """AI 映射失败时自动回退到规则自动映射，保证用户不被阻塞。

    只更新未被用户手动修改、且非图片的字段；用户手动填写的映射保持不变。
    返回：(回退更新字段数, 字段名列表)
    """
    protected = set(protected_fields or ())
    if not template:
        return 0, []
    rule_by_field = {m.template_field: m for m in auto_map(template, data)}
    restored = 0
    fields: list[str] = []
    for m in mappings:
        if m.template_field in protected or m.source_type == "image":
            continue
        r = rule_by_field.get(m.template_field)
        if r is None:
            continue
        m.source_type = r.source_type
        m.source_column = r.source_column
        m.constant_value = r.constant_value
        m.value = None
        m.source = ""
        m.needs_confirmation = False
        restored += 1
        fields.append(m.template_field)
    return restored, fields


def _format_value(v) -> str:
    """把数据值格式化为适合进报告文本的字符串。

    - 整数 float（85.0）→ "85"
    - 科学计数法小值（1e-05）→ 普通小数
    - pandas datetime / 日期 → YYYY-MM-DD
    - 百分比字符串（"85%"）保持不变
    - 其它 None / 普通值 → 原样字符串
    """
    if v is None:
        return ""
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        # 科学计数法小值（如 1e-05）：转普通小数
        s = str(v)
        if "e" in s or "E" in s:
            # 用足够多的小数位，去掉尾随 0
            return f"{v:.10f}".rstrip("0").rstrip(".")
        return s
    if isinstance(v, int):
        return str(v)
    # 处理 pandas Timestamp（datetime 子类）
    import datetime as _dt

    if isinstance(v, _dt.datetime):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, _dt.date):
        return v.strftime("%Y-%m-%d")
    return str(v)


def resolve_values(
    mappings: list[FieldMapping], row: dict | None = None
) -> dict[str, object]:
    """根据映射与当前数据行解析出模板上下文。"""
    context: dict[str, object] = {}
    for m in mappings:
        if m.source_type == "column" and m.source_column is not None:
            v = (row or {}).get(m.source_column)
            context[m.template_field] = _format_value(v)
        elif m.source_type == "constant":
            context[m.template_field] = m.constant_value or ""
        elif m.source_type == "text":
            context[m.template_field] = m.value or ""
        else:
            context[m.template_field] = m.value if m.value is not None else ""
    return context
