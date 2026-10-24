"""FormoraReport API 服务启动入口。

用法：
    python api_server.py            # 默认 127.0.0.1:8000
    python api_server.py --port 9000
"""

import argparse
import os
import sys

# 确保能 import formora（源码运行时）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FormoraReport API 服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"FormoraReport API 服务启动: http://{args.host}:{args.port}/docs")
    uvicorn.run("formora.api:app", host=args.host, port=args.port, reload=False)
