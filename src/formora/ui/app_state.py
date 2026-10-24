"""跨页面共享的应用状态：当前任务、模板、数据、映射、输出。"""
from __future__ import annotations

from dataclasses import dataclass, field

from formora.core.models import DataSource, FieldMapping, ReportTask, TemplateInfo
from formora.services.config import Config


@dataclass
class AppState:
    config: Config
    task: ReportTask | None = None
    template: TemplateInfo | None = None
    data: DataSource | None = None
    mappings: list[FieldMapping] = field(default_factory=list)
    output_path: str | None = None

    def new_task(self, name: str = "新任务"):
        from formora.services.history import now_str
        self.task = ReportTask(name=name, template_path=None, created_at=now_str())
        self.template = None
        self.data = None
        self.mappings = []
        self.output_path = None
        return self.task