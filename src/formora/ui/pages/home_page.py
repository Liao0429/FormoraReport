"""首页：新建任务 + 最近任务（双击可恢复历史任务）。"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from formora.core import data_reader, template_parser
from formora.core.errors import UserError
from formora.core.models import FieldMapping, TaskLog
from formora.services.history import get_task, load_history
from formora.ui.errors import show_error
from formora.ui.widgets import Card, primary_button, secondary_button

_LOGGER = logging.getLogger(__name__)


class HomePage(QWidget):
    def __init__(self, state, navigate):
        super().__init__()
        self.state = state
        self.navigate = navigate
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        title = QLabel("FormoraReport")
        title.setObjectName("AppTitle")
        lay.addWidget(title)
        sub = QLabel("实验报告自动填写工具：导入模板 → 填写字段 → 一键生成")
        sub.setObjectName("HintText")
        lay.addWidget(sub)

        # 快捷操作
        actions = Card("快速开始")
        row = QHBoxLayout()
        new_btn = primary_button("＋ 新建任务")
        new_btn.clicked.connect(lambda: self.navigate("import"))
        template_btn = secondary_button("导入模板")
        template_btn.clicked.connect(lambda: self.navigate("import"))
        demo_btn = secondary_button("🎓 使用示例模板体验")
        demo_btn.setToolTip(
            "自动生成一份示例实验报告模板和数据，载入后即可体验完整流程"
        )
        demo_btn.clicked.connect(self._load_demo)
        row.addWidget(new_btn)
        row.addWidget(template_btn)
        row.addWidget(demo_btn)
        row.addStretch(1)
        actions.add_layout(row)
        lay.addWidget(actions)

        # 最近任务（双击可恢复历史任务，继续编辑或生成）
        recent = Card("最近任务")
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._restore_task)
        self.list_widget.setToolTip("双击历史任务可恢复并继续编辑")
        recent.add_widget(self.list_widget)
        lay.addWidget(recent, 1)

        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        entries = load_history(limit=10)
        if not entries:
            self.list_widget.addItem("暂无历史记录，点击「新建任务」开始。")
            return
        for e in entries:
            name = e.get("name", "未命名任务")
            status = e.get("status", "")
            out = e.get("output_path") or ""
            item = QListWidgetItem(f"{name}  [{status}]  {out}")
            item.setData(Qt.ItemDataRole.UserRole, e.get("id"))
            self.list_widget.addItem(item)

    def _restore_task(self, item):
        """双击历史任务：恢复其数据源/模板/映射到 state 并跳转对应页面。"""
        if item is None:
            return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if not task_id:
            return
        entry = get_task(task_id)
        if entry is None:
            show_error(
                self,
                UserError("历史记录不存在或已被清理。"),
                "无法找到该历史任务，它可能已被清理。",
                title="恢复失败",
                logger=_LOGGER,
                prefix="恢复历史任务",
            )
            return
        try:
            self._apply_history(entry)
        except Exception as e:  # noqa: BLE001 - 统一弹友好提示
            show_error(
                self,
                e,
                "恢复历史任务时发生意外错误，请稍后重试。",
                title="恢复失败",
                logger=_LOGGER,
                prefix="恢复历史任务",
            )

    def _apply_history(self, entry: dict) -> None:
        """把单条历史记录恢复到 state，并跳转到映射页或生成页。

        - 模板/数据源/映射齐全：完整恢复后进入映射页（可继续编辑或生成）；
        - 缺少映射：仍恢复模板和数据源，提示用户重新映射；
        - 模板缺失：只恢复数据源，提示重新导入模板。
        """
        state = self.state
        state.new_task(name=entry.get("name", "未命名任务"))
        task = state.task
        task.id = entry.get("id", task.id)
        task.created_at = entry.get("created_at", "")
        task.status = entry.get("status", "draft")
        tpl_path = entry.get("template_path")
        task.template_path = Path(tpl_path) if tpl_path else None
        out_path = entry.get("output_path")
        task.output_path = Path(out_path) if out_path else None

        logs: list[TaskLog] = []
        for l in entry.get("logs", []):
            try:
                logs.append(
                    TaskLog(
                        level=l.get("level", "info"),
                        category=l.get("category", "system"),
                        message=l.get("message", ""),
                    )
                )
            except Exception:
                continue
        task.logs = logs

        # 模板：文件存在则重新解析，否则视为缺失
        if tpl_path and Path(tpl_path).exists():
            state.template = template_parser.parse_template(tpl_path)
        else:
            state.template = None

        # 数据源：文件存在则重新读取，否则置空
        ds_path = entry.get("data_source")
        if ds_path and Path(ds_path).exists():
            ds = data_reader.read_data(ds_path)
            state.data = ds
            task.data_source = ds
        else:
            state.data = None
            task.data_source = None

        # 映射：旧版历史可能未保存完整映射，此时置空让映射页自动匹配
        raw_mappings = entry.get("mappings")
        if isinstance(raw_mappings, list) and raw_mappings:
            restored: list[FieldMapping] = []
            for m in raw_mappings:
                if not isinstance(m, dict) or not m.get("template_field"):
                    continue
                source_type = m.get("source_type")
                if source_type not in ("column", "constant", "text", "chart", "image"):
                    source_type = "column"
                restored.append(
                    FieldMapping(
                        template_field=m["template_field"],
                        source_type=source_type,
                        source_column=m.get("source_column"),
                        constant_value=m.get("constant_value"),
                        value=m.get("value"),
                        required=bool(m.get("required", False)),
                        source=m.get("source", ""),
                        needs_confirmation=bool(m.get("needs_confirmation", False)),
                    )
                )
            state.mappings = restored
        else:
            state.mappings = []

        # 缺失项统计，用于友好提示
        missing = []
        if tpl_path and not Path(tpl_path).exists():
            missing.append("模板文件")
        if ds_path and not Path(ds_path).exists():
            missing.append("数据文件")
        if not state.mappings:
            missing.append("映射信息")

        if state.template is None:
            show_error(
                self,
                UserError("模板文件不存在或已被移动，仅恢复数据源。"),
                "该历史任务的部分文件已丢失（模板不存在），已尽力恢复数据源，"
                "请重新导入模板后再生成。",
                title="部分恢复",
                level="warning",
                logger=_LOGGER,
                prefix="恢复历史任务",
            )
            self.navigate("import")
            return

        if not state.mappings:
            show_error(
                self,
                UserError("该历史记录缺少映射信息，请重新映射。"),
                "该历史任务未保存映射信息，已恢复模板和数据源，"
                "请在映射页重新映射字段后生成。",
                title="部分恢复",
                level="warning",
                logger=_LOGGER,
                prefix="恢复历史任务",
            )
            self.navigate("mapping")
            return

        if missing:
            show_error(
                self,
                UserError("部分历史文件缺失。"),
                "该历史任务已恢复模板与映射，但以下内容缺失："
                + "、".join(missing)
                + "。请检查文件后继续。",
                title="部分恢复",
                level="warning",
                logger=_LOGGER,
                prefix="恢复历史任务",
            )

        self.navigate("mapping")

    def _load_demo(self):
        """载入示例模板+数据并跳转映射页，让新手一键体验完整流程。

        支持两种环境：
        - 打包版（frozen）：从 PyInstaller 资源目录（sys._MEIPASS/samples）读取示例文件；
        - 源码运行：从 tests/samples 读取，缺失时现场生成。
        """
        from pathlib import Path

        from PySide6.QtWidgets import QMessageBox

        try:
            import sys

            from formora.core import data_reader, template_parser

            tpl: Path
            data: Path
            if getattr(sys, "frozen", False):
                # 打包版：资源在 sys._MEIPASS（onedir 是 _internal）
                base = Path(getattr(sys, "_MEIPASS", Path(sys.argv[0]).parent))
                samples_dir = base / "samples"
                tpl = samples_dir / "实验报告模板.docx"
                data = samples_dir / "实验数据.csv"
            else:
                # 源码运行：优先用 tests/samples，缺失则现场生成
                root = Path(__file__).resolve().parent.parent.parent.parent.parent
                samples_dir = root / "tests" / "samples"
                samples_dir.mkdir(parents=True, exist_ok=True)
                tpl = samples_dir / "实验报告模板.docx"
                data = samples_dir / "实验数据.csv"
                if not tpl.exists() or not data.exists():
                    sys.path.insert(0, str(root / "scripts"))
                    from make_samples import make_csv, make_template

                    if not tpl.exists():
                        make_template(tpl)
                    if not data.exists():
                        make_csv(data)

            info = template_parser.parse_template(tpl)
            ds = data_reader.read_data(data)
            self.state.new_task(name="示例实验报告")
            self.state.task.template_path = tpl
            self.state.template = info
            self.state.data = ds
            self.state.task.data_source = ds
            self.navigate("mapping")
        except Exception as e:
            QMessageBox.warning(self, "加载示例失败", f"无法加载示例模板：{e}")
