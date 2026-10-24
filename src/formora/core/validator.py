"""校验：检查缺失字段、空数据、异常格式，输出明确问题清单。"""
from __future__ import annotations

from pathlib import Path

from .models import FieldMapping, TemplateInfo, ValidationIssue

CORE_FIELDS = ["实验名称", "实验目的", "实验环境", "实验步骤", "实验数据",
               "实验结果", "问题分析", "实验结论", "结论"]


def validate_mappings(
    mappings: list[FieldMapping],
    skip_image_placeholders: set[str] | None = None,
) -> list[ValidationIssue]:
    """校验映射。skip_image_placeholders 为自动图表占位符集合，这些字段
    由「自动生成图表」处理，未手动选图不算错误。"""
    skip = skip_image_placeholders or set()
    issues: list[ValidationIssue] = []
    for m in mappings:
        if m.source_type == "column" and not m.source_column:
            issues.append(ValidationIssue(
                severity="warning", field=m.template_field,
                message="字段未关联数据列，生成时将为空。"))
        if m.source_type == "constant" and not m.constant_value:
            issues.append(ValidationIssue(
                severity="warning", field=m.template_field,
                message="字段为常量但未填写值，生成时将为空。"))
        if m.source_type == "image":
            if m.template_field in skip:
                # 自动图表占位符：由图表生成处理，跳过「未选择图片」误报
                pass
            elif not m.value:
                issues.append(ValidationIssue(
                    severity="error", field=m.template_field,
                    message="图片字段未选择图片，报告将缺少该插图。"))
            elif not Path(str(m.value)).exists():
                issues.append(ValidationIssue(
                    severity="error", field=m.template_field,
                    message=f"图片文件不存在：{m.value}"))
        if m.needs_confirmation:
            issues.append(ValidationIssue(
                severity="warning", field=m.template_field,
                message="该字段为 AI 补充且标记「待确认」，请在导出前人工核对内容。"))
    return issues


def validate_context(context: dict, template: TemplateInfo,
                     image_placeholders: set[str] | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    image_placeholders = image_placeholders or set()
    for field in CORE_FIELDS:
        if field in template.sections:
            val = context.get(field, "")
            if val is None or str(val).strip() == "":
                issues.append(ValidationIssue(
                    severity="warning", field=field,
                    message=f"核心字段「{field}」为空，请补充内容。"))
    # 所有占位符是否都有值（图片占位符跳过）
    for ph in template.placeholders:
        if ph in image_placeholders:
            continue
        v = context.get(ph)
        if v is None or (isinstance(v, str) and not v.strip()):
            issues.append(ValidationIssue(
                severity="info", field=ph,
                message=f"占位符「{ph}」没有值。"))
    return issues