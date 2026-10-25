"""FormoraReport REST API 层（阶段2：后端化）。

用 FastAPI 把 core 引擎包装为 REST 服务，供微信小程序 / App 前端调用。
仅依赖 core 层纯 Python 函数，不依赖 Qt / UI 状态，与桌面端共享同一套逻辑。

设计要点：
- 文件用内存字典管理（file_id -> 记录），任务结果按 task_id 暂存（含类型/时间戳）；
- 生成报告复用 core.generator.generate_report，与桌面端行为一致；
- 图片字段：前端先上传图片得到 file_id，映射里 image 字段的 value 填 file_id；
- 安全：可选 API Key 鉴权（FORMORA_API_KEY）、上传大小限制、文件 TTL/容量清理、
  文件类型魔数校验、错误消息不泄露内部路径；
- 生产部署应把文件存储换为对象存储 / 数据库，本实现用于本地/演示/自托管。
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError

import formora
from formora.core import data_reader, generator, mapper, pdf_exporter, template_parser
from formora.core.errors import (
    DocumentFormatError,
    ExternalDependencyError,
    FormoraError,
    UserError,
)
from formora.core.models import FieldMapping, FieldSourceType, ReportTask
from formora.services.report_reader import extract_report_text

logger = logging.getLogger("formora.api")

# ---------- 配置 ----------

MAX_UPLOAD_SIZE = int(os.environ.get("FORMORA_MAX_UPLOAD_MB", "20")) * 1024 * 1024
FILE_TTL_SECONDS = int(os.environ.get("FORMORA_FILE_TTL_HOURS", "1")) * 3600
MAX_CACHED_FILES = int(os.environ.get("FORMORA_MAX_CACHED_FILES", "1000"))
_API_KEY = os.environ.get("FORMORA_API_KEY", "").strip()
_CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("FORMORA_CORS_ORIGINS", "*").split(",")
    if o.strip()
]

# ---------- 限流 ----------


def _rate_limit_from_env() -> int:
    """读取 FORMORA_RATE_LIMIT（每分钟每 IP 请求上限），非法值回退默认 120。"""
    try:
        return max(1, int(os.environ.get("FORMORA_RATE_LIMIT", "120")))
    except ValueError:
        logger.warning("FORMORA_RATE_LIMIT 不是合法整数，使用默认值 120")
        return 120


RATE_LIMIT_PER_MINUTE = _rate_limit_from_env()
RATE_LIMIT_WINDOW_SECONDS = 60.0


class _RateLimiter:
    """线程安全的内存滑动窗口限流器：按 client IP 记录窗口内请求时间戳。

    仅适用于单进程部署（多 worker 时各进程独立计数）；生产环境可替换为 Redis 等共享存储。
    """

    def __init__(
        self, max_requests: int, window_seconds: float = RATE_LIMIT_WINDOW_SECONDS
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._max_keys = 10_000

    def allow(self, key: str, now: float | None = None) -> bool:
        """为 key 记录一次请求；未超限返回 True，超限返回 False（超限请求不计入窗口）。"""
        now = time.time() if now is None else now
        cutoff = now - self.window_seconds
        with self._lock:
            if len(self._hits) >= self._max_keys:
                self._prune(now)
            timestamps = self._hits.get(key)
            if timestamps is None:
                self._hits[key] = deque([now])
                return True
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= self.max_requests:
                return False
            timestamps.append(now)
            return True

    def _prune(self, now: float) -> None:
        """清理窗口已完全滑出的 key，防止字典无限增长。"""
        cutoff = now - self.window_seconds
        stale = [k for k, ts in self._hits.items() if not ts or ts[-1] <= cutoff]
        for k in stale:
            del self._hits[k]

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


class RateLimitMiddleware:
    """基础限流中间件：除 /api/health 外，每 client IP 每分钟最多 RATE_LIMIT_PER_MINUTE 次请求。"""

    def __init__(self, app: FastAPI):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == "/api/health" or path.startswith("/api/health/"):
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        key = client[0] if client else "unknown"
        if not _RATE_LIMITER.allow(key):
            response = JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后重试"},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


_RATE_LIMITER = _RateLimiter(RATE_LIMIT_PER_MINUTE)

app = FastAPI(
    title="FormoraReport API",
    description="实验报告自动生成引擎 REST 接口",
    version=formora.__version__,
)

# 限流中间件注册在 CORS 之前：CORS 最外层处理预检，429 响应同样带 CORS 头
app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 内存文件/任务存储 ----------


@dataclass
class _FileRecord:
    path: Path
    created_at: float


@dataclass
class _TaskRecord:
    path: Path
    kind: str  # "docx" | "pdf"
    created_at: float


_FILES: dict[str, _FileRecord] = {}
_TASKS: dict[str, _TaskRecord] = {}
_WORK_DIR = Path(tempfile.mkdtemp(prefix="formora_api_"))


def _now() -> float:
    return time.time()


def _prune_expired() -> None:
    """清理过期文件与超容量的最旧条目，并删除对应磁盘文件，避免内存/磁盘无限增长。"""
    now = _now()

    def _drop(records: dict[str, "_FileRecord | _TaskRecord"], key: str) -> None:
        """弹出记录并同步删除磁盘文件，保证内存字典与磁盘一致。"""
        rec = records.pop(key, None)
        if rec is not None:
            try:
                rec.path.unlink(missing_ok=True)
            except OSError:
                pass

    for fid in [
        fid for fid, rec in _FILES.items() if now - rec.created_at > FILE_TTL_SECONDS
    ]:
        _drop(_FILES, fid)
    for tid in [
        tid for tid, rec in _TASKS.items() if now - rec.created_at > FILE_TTL_SECONDS
    ]:
        _drop(_TASKS, tid)

    if len(_FILES) > MAX_CACHED_FILES:
        for fid in sorted(_FILES, key=lambda f: _FILES[f].created_at)[
            : len(_FILES) - MAX_CACHED_FILES
        ]:
            _drop(_FILES, fid)
    if len(_TASKS) > MAX_CACHED_FILES:
        for tid in sorted(_TASKS, key=lambda t: _TASKS[t].created_at)[
            : len(_TASKS) - MAX_CACHED_FILES
        ]:
            _drop(_TASKS, tid)


def _cleanup_workdir() -> None:
    """清理工作目录中超过 TTL 的残留文件（启动时调用）。"""
    now = _now()
    for p in _WORK_DIR.glob("*"):
        try:
            if p.is_file() and now - p.stat().st_mtime > FILE_TTL_SECONDS:
                p.unlink(missing_ok=True)
        except OSError:
            pass


_cleanup_workdir()


# ---------- 鉴权 ----------


def _verify_api_key(authorization: str | None = Header(default=None)) -> None:
    """若配置了 FORMORA_API_KEY，则要求请求头携带 Bearer token。"""
    if not _API_KEY:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证信息")
    token = authorization[len("Bearer ") :].strip()
    if token != _API_KEY:
        raise HTTPException(status_code=401, detail="认证失败")


# ---------- Pydantic 模型 ----------


class MappingItem(BaseModel):
    template_field: str
    source_type: FieldSourceType = "column"
    source_column: str | None = None
    constant_value: str | None = None
    value: str | None = None  # 图片字段填已上传的 file_id


class GenerateRequest(BaseModel):
    template_file_id: str
    mappings: list[MappingItem] = Field(default_factory=list)
    data_file_id: str | None = None
    row_index: int | None = None  # 指定第几行数据；None 表示只填常量/文本
    image_vars: dict[str, str] = Field(default_factory=dict)  # 占位符 -> 图片 file_id


class GenerateBatchRequest(BaseModel):
    """批量生成请求（JSON 模式；multipart 模式的解析见 generate_batch 端点）。"""

    template_file_id: str
    mappings: list[MappingItem] = Field(default_factory=list)
    data_file_id: str | None = None
    auto_chart: bool | None = None  # 是否自动生成图表；None 表示用服务默认值


class PdfRequest(BaseModel):
    task_id: str  # 已生成报告的 task_id


# ---------- 辅助函数 ----------


def _save_upload(
    file: UploadFile, prefix: str, allowed_suffixes: set[str] | None = None
) -> str:
    """流式保存上传文件，限制大小与后缀。返回 file_id。"""
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if allowed_suffixes and suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的文件类型 {suffix or '(无后缀)'}，仅支持: {', '.join(sorted(allowed_suffixes))}",
        )
    file_id = f"{prefix}_{uuid.uuid4().hex}"
    dest = _WORK_DIR / (file_id + suffix)
    size = 0
    with dest.open("wb") as out:
        while True:
            chunk = file.file.read(1024 * 64)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_SIZE:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"文件超过大小限制 {MAX_UPLOAD_SIZE // 1024 // 1024}MB",
                )
            out.write(chunk)
    _FILES[file_id] = _FileRecord(path=dest, created_at=_now())
    _prune_expired()
    return file_id


def _check_docx_magic(path: Path) -> bool:
    """校验 DOCX 魔数（ZIP 签名 PK\x03\x04），防止任意文件伪装 .docx。"""
    try:
        with path.open("rb") as f:
            return f.read(2) == b"PK"
    except OSError:
        return False


def _get_file(file_id: str) -> Path:
    rec = _FILES.get(file_id)
    if rec is None or not rec.path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    return rec.path


def _handle_error(exc: Exception) -> HTTPException:
    """把 core 层异常映射为友好状态码与通用消息（不泄露内部路径）。"""
    if isinstance(exc, UserError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, DocumentFormatError):
        return HTTPException(status_code=422, detail="文件格式不支持，请检查文件内容")
    if isinstance(exc, ExternalDependencyError):
        logger.warning("外部依赖不可用: %s", exc)
        return HTTPException(
            status_code=503, detail="外部依赖不可用（LibreOffice/Word/网络）"
        )
    if isinstance(exc, FormoraError):
        return HTTPException(status_code=422, detail="请求处理失败，请检查输入")
    logger.exception("API 内部错误: %s", exc)
    return HTTPException(status_code=500, detail="服务器内部错误，请稍后重试")


def _register_task(path: Path, kind: str) -> str:
    task_id = f"{'pdf' if kind == 'pdf' else 'task'}_{uuid.uuid4().hex}"
    _TASKS[task_id] = _TaskRecord(path=path, kind=kind, created_at=_now())
    _prune_expired()
    return task_id


# ---------- 端点 ----------


@app.get("/api/health")
def health() -> dict:
    """健康检查：返回服务状态、版本与安全配置。"""
    return {
        "status": "ok",
        "version": formora.__version__,
        "files_cached": len(_FILES),
        "tasks": len(_TASKS),
        "auth_enabled": bool(_API_KEY),
        "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
    }


@app.post("/api/template/parse")
async def parse_template(
    file: UploadFile = File(...),
    _auth: None = Depends(_verify_api_key),
) -> dict:
    """上传 DOCX 模板，返回占位符、章节、图片位。"""
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="仅支持 .docx 模板文件")
    file_id = _save_upload(file, "tpl", allowed_suffixes={".docx"})
    tpl_path = _FILES[file_id].path
    if not _check_docx_magic(tpl_path):
        raise HTTPException(status_code=422, detail="文件不是有效的 DOCX 模板")
    try:
        info = template_parser.parse_template(tpl_path)
    except Exception as e:
        raise _handle_error(e)
    from formora.services.report_service import is_image_field

    image_ph = [p for p in info.placeholders if is_image_field(p)]
    return {
        "file_id": file_id,
        "placeholders": sorted(info.placeholders),
        "sections": info.sections,
        "has_images": info.has_images,
        "image_placeholders": sorted(image_ph),
        "missing_core_fields": info.missing_core_fields,
    }


@app.post("/api/data/read")
async def read_data(
    file: UploadFile = File(...),
    _auth: None = Depends(_verify_api_key),
) -> dict:
    """上传数据文件（CSV/Excel/TXT/MD/PDF），返回列名与预览行。"""
    file_id = _save_upload(file, "data")
    try:
        ds = data_reader.read_data(_FILES[file_id].path)
    except Exception as e:
        raise _handle_error(e)
    return {
        "file_id": file_id,
        "kind": ds.kind,
        "columns": list(ds.columns),
        "rows_preview": ds.rows[:5],
        "row_count": len(ds.rows),
    }


@app.post("/api/image/upload")
async def upload_image(
    file: UploadFile = File(...),
    _auth: None = Depends(_verify_api_key),
) -> dict:
    """上传图片（PNG/JPG/WebP/GIF），返回 file_id 供 image 映射/图表使用。"""
    file_id = _save_upload(
        file, "img", allowed_suffixes={".png", ".jpg", ".jpeg", ".webp", ".gif"}
    )
    return {
        "file_id": file_id,
        "size": _FILES[file_id].path.stat().st_size,
    }


@app.post("/api/mapping/auto")
async def auto_mapping(
    template_file_id: str,
    data_file_id: str | None = None,
    _auth: None = Depends(_verify_api_key),
) -> dict:
    """自动映射：根据模板占位符与数据列名智能匹配。"""
    tpl_path = _get_file(template_file_id)
    try:
        info = template_parser.parse_template(tpl_path)
        ds = None
        if data_file_id:
            ds = data_reader.read_data(_get_file(data_file_id))
        mappings = mapper.auto_map(info, ds)
    except Exception as e:
        raise _handle_error(e)
    return {
        "mappings": [
            {
                "template_field": m.template_field,
                "source_type": m.source_type,
                "source_column": m.source_column,
                "constant_value": m.constant_value,
            }
            for m in mappings
        ],
    }


@app.post("/api/report/generate")
async def generate_report(
    req: GenerateRequest,
    _auth: None = Depends(_verify_api_key),
) -> dict:
    """根据模板 + 映射（+ 可选数据行）生成 DOCX，返回 task_id 与下载 URL。"""
    tpl_path = _get_file(req.template_file_id)
    try:
        info = template_parser.parse_template(tpl_path)
    except Exception as e:
        raise _handle_error(e)

    # 数据行
    row: dict | None = None
    columns: list[str] = []
    if req.data_file_id:
        try:
            ds = data_reader.read_data(_get_file(req.data_file_id))
        except Exception as e:
            raise _handle_error(e)
        columns = list(ds.columns)
        if ds.rows:
            if req.row_index is not None:
                if req.row_index < 0 or req.row_index >= len(ds.rows):
                    raise HTTPException(
                        status_code=400, detail=f"row_index 越界: {req.row_index}"
                    )
                row = ds.rows[req.row_index]
            else:
                row = ds.rows[0]
        elif any(m.source_type == "column" for m in req.mappings):
            raise HTTPException(
                status_code=400, detail="数据文件为空，无法按列映射填充"
            )

    # 列映射校验：避免静默填空
    missing_cols = [
        m.source_column
        for m in req.mappings
        if m.source_type == "column"
        and m.source_column
        and m.source_column not in columns
    ]
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"映射的列不存在于数据文件: {', '.join(sorted(set(missing_cols)))}",
        )

    # 构造映射
    mappings: list[FieldMapping] = []
    for item in req.mappings:
        value = item.value
        if item.source_type == "image" and value:
            value = str(_get_file(value))
        mappings.append(
            FieldMapping(
                template_field=item.template_field,
                source_type=item.source_type,
                source_column=item.source_column,
                constant_value=item.constant_value,
                value=value,
            )
        )

    context = mapper.resolve_values(mappings, row=row)

    # 图片变量（image_vars: 占位符 -> 图片 file_id）
    image_vars: dict[str, str] = {}
    for placeholder, fid in req.image_vars.items():
        image_vars[placeholder] = str(_get_file(fid))

    out_path = _WORK_DIR / f"task_{uuid.uuid4().hex}.docx"
    try:
        generator.generate_report(
            tpl_path,
            context,
            out_path,
            image_vars=image_vars,
            template_info=info,
        )
    except Exception as e:
        raise _handle_error(e)

    task_id = _register_task(out_path, "docx")
    return {
        "task_id": task_id,
        "download_url": f"/api/report/{task_id}/download",
    }


@app.post("/api/report/generate_batch")
async def generate_batch(
    request: Request,
    _auth: None = Depends(_verify_api_key),
) -> dict:
    """批量生成多份 DOCX（同步版）。

    请求支持两种格式：
    - JSON：{"template_file_id", "data_file_id", "mappings": [...], "auto_chart": bool}
    - multipart/form-data：template_file_id + mappings(JSON 数组字符串) +
      file(数据文件上传)，可选 data_file_id / auto_chart。

    返回每份生成文件的 file_name / path / task_id / download_url，以及失败信息列表。

    注意：批量生成是耗时操作（每份报告都要重新解析模板并渲染 DOCX）。当前为同步实现，
    请求会阻塞直到全部生成完成，适合单机/内网调用与批量份数较少（如课程报告）的场景。

    【后续方案：异步任务队列】
    若批量份数大或并发高，应改为异步：
    1. 本端点仅校验参数并创建批量任务记录，返回 batch_id（202 Accepted）；
    2. 后台 worker（Celery / RQ，或 FastAPI BackgroundTasks + 线程池）消费队列，
       逐行调用 report_service.generate_batch 并更新任务状态与进度；
    3. 客户端通过 GET /api/report/batch/{batch_id} 轮询状态，完成后获取文件列表；
    4. 文件与任务记录沿用现有 _TASKS TTL 清理机制，超时未查询自动回收。
    """
    # ---- 解析请求体（JSON 或 multipart） ----
    content_type = request.headers.get("content-type", "")
    is_form = content_type.startswith("multipart/form-data") or content_type.startswith(
        "application/x-www-form-urlencoded"
    )
    req: GenerateBatchRequest
    if is_form:
        form = await request.form()
        template_file_id = str(form.get("template_file_id") or "").strip()
        mappings_raw = form.get("mappings") or "[]"
        try:
            mappings_data = json.loads(mappings_raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="mappings 必须是 JSON 数组字符串")
        if not isinstance(mappings_data, list):
            raise HTTPException(status_code=400, detail="mappings 必须是 JSON 数组")
        auto_chart_raw = form.get("auto_chart")
        auto_chart = None
        if auto_chart_raw is not None:
            auto_chart = str(auto_chart_raw).strip().lower() in ("1", "true", "yes", "on")
        try:
            req = GenerateBatchRequest(
                template_file_id=template_file_id,
                mappings=[MappingItem(**m) for m in mappings_data],
                data_file_id=str(form.get("data_file_id") or "").strip() or None,
                auto_chart=auto_chart,
            )
        except (ValidationError, TypeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"mappings 格式错误: {e}")
        uploaded = form.get("file")
        if uploaded is not None and getattr(uploaded, "filename", None):
            if req.data_file_id:
                raise HTTPException(
                    status_code=400, detail="不能同时提供 data_file_id 与文件上传"
                )
            req.data_file_id = _save_upload(uploaded, "data")
    else:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="请求体必须是合法 JSON")
        try:
            req = GenerateBatchRequest.model_validate(body)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"请求参数错误: {e}")

    # ---- 参数校验 ----
    if not req.template_file_id:
        raise HTTPException(status_code=400, detail="缺少 template_file_id")
    if not req.mappings:
        raise HTTPException(status_code=400, detail="映射列表 mappings 不能为空")
    if not req.data_file_id:
        raise HTTPException(
            status_code=400, detail="缺少数据文件（请提供 data_file_id 或上传数据文件）"
        )

    # ---- 模板与数据 ----
    try:
        tpl_path = _get_file(req.template_file_id)
        info = template_parser.parse_template(tpl_path)
        ds = data_reader.read_data(_get_file(req.data_file_id))
    except HTTPException:
        raise
    except Exception as e:
        raise _handle_error(e)

    if not ds.is_tabular or not ds.rows:
        raise HTTPException(
            status_code=400, detail="数据文件为空或无表格数据，无法批量生成"
        )

    # 列映射校验：避免静默填空
    missing_cols = [
        m.source_column
        for m in req.mappings
        if m.source_type == "column"
        and m.source_column
        and m.source_column not in ds.columns
    ]
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"映射的列不存在于数据文件: {', '.join(sorted(set(missing_cols)))}",
        )

    # 构造 FieldMapping 列表（图片 file_id -> 本地路径）
    mappings: list[FieldMapping] = []
    for item in req.mappings:
        value = item.value
        if item.source_type == "image" and value:
            value = str(_get_file(value))
        mappings.append(
            FieldMapping(
                template_field=item.template_field,
                source_type=item.source_type,
                source_column=item.source_column,
                constant_value=item.constant_value,
                value=value,
            )
        )

    # ---- 复用 report_service.generate_batch（同步执行） ----
    from formora.services.config import Config
    from formora.services.report_service import generate_batch as service_generate_batch

    task = ReportTask(
        name="批量报告",
        template_path=tpl_path,
        data_source=ds,
        mappings=mappings,
        status="generating",
        created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
    )
    # 隔离配置：输出到 API 工作目录（随 _TASKS TTL 清理），避免写入用户 Documents
    cfg = Config(_WORK_DIR / "config.json")
    cfg.set("output_dir", str(_WORK_DIR / "batch_output"))
    if req.auto_chart is not None:
        cfg.set("auto_chart", req.auto_chart)
    state = SimpleNamespace(
        config=cfg,
        template=info,
        data=ds,
        mappings=mappings,
        task=task,
    )

    try:
        results, errors = service_generate_batch(state)
    except Exception as e:
        raise _handle_error(e)

    # ---- 注册每个生成文件为可下载任务 ----
    files: list[dict] = []
    for path_str in results:
        out = Path(path_str)
        task_id = _register_task(out, "docx")
        files.append(
            {
                "file_name": out.name,
                "path": str(out),
                "task_id": task_id,
                "download_url": f"/api/report/{task_id}/download",
            }
        )

    return {
        "total": len(files) + len(errors),
        "generated": len(files),
        "failed": len(errors),
        "files": files,
        "errors": errors,
    }


@app.get("/api/report/{task_id}/download")
def download_report(
    task_id: str, _auth: None = Depends(_verify_api_key)
) -> FileResponse:
    """下载生成的报告（按实际类型返回正确 MIME 与文件名）。"""
    rec = _TASKS.get(task_id)
    if rec is None or not rec.path.exists():
        raise HTTPException(status_code=404, detail="报告不存在或已过期")
    if rec.kind == "pdf":
        media_type = "application/pdf"
        filename = f"{task_id}.pdf"
    else:
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        filename = f"{task_id}.docx"
    return FileResponse(rec.path, media_type=media_type, filename=filename)


@app.post("/api/report/pdf")
async def convert_pdf(
    req: PdfRequest,
    _auth: None = Depends(_verify_api_key),
) -> dict:
    """把已生成报告的 DOCX 转为 PDF，返回新 task_id 与下载 URL。"""
    rec = _TASKS.get(req.task_id)
    if rec is None or not rec.path.exists():
        raise HTTPException(status_code=404, detail="报告不存在或已过期")
    if rec.kind != "docx":
        raise HTTPException(status_code=400, detail="该任务不是 DOCX 报告")
    out_path = rec.path.with_suffix(".pdf")
    try:
        pdf_exporter.export_pdf(rec.path, out_path)
    except Exception as e:
        raise _handle_error(e)
    task_id = _register_task(out_path, "pdf")
    return {
        "task_id": task_id,
        "download_url": f"/api/report/{task_id}/download",
    }


@app.post("/api/report/{task_id}/text")
def report_text(task_id: str, _auth: None = Depends(_verify_api_key)) -> dict:
    """抽取已生成报告的文本（供预览 / AI 审查）。"""
    rec = _TASKS.get(task_id)
    if rec is None or not rec.path.exists():
        raise HTTPException(status_code=404, detail="报告不存在或已过期")
    if rec.kind != "docx":
        raise HTTPException(status_code=400, detail="仅 DOCX 报告支持文本抽取")
    try:
        text = extract_report_text(rec.path)
    except Exception as e:
        raise _handle_error(e)
    # 限制响应大小，避免超大 DOCX 拖垮客户端
    if len(text) > 200_000:
        text = text[:200_000] + "\n...[内容过长已截断]"
    return {"text": text}
