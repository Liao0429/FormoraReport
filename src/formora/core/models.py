"""核心数据结构。"""

from __future__ import annotations

# 任务书要求的核心章节字段（models 与 validator 共用，避免漂移）
CORE_FIELDS = [
    "实验名称",
    "实验目的",
    "实验环境",
    "实验步骤",
    "实验数据",
    "实验结果",
    "问题分析",
    "实验结论",
    "结论",
]

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

FieldSourceType = Literal["column", "constant", "text", "chart", "image"]


@dataclass
class TableInfo:
    """模板中的表格信息。"""

    index: int
    header: list[str]  # 表头（若可识别）
    row_count: int
    col_count: int
    sample: list[list[str]]


@dataclass
class TemplateInfo:
    """解析模板后得到的结构化信息。"""

    path: Path
    placeholders: list[str] = field(default_factory=list)  # 检测到的 {{var}}
    loop_blocks: list[str] = field(default_factory=list)  # {% for %} 变量
    sections: dict[str, str] = field(default_factory=dict)  # 章节名 -> 首个段落文本
    tables: list[TableInfo] = field(default_factory=list)
    has_images: bool = False
    has_header_footer: bool = False

    @property
    def missing_core_fields(self) -> list[str]:
        """任务书要求的核心字段中，模板缺失哪些。"""
        found = {c for c in CORE_FIELDS if c in self.sections}
        return [c for c in CORE_FIELDS if c not in found]


@dataclass
class DataSource:
    """导入的数据源。"""

    path: Path
    kind: Literal["csv", "xlsx", "txt", "md", "pdf", "unknown"]
    columns: list[str] = field(default_factory=list)  # 表格型数据列名
    rows: list[dict[str, Any]] = field(default_factory=list)  # 表格型数据行
    text: str = ""  # 文本型数据（TXT/MD/PDF）
    summary: str = ""

    @property
    def is_tabular(self) -> bool:
        return self.kind in ("csv", "xlsx")


@dataclass
class FieldMapping:
    """模板字段到数据来源的映射。"""

    template_field: str
    source_type: FieldSourceType = "column"
    source_column: str | None = None
    constant_value: str | None = None
    value: Any = None  # 预览/确认后的实际值
    required: bool = False
    # AI 来源追踪（可选，无 AI 模式为空）
    source: str = ""  # AI 依据说明（文件名/段落/表格）
    needs_confirmation: bool = False  # True 表示 AI 无依据，需人工确认

    def resolved_value(self) -> Any:
        if self.source_type == "column":
            return self.value
        if self.source_type == "constant":
            return self.constant_value
        return self.value


@dataclass
class TaskLog:
    level: Literal["info", "warning", "error", "success"]
    category: Literal["user", "format", "dependency", "bug", "system"]
    message: str


@dataclass
class ReportTask:
    """一次报告生成任务。"""

    name: str
    template_path: Path
    data_source: DataSource | None = None
    mappings: list[FieldMapping] = field(default_factory=list)
    status: Literal["draft", "mapping", "generating", "preview", "done", "failed"] = (
        "draft"
    )
    logs: list[TaskLog] = field(default_factory=list)
    output_path: Path | None = None
    created_at: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def log(self, level, category, message):
        self.logs.append(TaskLog(level=level, category=category, message=message))


@dataclass
class ValidationIssue:
    severity: Literal["error", "warning", "info"]
    field: str
    message: str
