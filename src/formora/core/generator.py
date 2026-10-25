"""报告生成：使用 docxtpl 把上下文渲染进 DOCX 模板，保留原有格式/表格/图片。

- 文本占位符：{{ 变量 }} 直接替换。
- 图片插入：通过 InlineImage 包装图片路径，替换到 {{ 变量 }} 处。
- 表格循环：模板中已有 {% for row in rows %}...{% endfor %} 语法，由 docxtpl 处理。

性能：docxtpl 在 render() 时才读取模板 zip 并解析 Document，是批量生成的主要
开销。这里增加按「模板路径 + 修改时间 + 大小」为键的解析缓存：批量生成时同一
模板只解析一次，后续每份报告通过深拷贝缓存的文档骨架获得独立的未渲染模板。
模板被修改后键变化，自动重新解析。
"""

from __future__ import annotations

import copy
import io
import threading
from collections import OrderedDict
from pathlib import Path

from jinja2 import Environment

from .errors import DocumentFormatError, ExternalDependencyError
from .models import TemplateInfo
from .template_parser import parse_template

# 模板解析缓存容量：最多缓存 32 个不同模板，超出按 LRU 淘汰。
_TEMPLATE_CACHE_MAX = 32
# 缓存 key = (规范化模板路径, mtime_ns, size)；value 为 _TemplateCacheEntry。
# 批量生成在 QThread 中运行，多个任务可能并发，因此用 RLock 保护字典。
_template_cache: "OrderedDict[tuple[str, int, int], _TemplateCacheEntry]" = (
    OrderedDict()
)
_template_cache_lock = threading.RLock()
# 共享 jinja2 Environment：docxtpl 每次 render 都会用同一段模板 XML 调用
# from_string()，默认会重新解析并编译模板。jinja2 的 from_string 不走自带缓存，
# 因此这里用子类按源码缓存编译后的 Template 对象，批量生成时每个模板部件
# 只编译一次。缓存只读复用 Template（render 不修改模板），多线程安全。
_JINJA_ENV = None
# 编译模板缓存上限：不同源码片段超过该数量时按 LRU 淘汰，防止长期运行膨胀
_JINJA_CACHE_MAX = 256


class _CachingJinjaEnvironment(Environment):
    """在 from_string 上按源码缓存编译结果，避免 docxtpl 重复编译。"""

    def __init__(self):
        super().__init__()
        self._formora_template_cache: OrderedDict = OrderedDict()

    def from_string(self, source, globals=None, template_class=None):
        # 仅对 docxtpl 的调用形态（不带 globals/template_class）使用缓存
        if globals is None and template_class is None:
            tpl = self._formora_template_cache.get(source)
            if tpl is not None:
                self._formora_template_cache.move_to_end(source)
                return tpl
        tpl = super().from_string(source, globals=globals, template_class=template_class)
        if globals is None and template_class is None:
            self._formora_template_cache[source] = tpl
            while len(self._formora_template_cache) > _JINJA_CACHE_MAX:
                self._formora_template_cache.popitem(last=False)
        return tpl


def _get_jinja_env() -> "_CachingJinjaEnvironment":
    """返回进程级共享的 jinja2 Environment（惰性创建，线程安全）。"""
    global _JINJA_ENV
    if _JINJA_ENV is None:
        _JINJA_ENV = _CachingJinjaEnvironment()
    return _JINJA_ENV


class _TemplateCacheEntry:
    """一份模板的解析结果：原始字节 + 未渲染的 Document 骨架。

    new_template() 深拷贝骨架并返回一个独立的 DocxTemplate，可安全并发渲染；
    缓存的骨架本身从不被修改，因此多线程共享 entry 是安全的。
    """

    __slots__ = ("_raw", "_doc")

    def __init__(self, raw: bytes, doc) -> None:
        self._raw = raw
        self._doc = doc

    def new_template(self):
        """返回一个从原始骨架出发的全新 DocxTemplate（未渲染状态）。"""
        from docxtpl import DocxTemplate

        tpl = DocxTemplate(io.BytesIO(self._raw))
        # docxtpl 的 render() 会原地改写 self.docx，不能复用已渲染对象；
        # 深拷贝骨架保证每份报告都从原始未渲染状态开始。
        tpl.docx = copy.deepcopy(self._doc)
        tpl.is_rendered = False
        tpl.is_saved = False
        return tpl


def clear_template_cache() -> None:
    """清空模板解析缓存（测试与模板批量变更时使用）。"""
    with _template_cache_lock:
        _template_cache.clear()


def _load_template_entry(template_path: Path) -> _TemplateCacheEntry:
    """读取模板字节并解析一次，构造缓存条目（调用方需持有锁）。"""
    try:
        raw = template_path.read_bytes()
        from docx import Document

        doc = Document(io.BytesIO(raw))
    except Exception as e:
        raise DocumentFormatError(f"无法加载模板: {e}") from e
    return _TemplateCacheEntry(raw, doc)


def _get_cached_template(template_path: Path):
    """按 (路径, mtime, size) 获取模板，返回独立的未渲染 DocxTemplate。

    缓存命中时直接深拷贝骨架；未命中时读取文件并解析一次后入缓存。
    模板文件缺失/损坏时抛出 DocumentFormatError（与旧行为一致）。
    """
    try:
        stat = template_path.stat()
    except OSError as e:
        raise DocumentFormatError(f"无法加载模板: {e}") from e
    key = (str(template_path.resolve()), stat.st_mtime_ns, stat.st_size)

    with _template_cache_lock:
        entry = _template_cache.get(key)
        if entry is None:
            # 未命中：持锁解析一次，避免并发任务重复解析同一模板
            entry = _load_template_entry(template_path)
            _template_cache[key] = entry
        _template_cache.move_to_end(key)
        while len(_template_cache) > _TEMPLATE_CACHE_MAX:
            _template_cache.popitem(last=False)
    # 深拷贝放到锁外执行：骨架不可变，拷贝可并发
    return entry.new_template()


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
        tpl = _get_cached_template(template_path)
    except DocumentFormatError:
        raise
    except Exception as e:
        raise DocumentFormatError(f"无法加载模板: {e}")

    render_context = dict(context)
    for var, img_path in (image_vars or {}).items():
        render_context[var] = _render_image(tpl, var, img_path)

    try:
        # 共享 jinja_env：docxtpl 会按模板源码缓存编译结果，批量生成只编译一次
        tpl.render(render_context, jinja_env=_get_jinja_env())
    except Exception as e:
        raise DocumentFormatError(f"模板渲染失败（可能是占位符不匹配）: {e}")

    try:
        tpl.save(str(output))
    except Exception as e:
        raise DocumentFormatError(f"保存输出文档失败: {e}")
    return output
