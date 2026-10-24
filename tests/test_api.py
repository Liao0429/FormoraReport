"""API 层测试：健康检查、模板解析、数据读取、报告生成与下载。

使用 FastAPI TestClient（httpx），不启动真实服务。
需要 tests/samples/ 下的样例模板与数据。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from formora.api import app

SAMPLES = Path(__file__).resolve().parent / "samples"
TEMPLATE = SAMPLES / "实验报告模板.docx"
DATA = SAMPLES / "实验数据.csv"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def template_fid(client: TestClient) -> str:
    with TEMPLATE.open("rb") as f:
        r = client.post("/api/template/parse", files={"file": ("模板.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert r.status_code == 200, r.text
    return r.json()["file_id"]


@pytest.fixture(scope="module")
def data_fid(client: TestClient) -> str:
    with DATA.open("rb") as f:
        r = client.post("/api/data/read", files={"file": ("数据.csv", f, "text/csv")})
    assert r.status_code == 200, r.text
    return r.json()["file_id"]


class TestHealth:
    def test_health(self, client: TestClient):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestTemplateParse:
    def test_parse_template(self, client: TestClient, template_fid: str):
        assert template_fid
        r = client.get("/api/health")  # 模板已解析成功即通过
        assert r.status_code == 200

    def test_reject_non_docx(self, client: TestClient):
        r = client.post("/api/template/parse", files={"file": ("bad.txt", b"hello", "text/plain")})
        assert r.status_code == 400


class TestDataRead:
    def test_read_csv(self, client: TestClient, data_fid: str):
        assert data_fid


class TestGenerateReport:
    def test_generate_with_constant(self, client: TestClient, template_fid: str):
        """只用常量映射生成报告，不依赖数据文件。"""
        req = {
            "template_file_id": template_fid,
            "mappings": [
                {"template_field": "实验名称", "source_type": "constant", "constant_value": "API 测试实验"},
            ],
        }
        r = client.post("/api/report/generate", json=req)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["task_id"]
        # 下载
        dl = client.get(data["download_url"])
        assert dl.status_code == 200
        assert dl.headers["content-type"].startswith("application/vnd.openxmlformats")
        assert len(dl.content) > 0

    def test_generate_with_data_row(self, client: TestClient, template_fid: str, data_fid: str):
        req = {
            "template_file_id": template_fid,
            "data_file_id": data_fid,
            "row_index": 0,
            "mappings": [
                {"template_field": "实验名称", "source_type": "constant", "constant_value": "数据行实验"},
            ],
        }
        r = client.post("/api/report/generate", json=req)
        assert r.status_code == 200, r.text

    def test_generate_bad_template(self, client: TestClient):
        req = {"template_file_id": "not_exist", "mappings": []}
        r = client.post("/api/report/generate", json=req)
        assert r.status_code == 404

    def test_generate_row_out_of_range(self, client: TestClient, template_fid: str, data_fid: str):
        req = {
            "template_file_id": template_fid,
            "data_file_id": data_fid,
            "row_index": 9999,
            "mappings": [],
        }
        r = client.post("/api/report/generate", json=req)
        assert r.status_code == 400


class TestReportText:
    def test_report_text(self, client: TestClient, template_fid: str):
        req = {
            "template_file_id": template_fid,
            "mappings": [
                {"template_field": "实验名称", "source_type": "constant", "constant_value": "文本抽取测试"},
            ],
        }
        r = client.post("/api/report/generate", json=req)
        task_id = r.json()["task_id"]
        t = client.post(f"/api/report/{task_id}/text")
        assert t.status_code == 200, t.text
        assert "文本抽取测试" in t.json()["text"]