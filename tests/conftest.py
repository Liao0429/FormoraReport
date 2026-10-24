"""pytest 共享夹具与测试基础设施。

职责：
- 兜底把项目 src 目录加入 sys.path（pytest.ini 的 ``pythonpath = src`` 已处理，
  这里再兜底一次，保证任意方式启动 pytest 都能直接 import formora）。
- 提供共享样例文件夹具：模板/数据路径，缺失时自动生成。
- 提供隔离的 Config 工厂与完整任务状态构造助手，避免各测试文件重复样板代码。
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
TEMPLATE = SAMPLES_DIR / "实验报告模板.docx"
DATA = SAMPLES_DIR / "实验数据.csv"


@pytest.fixture(scope="session", autouse=True)
def ensure_samples():
    """确保样例存在（仅缺时生成，避免改动已跟踪的样例文件）。"""
    scripts = PROJECT_ROOT / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from make_samples import make_csv, make_template

    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    if not TEMPLATE.exists():
        make_template(TEMPLATE)
    if not DATA.exists():
        make_csv(DATA)
    yield


@pytest.fixture
def samples_dir() -> Path:
    return SAMPLES_DIR


@pytest.fixture
def template_path() -> Path:
    return TEMPLATE


@pytest.fixture
def data_path() -> Path:
    return DATA


@pytest.fixture
def make_config(tmp_path):
    """返回写入临时目录的 Config 工厂；可指定 output_dir。"""
    from formora.services.config import Config

    def _make(output_dir: str | None = None) -> Config:
        cfg = Config(tmp_path / "config.json")
        if output_dir is not None:
            cfg.set("output_dir", output_dir)
        return cfg

    return _make


@pytest.fixture
def make_task_state(tmp_path, template_path, data_path):
    """构造带真实样例的完整任务状态（输出与历史均隔离在临时目录）。

    返回的 SimpleNamespace 与 report_service 各函数期望的 state 兼容：
    config / template / data / mappings / task。
    """
    from formora.core import data_reader, mapper, template_parser
    from formora.core.models import ReportTask
    from formora.services.config import Config

    def _make(
        name: str = "测试任务",
        output_dir: str | None = None,
        fill_constants: bool = True,
    ) -> SimpleNamespace:
        cfg = Config(tmp_path / "config.json")
        cfg.set("output_dir", output_dir or str(tmp_path / "out"))
        template = template_parser.parse_template(template_path)
        data = data_reader.read_data(data_path)
        mappings = mapper.auto_map(template, data)
        if fill_constants:
            constants = {
                "实验名称": f"{name}实验",
                "实验目的": "验证服务层全流程",
                "实验环境": "本机",
                "实验步骤": "1. 映射；2. 生成",
                "实验结果": "成功",
                "问题分析": "无",
                "实验结论": "结论",
            }
            for m in mappings:
                if m.source_type == "constant" and m.template_field in constants:
                    m.constant_value = constants[m.template_field]
        task = ReportTask(name=name, template_path=template_path)
        return SimpleNamespace(
            config=cfg,
            template=template,
            data=data,
            mappings=mappings,
            task=task,
        )

    return _make


@pytest.fixture(scope="session")
def qapp():
    """创建（或复用）一个 offscreen 的 QApplication，供 UI 辅助模块测试使用。"""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    return app
