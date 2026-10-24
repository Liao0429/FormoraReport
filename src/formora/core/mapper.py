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
            for norm_c, col in norm_cols.items():
                if np and (np in col or col in np):
                    matched_col = col
                    break

        if matched_col:
            mappings.append(FieldMapping(
                template_field=ph, source_type="column", source_column=matched_col, required=True))
        else:
            mappings.append(FieldMapping(
                template_field=ph, source_type="constant", constant_value=""))

    return mappings


def resolve_values(mappings: list[FieldMapping], row: dict | None = None) -> dict[str, object]:
    """根据映射与当前数据行解析出模板上下文。"""
    context: dict[str, object] = {}
    for m in mappings:
        if m.source_type == "column" and m.source_column is not None:
            v = (row or {}).get(m.source_column)
            context[m.template_field] = "" if v is None else str(v)
        elif m.source_type == "constant":
            context[m.template_field] = m.constant_value or ""
        elif m.source_type == "text":
            context[m.template_field] = m.value or ""
        else:
            context[m.template_field] = m.value if m.value is not None else ""
    return context