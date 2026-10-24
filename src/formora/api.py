"""FormoraReport REST API 层（阶段2：后端化）。

用 FastAPI 把 core 引擎包装为 REST 服务，供微信小程序 / App 前端调用。
仅依赖 core 层纯 Python 函数，不依赖 Qt / UI 状态，与桌面端共享同一套逻辑。

设计要点：
- 文件用内存字典管理（file_id -> 磁盘路径），任务结果同样按 task_id 暂存；
- 生成报告复用 core.generator.generate_report，与桌面端行为一致；
- 图片字段：前端先上传图片得到 file_id，映射里 image 字段的 value 填 file_id；
- 生产部署应把文件存储换为对象存储 / 数据库，本实现用于本地/演示/自托管。
"""
from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import formora
from formora.core import data_reader, generator, mapper, pdf_exporter, template_parser
from formora.core.models import FieldMapping
from formora.services.report_reader import extract_report_text

app = FastAPI(
    title="FormoraReport API",
    description="实验报告自动生成引擎 REST 接口",
    version=formora.__version__,
)

# 允许跨域（小程序/前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 内存文件/任务存储 ----------

_FILES: dict[str, Path] = {}          # file_id -> 已上传文件路径
_TASKS: dict[str, Path] = {}          # task_id -> 生成结果路径
_WORK_DIR = Path(tempfile.mkdtemp(prefix="formora_api_"))

# ---------- Pydantic 模型 ----------

class MappingItem(BaseModel):
    template_field: str
    source_type: str = "column"       # column | constant | text | image
    source_column: str | None = None
    constant_value: str | None = None
    value: str | None = None          # 图片字段填已上传的 file_id


class GenerateRequest(BaseModel):
    template_file_id: str
    mappings: list[MappingItem] = Field(default_factory=list)
    data_file_id: str | None = None
    row_index: int | None = None      # 指定第几行数据；None 表示只填常量/文本
    image_vars: dict[str, str] = Field(default_factory=dict)  # 占位符 -> 图片 file_id


class PdfRequest(BaseModel):
    docx_file_id: str


# ---------- 辅助函数 ----------

def _save_upload(file: UploadFile, prefix: str) -> str:
    file_id = f"{prefix}_{uuid.uuid4().hex[:12]}"
    suffix = Path(file.filename or "").suffix.lower()
    dest = _WORK_DIR / (file_id + suffix)
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    _FILES[file_id] = dest
    return file_id


def _get_file(file_id: str, suffix: str = "") -> Path:
    path = _FILES.get(file_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在或已过期: {file_id}")
    return path


# ---------- 端点 ----------

@app.get("/api/health")
def health() -> dict:
    """健康检查：返回服务状态与版本。"""
    return {
        "status": "ok",
        "version": formora.__version__,
        "files_cached": len(_FILES),
        "tasks": len(_TASKS),
    }


@app.post("/api/template/parse")
async def parse_template(file: UploadFile = File(...)) -> dict:
    """上传 DOCX 模板，返回占位符、章节、图片位。"""
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="仅支持 .docx 模板文件")
    file_id = _save_upload(file, "tpl")
    try:
        info = template_parser.parse_template(_FILES[file_id])
        from formora.services.report_service import is_image_field
        image_ph = [p for p in info.placeholders if is_image_field(p)]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"模板解析失败: {e}")
    return {
        "file_id": file_id,
        "placeholders": sorted(info.placeholders),
        "sections": info.sections,
        "has_images": info.has_images,
        "image_placeholders": sorted(image_ph),
        "missing_core_fields": info.missing_core_fields,
    }


@app.post("/api/data/read")
async def read_data(file: UploadFile = File(...)) -> dict:
    """上传数据文件（CSV/Excel/TXT/MD/PDF），返回列名与预览行。"""
    file_id = _save_upload(file, "data")
    try:
        ds = data_reader.read_data(_FILES[file_id])
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"数据读取失败: {e}")
    return {
        "file_id": file_id,
        "kind": ds.kind,
        "columns": list(ds.columns),
        "rows_preview": ds.rows[:5],
        "row_count": len(ds.rows),
    }


@app.post("/api/mapping/auto")
async def auto_mapping(template_file_id: str, data_file_id: str | None = None) -> dict:
    """自动映射：根据模板占位符与数据列名智能匹配。"""
    tpl_path = _get_file(template_file_id)
    info = template_parser.parse_template(tpl_path)
    ds = None
    if data_file_id:
        ds = data_reader.read_data(_get_file(data_file_id))
    mappings = mapper.auto_map(info, ds)
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
async def generate_report(req: GenerateRequest) -> dict:
    """根据模板 + 映射（+ 可选数据行）生成 DOCX，返回 task_id 与下载 URL。"""
    tpl_path = _get_file(req.template_file_id, suffix=".docx")
    info = template_parser.parse_template(tpl_path)

    # 数据行
    row: dict | None = None
    if req.data_file_id:
        ds = data_reader.read_data(_get_file(req.data_file_id))
        if ds.rows:
            if req.row_index is not None:
                if req.row_index < 0 or req.row_index >= len(ds.rows):
                    raise HTTPException(status_code=400, detail=f"row_index 越界: {req.row_index}")
                row = ds.rows[req.row_index]
            else:
                row = ds.rows[0]
        elif req.mappings:
            raise HTTPException(status_code=400, detail="数据文件为空，无法按列映射填充")

    # 构造映射
    mappings: list[FieldMapping] = []
    for item in req.mappings:
        value = item.value
        # 图片字段：value 是已上传的图片 file_id，这里解析为磁盘路径
        if item.source_type == "image" and value:
            value = str(_get_file(value))
        mappings.append(FieldMapping(
            template_field=item.template_field,
            source_type=item.source_type,  # type: ignore[arg-type]
            source_column=item.source_column,
            constant_value=item.constant_value,
            value=value,
        ))

    # 解析 context（与桌面端 mapper.resolve_values 一致）
    context = mapper.resolve_values(mappings, row=row)

    # 图片变量（image_vars: 占位符 -> 图片 file_id）
    image_vars: dict[str, str] = {}
    for placeholder, fid in req.image_vars.items():
        image_vars[placeholder] = str(_get_file(fid))

    task_id = f"task_{uuid.uuid4().hex[:12]}"
    out_path = _WORK_DIR / f"{task_id}.docx"
    try:
        generator.generate_report(
            tpl_path, context, out_path,
            image_vars=image_vars, template_info=info,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败: {e}")

    _TASKS[task_id] = out_path
    return {
        "task_id": task_id,
        "download_url": f"/api/report/{task_id}/download",
    }


@app.get("/api/report/{task_id}/download")
def download_report(task_id: str) -> FileResponse:
    """下载生成的 DOCX 报告。"""
    path = _TASKS.get(task_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="报告不存在或已过期")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{task_id}.docx",
    )


@app.post("/api/report/pdf")
async def convert_pdf(req: PdfRequest) -> dict:
    """把已生成的 DOCX 转为 PDF，返回下载 URL。"""
    docx_path = _get_file(req.docx_file_id, suffix=".docx")
    out_path = docx_path.with_suffix(".pdf")
    try:
        pdf_exporter.export_pdf(docx_path, out_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 转换失败: {e}")
    task_id = f"pdf_{uuid.uuid4().hex[:12]}"
    _TASKS[task_id] = out_path
    return {
        "task_id": task_id,
        "download_url": f"/api/report/{task_id}/download",
    }


@app.post("/api/report/{task_id}/text")
def report_text(task_id: str) -> dict:
    """抽取已生成报告的文本（供预览 / AI 审查）。"""
    path = _TASKS.get(task_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="报告不存在或已过期")
    return {"text": extract_report_text(path)}