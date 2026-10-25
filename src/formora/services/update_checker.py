"""GitHub Releases 更新检查服务（低风险：静默失败，绝不打扰主流程）。

启动后由 UI 在后台线程调用一次：查询 GitHub Releases 最新版，
与当前 __version__ 比较；有新版返回 (版本号, 下载页 URL)，否则返回 None。
网络/解析失败一律静默返回 None，不影响主流程。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from urllib.request import Request, urlopen

from formora import __version__ as CURRENT_VERSION

logger = logging.getLogger(__name__)

RELEASES_URL = "https://api.github.com/repos/Liao0429/FormoraReport/releases/latest"
DEFAULT_TIMEOUT = 5.0


def _parse_version(text: str) -> tuple[int, ...]:
    """把版本号解析为可比较的整数元组；解析失败返回空元组（视为不更新）。"""
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", text or "")
    if not match:
        return ()
    return tuple(int(part) for part in match.groups() if part is not None)


def is_newer(remote: str, current: str) -> bool:
    """判断远端版本号是否严格高于当前版本号（忽略 v 前缀）。"""
    return _parse_version(remote) > _parse_version(current)


def check_for_update(timeout: float = DEFAULT_TIMEOUT) -> tuple[str, str] | None:
    """同步执行一次更新检查。

    返回 (最新版本号, 下载页 URL)；无新版、请求失败或响应异常时返回 None。
    """
    try:
        request = Request(
            RELEASES_URL,
            headers={
                "User-Agent": f"FormoraReport/{CURRENT_VERSION}",
                "Accept": "application/vnd.github+json",
            },
        )
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        tag = str(data.get("tag_name") or "").strip()
        html_url = str(data.get("html_url") or "").strip()
        if not tag or not html_url or not is_newer(tag, CURRENT_VERSION):
            return None
        return (tag.lstrip("vV"), html_url)
    except Exception:
        # 网络失败/超时/响应异常：静默返回 None，不打扰用户。
        logger.debug("更新检查失败（已静默忽略）", exc_info=True)
        return None


async def check_for_update_async(
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[str, str] | None:
    """异步版本：把阻塞的网络请求放到后台线程执行，避免卡住 UI。"""
    return await asyncio.to_thread(check_for_update, timeout)
