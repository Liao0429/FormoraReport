"""报告生成：使用 docxtpl 把上下文渲染进 DOCX 模板，保留原有格式/表格/图片。

- 文本占位符：{{ 变量 }} 直接替换。
- 图片插入：通过 InlineImage 包装图片路径，替换到 {{ 变量 }} 处。
- 表格循环：模板中已有 {% for row in rows %}...{% endfor %} 语法，由 docxtpl 处理。
"""

from __future__ import annotations

from pathlib import Path

from .errors import DocumentFormatError, ExternalDependencyError
from .models import TemplateInfo
from .template_parser import parse_template


def _render_image(tpl, var: str, img_path: str) -> object:
    """把图片包装成 docxtpl InlineImage 对象。"""
    from docx.shared import Cm
    from docxtpl import InlineImage

    img = Path(img_path)
    if not img.exists():
        raise ExternalDependencyError(f"图片文件不存在: {img}")
    try:
        # 宽度默认 14cm，保持比例
        return InlineImage(tpl, str(img), width=Cm(14))
    except Exception as e:
        raise DocumentFormatError(f"插入图片 {img} 失败: {e}")


def generate_report(
    template_path: str | Path,
    context: dict,
    output_path: str | Path,
    image_vars: dict[str, str] | None = None,
    template_info: TemplateInfo | None = None,
) -> Path:
    """把 context（占位符->值）渲染进模板，输出到 output_path。

    image_vars: {占位符名: 图片路径}，这些占位符将被替换为图片。
    template_info: 已解析的模板信息。传入可避免重复解析，批量生成时显著提速。
    """
    template_path = Path(template_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        from docxtpl import DocxTemplate
    except ImportError:
        raise ExternalDependencyError("docxtpl 未安装，无法生成报告。")

    # 校验模板（优先使用调用方缓存的解析结果）
    info = template_info or parse_template(template_path)
    if not info.placeholders and not info.loop_blocks:
        raise DocumentFormatError(
            "模板中未检测到任何 {{占位符}} 或 {% for %} 循环块。"
            "请在 Word 模板中用 {{字段名}} 标记待填写位置后重试。"
        )

    try:
        tpl = DocxTemplate(str(template_path))
    except Exception as e:
        raise DocumentFormatError(f"无法加载模板: {e}")

    render_context = dict(context)
    for var, img_path in (image_vars or {}).items():
        render_context[var] = _render_image(tpl, var, img_path)

    try:
        tpl.render(render_context)
    except Exception as e:
        raise DocumentFormatError(f"模板渲染失败（可能是占位符不匹配）: {e}")

    try:
        tpl.save(str(output))
    except Exception as e:
        raise DocumentFormatError(f"保存输出文档失败: {e}")
    return output
