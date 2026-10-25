"""API 层测试：健康检查、模板解析、数据读取、图片上传、自动映射、报告生成/下载/PDF/文本。

使用 FastAPI TestClient（httpx），不启动真实服务。
需要 tests/samples/ 下的样例模板与数据。
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from formora import api
from formora.api import app

SAMPLES = Path(__file__).resolve().parent / "samples"
TEMPLATE = SAMPLES / "实验报告模板.docx"
DATA = SAMPLES / "实验数据.csv"


@pytest.fixture()
def client():
    """每个测试独立状态：清空内存字典，避免顺序耦合。"""
    api._FILES.clear()
    api._TASKS.clear()
    api._RATE_LIMITER.clear()
    return TestClient(app)


@pytest.fixture()
def template_fid(client: TestClient) -> str:
    with TEMPLATE.open("rb") as f:
        r = client.post(
            "/api/template/parse",
            files={
                "file": (
                    "模板.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert r.status_code == 200, r.text
    return r.json()["file_id"]


@pytest.fixture()
def data_fid(client: TestClient) -> str:
    with DATA.open("rb") as f:
        r = client.post("/api/data/read", files={"file": ("数据.csv", f, "text/csv")})
    assert r.status_code == 200, r.text
    return r.json()["file_id"]


def _generate(client: TestClient, template_fid: str, mappings=None, **kw) -> dict:
    req = {"template_file_id": template_fid, "mappings": mappings or []}
    req.update(kw)
    r = client.post("/api/report/generate", json=req)
    assert r.status_code == 200, r.text
    return r.json()


class TestHealth:
    def test_health(self, client: TestClient):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "auth_enabled" in data


class TestTemplateParse:
    def test_parse_template(self, client: TestClient, template_fid: str):
        assert template_fid
        # 模板解析成功即通过（fixture 已断言 200）
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_reject_non_docx(self, client: TestClient):
        r = client.post(
            "/api/template/parse", files={"file": ("bad.txt", b"hello", "text/plain")}
        )
        assert r.status_code == 400

    def test_reject_fake_docx_magic(self, client: TestClient):
        """任意字节伪装 .docx 应被魔数校验拒绝。"""
        r = client.post(
            "/api/template/parse",
            files={
                "file": ("fake.docx", b"not a zip file", "application/octet-stream")
            },
        )
        assert r.status_code == 422

    def test_parse_empty_template(self, client: TestClient):
        r = client.post(
            "/api/template/parse",
            files={"file": ("empty.docx", b"", "application/octet-stream")},
        )
        assert r.status_code == 422


class TestDataRead:
    def test_read_csv(self, client: TestClient, data_fid: str):
        assert data_fid

    def test_read_reject_unsupported(self, client: TestClient):
        r = client.post(
            "/api/data/read",
            files={"file": ("bad.dat", b"data", "application/octet-stream")},
        )
        assert r.status_code == 422


class TestImageUpload:
    def test_upload_image(self, client: TestClient):
        # 1x1 PNG
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
        r = client.post(
            "/api/image/upload", files={"file": ("chart.png", png, "image/png")}
        )
        assert r.status_code == 200, r.text
        assert r.json()["file_id"]
        assert r.json()["size"] == len(png)

    def test_upload_image_reject_non_image(self, client: TestClient):
        r = client.post(
            "/api/image/upload", files={"file": ("note.txt", b"hello", "text/plain")}
        )
        assert r.status_code == 415

    def test_upload_image_missing_file(self, client: TestClient):
        with TEMPLATE.open("rb") as f:
            # 用模板文件冒充图片：扩展名不符应 415
            r = client.post(
                "/api/image/upload",
                files={"file": ("tpl.docx", f, "application/octet-stream")},
            )
        assert r.status_code == 415


class TestAutoMapping:
    def test_auto_mapping_with_data(
        self, client: TestClient, template_fid: str, data_fid: str
    ):
        r = client.post(
            f"/api/mapping/auto?template_file_id={template_fid}&data_file_id={data_fid}"
        )
        assert r.status_code == 200, r.text
        mappings = r.json()["mappings"]
        assert isinstance(mappings, list)
        if mappings:
            m = mappings[0]
            assert "template_field" in m
            assert "source_type" in m

    def test_auto_mapping_without_data(self, client: TestClient, template_fid: str):
        r = client.post(f"/api/mapping/auto?template_file_id={template_fid}")
        assert r.status_code == 200, r.text

    def test_auto_mapping_missing_template(self, client: TestClient):
        r = client.post("/api/mapping/auto?template_file_id=not_exist")
        assert r.status_code == 404


class TestGenerateReport:
    def test_generate_with_constant(self, client: TestClient, template_fid: str):
        r = client.post(
            "/api/report/generate",
            json={
                "template_file_id": template_fid,
                "mappings": [
                    {
                        "template_field": "实验名称",
                        "source_type": "constant",
                        "constant_value": "API 测试实验",
                    }
                ],
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["task_id"]
        dl = client.get(data["download_url"])
        assert dl.status_code == 200
        assert dl.headers["content-type"].startswith("application/vnd.openxmlformats")
        assert len(dl.content) > 0

    def test_generate_with_data_row(
        self, client: TestClient, template_fid: str, data_fid: str
    ):
        r = client.post(
            "/api/report/generate",
            json={
                "template_file_id": template_fid,
                "data_file_id": data_fid,
                "row_index": 0,
                "mappings": [
                    {
                        "template_field": "实验名称",
                        "source_type": "constant",
                        "constant_value": "数据行实验",
                    }
                ],
            },
        )
        assert r.status_code == 200, r.text

    def test_generate_bad_template(self, client: TestClient):
        r = client.post(
            "/api/report/generate",
            json={"template_file_id": "not_exist", "mappings": []},
        )
        assert r.status_code == 404

    def test_generate_row_out_of_range(
        self, client: TestClient, template_fid: str, data_fid: str
    ):
        r = client.post(
            "/api/report/generate",
            json={
                "template_file_id": template_fid,
                "data_file_id": data_fid,
                "row_index": 9999,
                "mappings": [],
            },
        )
        assert r.status_code == 400

    def test_generate_missing_column(
        self, client: TestClient, template_fid: str, data_fid: str
    ):
        """映射列不存在于数据文件 → 400。"""
        r = client.post(
            "/api/report/generate",
            json={
                "template_file_id": template_fid,
                "data_file_id": data_fid,
                "mappings": [
                    {
                        "template_field": "实验名称",
                        "source_type": "column",
                        "source_column": "不存在的列",
                    }
                ],
            },
        )
        assert r.status_code == 400
        assert "不存在的列" in r.json()["detail"]

    def test_generate_with_image_vars(self, client: TestClient, template_fid: str):
        """用 image_vars 注入图片，报告含图片。"""
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
        up = client.post(
            "/api/image/upload", files={"file": ("chart.png", png, "image/png")}
        )
        img_fid = up.json()["file_id"]
        r = client.post(
            "/api/report/generate",
            json={
                "template_file_id": template_fid,
                "mappings": [
                    {
                        "template_field": "实验名称",
                        "source_type": "constant",
                        "constant_value": "带图实验",
                    }
                ],
                "image_vars": {"chart": img_fid},
            },
        )
        assert r.status_code == 200, r.text
        task_id = r.json()["task_id"]
        t = client.post(f"/api/report/{task_id}/text")
        assert t.status_code == 200
        assert "带图实验" in t.json()["text"]


class TestPdfConvert:
    def test_convert_generated_report(self, client: TestClient, template_fid: str):
        gen = _generate(
            client,
            template_fid,
            [
                {
                    "template_field": "实验名称",
                    "source_type": "constant",
                    "constant_value": "转PDF实验",
                }
            ],
        )
        task_id = gen["task_id"]
        r = client.post("/api/report/pdf", json={"task_id": task_id})
        assert r.status_code == 200, r.text
        pdf_task = r.json()["task_id"]
        dl = client.get(r.json()["download_url"])
        assert dl.status_code == 200
        assert dl.headers["content-type"] == "application/pdf"
        assert len(dl.content) > 0
        assert pdf_task != task_id

    def test_convert_missing_task(self, client: TestClient):
        r = client.post("/api/report/pdf", json={"task_id": "not_exist"})
        assert r.status_code == 404


class TestReportText:
    def test_report_text(self, client: TestClient, template_fid: str):
        gen = _generate(
            client,
            template_fid,
            [
                {
                    "template_field": "实验名称",
                    "source_type": "constant",
                    "constant_value": "文本抽取测试",
                }
            ],
        )
        task_id = gen["task_id"]
        t = client.post(f"/api/report/{task_id}/text")
        assert t.status_code == 200, t.text
        assert "文本抽取测试" in t.json()["text"]

    def test_text_missing_task(self, client: TestClient):
        r = client.post("/api/report/not_exist/text")
        assert r.status_code == 404


class TestAuth:
    def test_auth_required_when_configured(self, monkeypatch):
        """配置 FORMORA_API_KEY 后，受保护端点无 token 返回 401。"""
        import formora.api as api_mod

        monkeypatch.setattr(api_mod, "_API_KEY", "test-key")
        from fastapi.testclient import TestClient as TC

        c = TC(app)
        # /api/health 是公开健康检查（探活用），不受保护；用数据读取端点验证鉴权
        with DATA.open("rb") as f:
            files = {"file": ("数据.csv", f, "text/csv")}
            r = c.post("/api/data/read", files=files)
            assert r.status_code == 401, f"无 token 应 401，实际 {r.status_code}"
            r2 = c.post(
                "/api/data/read",
                files=files,
                headers={"Authorization": "Bearer test-key"},
            )
            assert r2.status_code == 200, (
                f"带 token 应 200，实际 {r2.status_code} {r2.text}"
            )

    def test_health_public_when_no_auth(self, client: TestClient):
        """未配置鉴权时，health 可公开访问。"""
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["auth_enabled"] is False

class TestRateLimit:
    def test_exceed_limit_returns_429(self, client: TestClient, monkeypatch):
        """超过每 IP 限制后，后续请求返回 429 JSON。"""
        import formora.api as api_mod

        monkeypatch.setattr(api_mod, "_RATE_LIMITER", api_mod._RateLimiter(max_requests=3))
        url = "/api/mapping/auto?template_file_id=not_exist"
        # 前 3 次未超限：端点正常处理（模板不存在返回 404）
        for _ in range(3):
            assert client.post(url).status_code == 404
        r = client.post(url)
        assert r.status_code == 429, r.text
        assert r.headers["content-type"].startswith("application/json")
        assert "detail" in r.json()

    def test_health_exempt_from_rate_limit(self, client: TestClient, monkeypatch):
        """限流器已满时，/api/health 仍可访问。"""
        import formora.api as api_mod

        monkeypatch.setattr(api_mod, "_RATE_LIMITER", api_mod._RateLimiter(max_requests=1))
        url = "/api/mapping/auto?template_file_id=not_exist"
        assert client.post(url).status_code == 404  # 消耗唯一额度
        assert client.post(url).status_code == 429  # 限流生效
        r = client.get("/api/health")
        assert r.status_code == 200  # 健康检查不受限

    def test_rate_limit_env_override(self, monkeypatch):
        """FORMORA_RATE_LIMIT 环境变量可覆盖默认值，非法值回退默认 120。"""
        import formora.api as api_mod

        monkeypatch.setenv("FORMORA_RATE_LIMIT", "7")
        assert api_mod._rate_limit_from_env() == 7
        monkeypatch.setenv("FORMORA_RATE_LIMIT", "abc")
        assert api_mod._rate_limit_from_env() == 120


class TestGenerateBatch:
    """POST /api/report/generate_batch：批量生成、参数校验与鉴权。"""

    @pytest.fixture()
    def isolated_history(self, tmp_path, monkeypatch):
        """把任务历史写入临时目录，避免批量生成污染真实用户数据。"""
        import formora.services.history as history_mod

        monkeypatch.setattr(history_mod, "HISTORY_PATH", tmp_path / "history.jsonl")

    @staticmethod
    def _batch_mappings() -> list[dict]:
        return [
            {
                "template_field": "实验名称",
                "source_type": "constant",
                "constant_value": "批量实验",
            },
            {
                "template_field": "姓名",
                "source_type": "column",
                "source_column": "项目",
            },
        ]

    def test_generate_batch_success(
        self, client: TestClient, template_fid: str, data_fid: str, isolated_history
    ):
        """JSON 模式：data_file_id + 常量/列映射，生成数据行数份报告。"""
        r = client.post(
            "/api/report/generate_batch",
            json={
                "template_file_id": template_fid,
                "data_file_id": data_fid,
                "auto_chart": False,
                "mappings": self._batch_mappings(),
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["generated"] == 4
        assert data["failed"] == 0
        assert len(data["files"]) == 4
        assert data["errors"] == []
        for item in data["files"]:
            assert item["file_name"].endswith(".docx")
            assert item["path"]
            assert item["task_id"]
            assert item["download_url"]
            assert Path(item["path"]).exists()
            dl = client.get(item["download_url"])
            assert dl.status_code == 200
            assert dl.content[:2] == b"PK"

    def test_generate_batch_success_with_upload(
        self, client: TestClient, template_fid: str, isolated_history
    ):
        """multipart 模式：直接上传数据文件 + mappings JSON 字符串。"""
        with DATA.open("rb") as f:
            r = client.post(
                "/api/report/generate_batch",
                data={
                    "template_file_id": template_fid,
                    "mappings": json.dumps(
                        self._batch_mappings(), ensure_ascii=False
                    ),
                    "auto_chart": "false",
                },
                files={"file": ("数据.csv", f, "text/csv")},
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["generated"] == 4
        assert data["failed"] == 0
        assert len(data["files"]) == 4

    def test_generate_batch_missing_mappings(
        self, client: TestClient, template_fid: str, data_fid: str
    ):
        """空映射 → 400。"""
        r = client.post(
            "/api/report/generate_batch",
            json={
                "template_file_id": template_fid,
                "data_file_id": data_fid,
                "mappings": [],
            },
        )
        assert r.status_code == 400
        assert "mappings" in r.json()["detail"]

    def test_generate_batch_missing_data(self, client: TestClient, template_fid: str):
        """无数据文件（无 data_file_id 也无上传）→ 400。"""
        r = client.post(
            "/api/report/generate_batch",
            json={
                "template_file_id": template_fid,
                "mappings": self._batch_mappings(),
            },
        )
        assert r.status_code == 400
        assert "数据" in r.json()["detail"]

    def test_generate_batch_missing_template(self, client: TestClient, data_fid: str):
        """缺少 template_file_id → 400。"""
        r = client.post(
            "/api/report/generate_batch",
            json={"data_file_id": data_fid, "mappings": self._batch_mappings()},
        )
        assert r.status_code == 400

    def test_generate_batch_bad_template(self, client: TestClient, data_fid: str):
        """template_file_id 不存在 → 404。"""
        r = client.post(
            "/api/report/generate_batch",
            json={
                "template_file_id": "not_exist",
                "data_file_id": data_fid,
                "mappings": self._batch_mappings(),
            },
        )
        assert r.status_code == 404

    def test_generate_batch_missing_column(
        self, client: TestClient, template_fid: str, data_fid: str
    ):
        """映射列不存在于数据文件 → 400。"""
        r = client.post(
            "/api/report/generate_batch",
            json={
                "template_file_id": template_fid,
                "data_file_id": data_fid,
                "mappings": [
                    {
                        "template_field": "实验名称",
                        "source_type": "column",
                        "source_column": "不存在的列",
                    }
                ],
            },
        )
        assert r.status_code == 400

    def test_generate_batch_auth_required(self, monkeypatch, isolated_history):
        """配置 FORMORA_API_KEY 后，无 token 返回 401；带 token 通过鉴权。"""
        import formora.api as api_mod
        from fastapi.testclient import TestClient as TC

        monkeypatch.setattr(api_mod, "_API_KEY", "test-key")
        c = TC(app)
        body = {"template_file_id": "x", "mappings": []}
        r = c.post("/api/report/generate_batch", json=body)
        assert r.status_code == 401
        r2 = c.post(
            "/api/report/generate_batch",
            json=body,
            headers={"Authorization": "Bearer test-key"},
        )
        # 鉴权通过后进入参数校验：空映射应返回 400 而非 401
        assert r2.status_code == 400
        assert "mappings" in r2.json()["detail"]
