"""FormoraReport API 服务启动入口（FastAPI + Uvicorn）。

用法：
    python api_server.py                        # 默认 127.0.0.1:8000
    python api_server.py --host 0.0.0.0 --port 9000
    python api_server.py --reload               # 开发模式：代码变更自动重载
    python api_server.py --help                 # 查看全部参数

环境变量：
    FORMORA_API_KEY         设置后启用 Bearer Token 鉴权（在 src/formora/api.py 中读取）
    FORMORA_MAX_UPLOAD_MB   上传大小上限（默认 20）
    FORMORA_FILE_TTL_HOURS  文件/任务缓存时长（默认 1）
    FORMORA_MAX_CACHED_FILES 内存缓存文件上限（默认 1000）
    FORMORA_CORS_ORIGINS    允许的 CORS 来源（逗号分隔，默认 *）
    FORMORA_RATE_LIMIT      每分钟每 IP 请求上限（默认 120）

退出：
    按 Ctrl+C 会触发 Uvicorn 优雅关闭，并清理 API 临时工作目录
    （formora.api 导入时通过 tempfile.mkdtemp 创建）。
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import sys

# 确保能 import formora（源码运行时）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import uvicorn


def _get_version() -> str:
    """返回 formora 包版本号；导入失败时回退 'unknown'。"""
    try:
        import formora

        return str(formora.__version__)
    except Exception:  # noqa: BLE001 - 启动信息不允许被版本号拖垮
        return "unknown"


def _get_lan_ip() -> str:
    """通过 UDP 路由探测本机局域网 IP（不实际发送数据包）。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return ""


def _cleanup_temp_dir() -> None:
    """清理 API 临时工作目录（formora.api 在导入时创建）。

    幂等，可重复调用；仅当本进程已加载 formora.api 时执行，避免在
    reload 主进程中误导入模块而新建临时目录。
    """
    api = sys.modules.get("formora.api")
    if api is None:
        return
    work_dir = getattr(api, "_WORK_DIR", None)
    if work_dir is None:
        return
    try:
        shutil.rmtree(work_dir, ignore_errors=True)
    except Exception:  # noqa: BLE001 - 清理失败不应阻断退出
        pass


def _print_startup_info(host: str, port: int, api_key_set: bool) -> None:
    """打印版本、鉴权状态与可访问的 URL（含 Swagger /docs）。"""
    version = _get_version()
    urls = [f"http://127.0.0.1:{port}"]
    if host not in ("0.0.0.0", "::", ""):
        urls.append(f"http://{host}:{port}")
    else:
        lan_ip = _get_lan_ip()
        if lan_ip:
            urls.append(f"http://{lan_ip}:{port}")

    print("=" * 64)
    print(f"FormoraReport API v{version}")
    print(f"  可访问地址:  {urls[0]}")
    for url in urls[1:]:
        print(f"               {url}")
    print(f"  Swagger UI:  {urls[0]}/docs")
    print(f"  OpenAPI:     {urls[0]}/openapi.json")
    print(f"  健康检查:    {urls[0]}/api/health")
    print(f"  API Key 鉴权: {'已启用（FORMORA_API_KEY）' if api_key_set else '未启用（设置 FORMORA_API_KEY 可开启）'}")
    print("=" * 64)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FormoraReport API 服务（FastAPI + Uvicorn）"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="绑定地址（默认 127.0.0.1；对外提供服务可用 0.0.0.0）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="监听端口（默认 8000）",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="开发模式：代码变更时自动重载（reload 模式下不支持多 worker）",
    )
    args = parser.parse_args()

    api_key_set = bool(os.environ.get("FORMORA_API_KEY", "").strip())
    _print_startup_info(args.host, args.port, api_key_set)

    try:
        uvicorn.run(
            "formora.api:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    finally:
        # Uvicorn 捕获 Ctrl+C 后完成优雅关闭再返回；此处兜底清理临时目录。
        # 真正负责清理的是 formora.api 的 lifespan（reload 子进程同样生效）。
        _cleanup_temp_dir()


if __name__ == "__main__":
    main()
