"""验证 2.1.1 修复：批量生成每份报告只含当前行数据，而非整表。"""
import sys
from pathlib import Path
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from docx import Document
from formora.core import data_reader, mapper, template_parser
from formora.core.models import ReportTask
from formora.services.config import Config
from formora.services import report_service

SAMPLES = Path(__file__).resolve().parent.parent / "tests" / "samples"
TEMPLATE = SAMPLES / "实验报告模板.docx"
DATA = SAMPLES / "实验数据.csv"


def _make_state(tmp_path):
    cfg = Config(tmp_path / "config.json")
    cfg.set("output_dir", str(tmp_path / "out"))
    template = template_parser.parse_template(TEMPLATE)
    data = data_reader.read_data(DATA)
    mappings = mapper.auto_map(template, data)
    constants = {"实验名称": "批量语义", "实验目的": "验证", "实验环境": "本机",
                 "实验步骤": "步骤", "实验结果": "结果", "问题分析": "无", "实验结论": "结论"}
    for m in mappings:
        if m.source_type == "constant" and m.template_field in constants:
            m.constant_value = constants[m.template_field]
    task = ReportTask(name="批量语义", template_path=TEMPLATE)
    return SimpleNamespace(config=cfg, template=template, data=data,
                            mappings=mappings, task=task)


class TestBatchDataRowsSemantics:
    def test_each_report_contains_only_its_own_row(self, tmp_path):
        """批量生成时，每份报告的 data_rows 循环只含当前行。"""
        state = _make_state(tmp_path)
        results, errors = report_service.generate_batch(state, auto_chart=False)
        assert errors == []
        assert len(results) == len(state.data.rows)

        for i, docx_path in enumerate(results):
            doc = Document(docx_path)
            texts = " ".join(p.text for p in doc.paragraphs)
            # 当前行数据应出现
            row = state.data.rows[i]
            assert str(row.get("项目")) in texts
            # 其它行数据不应出现（批量语义：每份只含当前行）
            for j, other in enumerate(state.data.rows):
                if j != i:
                    assert str(other.get("项目")) not in texts, (
                        f"报告 {i} 不应包含第 {j} 行数据 {other.get('项目')}")

    def test_single_uses_resolve_values_with_text_type(self, tmp_path):
        """批量路径复用 mapper.resolve_values，text 类型字段也能渲染。"""
        state = _make_state(tmp_path)
        # 把一个现有模板占位符改为 text 类型（手动填写的自由文本）
        for m in state.mappings:
            if m.template_field == "实验结论":
                m.source_type = "text"
                m.value = "这是text类型结论"
        results, errors = report_service.generate_batch(state, auto_chart=False)
        assert errors == []
        doc = Document(results[0])
        texts = " ".join(p.text for p in doc.paragraphs)
        assert "这是text类型结论" in texts