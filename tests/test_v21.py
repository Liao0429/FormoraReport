"""2.1 新增逻辑测试：图片字段校验、版本化输出、自动图表开关。"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from formora.core import data_reader, mapper, template_parser, validator
from formora.core.models import FieldMapping, ReportTask
from formora.services import report_service
from formora.services.config import Config

SAMPLES = Path(__file__).resolve().parent.parent / "tests" / "samples"
TEMPLATE = SAMPLES / "实验报告模板.docx"
DATA = SAMPLES / "实验数据.csv"


class TestImageValidation:
    def test_missing_image_is_error(self):
        mappings = [FieldMapping(template_field="截图", source_type="image", value="")]
        issues = validator.validate_mappings(mappings)
        assert any(i.severity == "error" and "未选择图片" in i.message for i in issues)

    def test_nonexistent_image_is_error(self):
        mappings = [FieldMapping(
            template_field="截图", source_type="image",
            value="C:/不存在/xx.png")]
        issues = validator.validate_mappings(mappings)
        assert any(i.severity == "error" and "不存在" in i.message for i in issues)

    def test_existing_image_no_error(self, tmp_path):
        img = tmp_path / "a.png"
        img.write_bytes(b"fake-png")
        mappings = [FieldMapping(template_field="截图", source_type="image", value=str(img))]
        issues = validator.validate_mappings(mappings)
        assert not any(i.field == "截图" for i in issues)


class TestVersionedOutput:
    def test_single_output_has_timestamp(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        cfg.set("output_dir", str(tmp_path / "out"))
        template = template_parser.parse_template(TEMPLATE)
        data = data_reader.read_data(DATA)
        mappings = mapper.auto_map(template, data)
        constants = {"实验名称": "x", "实验目的": "y", "实验环境": "z",
                     "实验步骤": "s", "实验结果": "r", "问题分析": "p", "实验结论": "c"}
        for m in mappings:
            if m.source_type == "constant" and m.template_field in constants:
                m.constant_value = constants[m.template_field]
        task = ReportTask(name="版本化", template_path=TEMPLATE)
        state = SimpleNamespace(config=cfg, template=template, data=data,
                                mappings=mappings, task=task)
        out = report_service.generate_single(state)
        assert out.exists()
        # 文件名应含时间戳
        assert "_输出_" in out.name

    def test_batch_uses_timestamped_dir(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        cfg.set("output_dir", str(tmp_path / "out"))
        template = template_parser.parse_template(TEMPLATE)
        data = data_reader.read_data(DATA)
        mappings = mapper.auto_map(template, data)
        task = ReportTask(name="批量版本化", template_path=TEMPLATE)
        state = SimpleNamespace(config=cfg, template=template, data=data,
                                mappings=mappings, task=task)
        results, errors = report_service.generate_batch(state, auto_chart=True)
        assert len(results) == len(data.rows)
        assert errors == []
        batch_dir = Path(state.last_batch_dir)
        assert batch_dir.exists()
        # 目录含时间戳段
        assert batch_dir.parent.name == "批量版本化_批量"


class TestAutoChartFlag:
    def test_auto_chart_false_no_image_var(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        cfg.set("output_dir", str(tmp_path / "out"))
        template = template_parser.parse_template(TEMPLATE)
        data = data_reader.read_data(DATA)
        mappings = mapper.auto_map(template, data)
        task = ReportTask(name="无图表", template_path=TEMPLATE)
        state = SimpleNamespace(config=cfg, template=template, data=data,
                                mappings=mappings, task=task)
        image_vars = report_service.collect_image_vars(state, auto_chart_enabled=False)
        assert not any("图表" in v or "chart" in k for k, v in image_vars.items())

    def test_auto_chart_true_creates_chart(self, tmp_path):
        cfg = Config(tmp_path / "config.json")
        cfg.set("output_dir", str(tmp_path / "out"))
        template = template_parser.parse_template(TEMPLATE)
        data = data_reader.read_data(DATA)
        mappings = mapper.auto_map(template, data)
        task = ReportTask(name="有图表", template_path=TEMPLATE)
        state = SimpleNamespace(config=cfg, template=template, data=data,
                                mappings=mappings, task=task)
        image_vars = report_service.collect_image_vars(state, auto_chart_enabled=True)
        assert image_vars  # 应有图表图片