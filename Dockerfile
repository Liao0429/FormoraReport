# syntax=docker/dockerfile:1
# =============================================================
# FormoraReport API 服务镜像
#   - 基础镜像: python:3.12-slim
#   - 内置 LibreOffice（DOCX -> PDF 导出）+ Noto CJK 中文字体
#   - 以非 root 用户运行
# 构建: docker build -t formora-api .
# 运行: docker compose up -d   （或 docker run 直接映射 8000 端口）
# =============================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TMPDIR=/data/tmp

# 系统依赖：
#   - libreoffice-writer / libreoffice-calc: DOCX->PDF（及 XLSX 转换）无头转换
#   - fonts-noto-cjk: 中文/日文/韩文字体（matplotlib 图表中文渲染、PDF 中文不乱码）
#   - fontconfig: 字体缓存
#   - tini: 作为 PID 1，保证 SIGTERM 能被正确转发给 uvicorn
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-writer \
        libreoffice-calc \
        fonts-noto-cjk \
        fontconfig \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f >/dev/null 2>&1

WORKDIR /app

# 创建非 root 运行用户 formora（uid 10001），并准备数据/临时目录
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin formora \
    && mkdir -p /data/tmp \
    && chown -R formora:formora /data

# 先复制依赖清单并安装（利用 Docker 层缓存）
COPY requirements.txt requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt

# 预热 matplotlib 字体缓存并校验 CJK 字体可用（图表中文正常渲染）
RUN python -c "from matplotlib import font_manager; font_manager.findfont('Noto Sans CJK SC', fallback_to_default=False); print('matplotlib CJK font: OK')" \
    || echo "matplotlib CJK font check skipped (fallback to DejaVu Sans)"

# 复制应用源码（API 入口 + src 包）
COPY --chown=formora:formora api_server.py ./
COPY --chown=formora:formora src/ ./src/

# 允许应用在 /app 下写临时文件（日志、profile 等）
RUN chown formora:formora /app

USER formora

EXPOSE 8000

# 健康检查：容器内直接用 Python 探测（无需 curl）
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3) or exit(1)"]

ENTRYPOINT ["/usr/bin/tini", "--"]
# 监听 0.0.0.0 以接受容器外/代理请求
CMD ["python", "api_server.py", "--host", "0.0.0.0", "--port", "8000"]