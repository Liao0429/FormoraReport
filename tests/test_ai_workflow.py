"""AI 工作流服务测试：结果落盘映射、来源追踪、字段筛选。"""

from __future__ import annotations

from formora.core.models import FieldMapping
from formora.services.ai_workflow import apply_ai_results, build_ai_fields


def _mapping(field: str, source_type: str = "constant") -> FieldMapping:
    return FieldMapping(template_field=field, source_type=source_type)


class TestApplyAiResults:
    def test_applies_constant_values(self):
        mappings = [_mapping("实验名称"), _mapping("实验目的")]
        applied, confirmed = apply_ai_results(
            mappings,
            [
                {
                    "field": "实验名称",
                    "value": "测试实验",
                    "source": "素材.txt",
                    "needs_confirmation": False,
                },
            ],
        )
        assert applied == 1
        assert confirmed == ["实验名称"]
        assert mappings[0].source_type == "constant"
        assert mappings[0].constant_value == "测试实验"
        assert mappings[0].source == "素材.txt"
        assert mappings[0].needs_confirmation is False

    def test_confirmation_flag(self):
        mappings = [_mapping("结论")]
        _, confirmed = apply_ai_results(
            mappings,
            [
                {
                    "field": "结论",
                    "value": "待补充",
                    "source": "",
                    "needs_confirmation": True,
                },
            ],
        )
        assert confirmed == ["结论（待确认）"]
        assert mappings[0].needs_confirmation is True

    def test_skips_image_fields(self):
        mappings = [_mapping("图表", source_type="image")]
        applied, confirmed = apply_ai_results(
            mappings,
            [
                {"field": "图表", "value": "x", "needs_confirmation": False},
            ],
        )
        assert applied == 0
        assert confirmed == []
        assert mappings[0].source_type == "image"

    def test_skips_unknown_fields(self):
        mappings = [_mapping("姓名")]
        applied, confirmed = apply_ai_results(
            mappings,
            [
                {"field": "不存在的字段", "value": "x", "needs_confirmation": False},
            ],
        )
        assert applied == 0
        assert confirmed == []

    def test_empty_result(self):
        mappings = [_mapping("姓名")]
        applied, confirmed = apply_ai_results(mappings, [])
        assert applied == 0
        assert confirmed == []


class TestBuildAiFields:
    def test_excludes_images(self):
        mappings = [
            _mapping("实验名称"),
            _mapping("图表", source_type="image"),
            _mapping("截图", source_type="image"),
        ]
        assert build_ai_fields(mappings) == ["实验名称"]

    def test_empty(self):
        assert build_ai_fields([]) == []
