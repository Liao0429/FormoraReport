"""首页：新建任务 + 最近任务。"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QVBoxLayout, QWidget

from formora.services.history import load_history
from formora.ui.widgets import Card, primary_button, secondary_button


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

        # 最近任务
        recent = Card("最近任务")
        self.list_widget = QListWidget()
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
            self.list_widget.addItem(f"{name}  [{status}]  {out}")

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
