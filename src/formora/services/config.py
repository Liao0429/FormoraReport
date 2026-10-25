"""配置管理 + 敏感信息加密存储。

- 配置文件：%APPDATA%/FormoraReport/config.json（普通配置明文）。
- API 密钥：用 Windows DPAPI 加密后以 base64 存入 config，不明文落盘。
  纯 ctypes 调用 CryptProtectData / CryptUnprotectData，无需第三方库。
"""

from __future__ import annotations

import base64
import copy
import json
import logging
import os
import sys
from pathlib import Path

_IS_WINDOWS = sys.platform == "win32"

from formora.core.errors import UserError

logger = logging.getLogger("formora.config")

if _IS_WINDOWS:
    _app_root = Path(os.environ.get("APPDATA", str(Path.home()))) / "FormoraReport"
    _documents_root = (
        Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents"
    )
else:
    # macOS/Linux：遵循 XDG 规范（~/.config/FormoraReport）；文档目录探测真实 Documents
    _app_root = (
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        / "FormoraReport"
    )
    _candidates = [
        Path.home() / "Documents",
        Path.home() / "文档",
        Path.home(),
    ]
    _documents_root = next((p for p in _candidates if p.is_dir()), Path.home())

APP_DIR = _app_root
CONFIG_PATH = APP_DIR / "config.json"
LOG_DIR = APP_DIR / "logs"
HISTORY_PATH = APP_DIR / "history.jsonl"
OUTPUT_DEFAULT_DIR = _documents_root / "FormoraReport"

DEFAULTS = {
    "theme": "light",
    "output_dir": str(OUTPUT_DEFAULT_DIR),
    "ai": {
        "enabled": True,
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key_enc": "",
        "temperature": 0.2,
    },
    "privacy": {
        "upload_warning_shown": False,
    },
    "chart": {
        "colors": ["#1f77b4", "#ff7f0e"],
        "figsize": [6, 4],
        "dpi": 150,
        "grid": True,
        "font_size": 10,
    },
}


def _dpapi_encrypt(plain: str) -> str:
    """用 Windows DPAPI 加密（仅 Windows；其他平台抛 UserError）。"""
    if not _IS_WINDOWS:
        raise UserError("DPAPI 加密仅支持 Windows 平台。")
    import ctypes
    import ctypes.wintypes

    class _DataBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    data = plain.encode("utf-8")
    in_blob = _DataBlob(len(data), ctypes.cast(data, ctypes.POINTER(ctypes.c_char)))
    out_blob = _DataBlob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    ):
        raise UserError("DPAPI 加密失败。")
    try:
        encrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return base64.b64encode(encrypted).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _dpapi_decrypt(enc_b64: str) -> str:
    """用 Windows DPAPI 解密（仅 Windows；其他平台抛 UserError）。"""
    if not _IS_WINDOWS:
        raise UserError("DPAPI 解密仅支持 Windows 平台。")
    import ctypes
    import ctypes.wintypes

    class _DataBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    encrypted = base64.b64decode(enc_b64)
    in_blob = _DataBlob(
        len(encrypted), ctypes.cast(encrypted, ctypes.POINTER(ctypes.c_char))
    )
    out_blob = _DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    ):
        raise UserError("DPAPI 解密失败（可能配置被移动或系统账户变更）。")
    try:
        decrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return decrypted.decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


class Config:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return copy.deepcopy(DEFAULTS)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            # 配置损坏：备份原件后回退默认，避免下次保存覆盖损坏文件
            try:
                bak = self.path.with_suffix(".json.bak")
                self.path.replace(bak)
                logger.warning("配置文件损坏，已备份为 %s 并使用默认配置", bak)
            except OSError:
                logger.warning("配置文件损坏且无法备份，已使用默认配置")
            return copy.deepcopy(DEFAULTS)
        if not isinstance(raw, dict):
            # 合法 JSON 但非对象（数组/标量）：按损坏处理
            try:
                bak = self.path.with_suffix(".json.bak")
                self.path.replace(bak)
                logger.warning(
                    "配置文件格式异常（非对象），已备份为 %s 并使用默认配置", bak
                )
            except OSError:
                logger.warning("配置文件格式异常（非对象），已使用默认配置")
            return copy.deepcopy(DEFAULTS)
        merged = copy.deepcopy(DEFAULTS)
        merged.update(raw)
        if isinstance(merged.get("ai"), dict):
            ai = dict(DEFAULTS["ai"])
            ai.update(merged["ai"])
            merged["ai"] = ai
        if isinstance(merged.get("chart"), dict):
            chart_cfg = dict(DEFAULTS["chart"])
            chart_cfg.update(merged["chart"])
            merged["chart"] = chart_cfg
        return merged

    def save(self):
        """原子写配置：先写临时文件再替换，避免崩溃/断电损坏 config.json。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(str(tmp), str(self.path))

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value

    def set_ai_api_key(self, key: str):
        self.data["ai"]["api_key_enc"] = _dpapi_encrypt(key) if key else ""
        self.save()

    def get_ai_api_key(self) -> str:
        enc = (self.data.get("ai") or {}).get("api_key_enc", "")
        if not enc:
            return ""
        try:
            return _dpapi_decrypt(enc)
        except UserError:
            return ""


def ensure_dirs() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
