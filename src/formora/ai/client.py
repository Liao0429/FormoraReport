"""OpenAI 兼容 API 客户端。

- 仅用户主动启用 AI 模式时使用。
- 密钥从 Config（DPAPI 加密）读取，不明文落盘。
- 结构化输出：要求模型返回 JSON，并解析。
- 防捏造：prompt 明确要求无依据内容标为「待补充/待确认」。
"""

from __future__ import annotations

import json
import re
import urllib.request

from formora.core.errors import ExternalDependencyError
from formora.services.config import Config

_CHAT_COMPLETIONS_SUFFIX = "/chat/completions"

# 允许的 URL scheme：仅 https；http 仅限本机回环（本地代理 / 测试端点）
_ALLOWED_SCHEMES = ("https",)
_ALLOWED_LOOPBACK_SCHEMES = ("https", "http")
# 不允许连接的内网/保留段前缀（SSRF 防护）
_BLOCKED_HOST_SUBSTRINGS = (
    "169.254.",
    "10.",
    "192.168.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "127.",
    "0.",
    "100.64.",
    "100.65.",
    "100.66.",
    "100.67.",
    "100.68.",
    "100.69.",
    "100.70.",
    "100.71.",
    "100.72.",
    "100.73.",
    "100.74.",
    "100.75.",
    "100.76.",
    "100.77.",
    "100.78.",
    "100.79.",
    "100.80.",
    "100.81.",
    "100.82.",
    "100.83.",
    "100.84.",
    "100.85.",
    "100.86.",
    "100.87.",
    "100.88.",
    "100.89.",
    "100.90.",
    "100.91.",
    "100.92.",
    "100.93.",
    "100.94.",
    "100.95.",
    "100.96.",
    "100.97.",
    "100.98.",
    "100.99.",
    "100.100.",
    "100.101.",
    "100.102.",
    "100.103.",
    "100.104.",
    "100.105.",
    "100.106.",
    "100.107.",
    "100.108.",
    "100.109.",
    "100.110.",
    "100.111.",
    "100.112.",
    "100.113.",
    "100.114.",
    "100.115.",
    "100.116.",
    "100.117.",
    "100.118.",
    "100.119.",
    "100.120.",
    "100.121.",
    "100.122.",
    "100.123.",
    "100.124.",
    "100.125.",
    "100.126.",
    "100.127.",
    "metadata.",
    "169.254.169.254",
)


def _validate_base_url(base_url: str) -> str:
    """校验并规范化 API base_url，阻止 SSRF / 密钥外发到内网或本地地址。

    规则：
    - 必须含 scheme 且仅允许 https（http 仅限 localhost / 127.0.0.1 / ::1）。
    - 拒绝内网/保留 IP 段（169.254.x、10.x、192.168.x、172.16-31.x、100.64+ 等）。
    - 拒绝裸 IP（除 localhost 回环）。
    校验失败抛 ExternalDependencyError，不发起网络请求。
    """
    from urllib.parse import urlparse

    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        raise ExternalDependencyError("AI API 地址不能为空。")
    if "://" not in base_url:
        raise ExternalDependencyError(
            f"AI API 地址缺少协议头（如 https://）：{base_url}"
        )
    try:
        parsed = urlparse(base_url)
    except Exception as e:
        raise ExternalDependencyError(f"AI API 地址无法解析：{e}")

    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    if not scheme or not host:
        raise ExternalDependencyError(f"AI API 地址不完整：{base_url}")

    is_loopback = host in ("localhost", "127.0.0.1", "::1")
    if is_loopback:
        if scheme not in _ALLOWED_LOOPBACK_SCHEMES:
            raise ExternalDependencyError(
                f"AI API 地址 scheme 仅允许 {'/'.join(_ALLOWED_LOOPBACK_SCHEMES)}：{base_url}"
            )
    else:
        if scheme not in _ALLOWED_SCHEMES:
            raise ExternalDependencyError(
                "出于安全考虑，AI API 地址仅允许 https://（本机代理可例外）。"
                f"当前：{base_url}"
            )
        # 拒绝内网/保留段
        if any(b in host for b in _BLOCKED_HOST_SUBSTRINGS):
            raise ExternalDependencyError(
                f"AI API 地址指向内网/保留地址，已阻止：{base_url}"
            )
        # 拒绝裸 IP（除回环）
        host_is_ip = host.replace(".", "").isdigit() or ":" in host
        if host_is_ip:
            raise ExternalDependencyError(
                f"AI API 地址为裸 IP，已阻止（请使用域名）：{base_url}"
            )

    return base_url


def is_configured(config: Config) -> bool:
    ai = config.get("ai", {}) or {}
    return (
        bool(ai.get("enabled"))
        and bool(config.get_ai_api_key())
        and bool(ai.get("base_url"))
    )


def _post_chat(
    base_url: str,
    model: str,
    api_key: str,
    messages: list[dict],
    temperature: float = 0.2,
    json_mode: bool = True,
    timeout: int = 60,
) -> dict:
    """向 OpenAI 兼容接口发送 chat/completions，返回解析后的 JSON。"""
    base_url = _validate_base_url(base_url)
    if base_url.endswith("/v1"):
        url = base_url + _CHAT_COMPLETIONS_SUFFIX
    else:
        url = base_url + "/v1" + _CHAT_COMPLETIONS_SUFFIX
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ExternalDependencyError(f"AI 请求失败: {e}")


def _parse_model_json(content) -> dict | list:
    """宽松解析模型输出为 JSON：剥离 Markdown 围栏、提取首个 JSON 对象/数组。

    兼容模型输出 ```json … ``` 或带前后缀文本的常见情况。
    """
    if content is None:
        raise ValueError("模型返回内容为空")
    text = str(content).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        if start >= 0:
            end_pos = text.rfind(close_ch)
            if end_pos > start:
                text = text[start:end_pos + 1]
                break
    return json.loads(text)


def _chat_json(config: Config, messages: list[dict], temperature: float = 0.2) -> dict:
    ai = config.get("ai", {})
    if not ai.get("enabled"):
        raise ExternalDependencyError(
            "AI 辅助已关闭：当前不会上传任何数据。如需使用，请在「设置」中启用 AI 辅助。"
        )
    base_url = (ai.get("base_url") or "").rstrip("/")
    model = ai.get("model") or ""
    api_key = config.get_ai_api_key()
    if not base_url or not model or not api_key:
        raise ExternalDependencyError("AI 配置不完整，请检查 API 地址、模型与密钥。")

    body = _post_chat(base_url, model, api_key, messages, temperature=temperature)
    try:
        content = body["choices"][0]["message"].get("content")
        # 部分 reasoning 模型把正文放在 reasoning_content
        if content is None:
            content = body["choices"][0]["message"].get("reasoning_content")
        result = _parse_model_json(content)
    except Exception as e:
        raise ExternalDependencyError(f"AI 返回无法解析为 JSON: {e}")
    if isinstance(result, list):
        return {"fields": result}
    if not isinstance(result, dict):
        raise ExternalDependencyError("AI 返回格式异常：既不是对象也不是数组。")
    return result

SYSTEM_PROMPT = (
    "你是一名严谨的实验报告辅助助手。你根据用户提供的实验模板字段与原始素材，"
    "抽取每个字段的内容。规则：\n"
    "1. 只能依据素材中的内容填写，不得编造实验数据、现象、测量结果、参考文献或过程。\n"
    "2. 若某字段在素材中没有依据，value 必须为“待补充”，并置 needs_confirmation=true。\n"
    "3. 对整理生成的内容，在 source 中注明依据（文件名/段落/表格）。\n"
    '4. 返回严格 JSON，格式为 {"fields":[{"field":"字段名","value":"内容",'
    '"source":"依据","needs_confirmation":true/false}]}。'
)


def extract_fields(
    config: Config, materials_text: str, template_fields: list[str]
) -> list[dict]:
    """从素材中抽取模板字段内容。返回 [{field, value, source, needs_confirmation}]"""
    if not is_configured(config):
        ai = config.get("ai", {}) or {}
        if not ai.get("enabled"):
            raise ExternalDependencyError(
                "AI 辅助已关闭：当前不会上传任何数据。如需使用，请在「设置」中启用 AI 辅助。"
            )
        raise ExternalDependencyError("AI 模式未启用或未配置，请先在 AI 设置中配置。")
    user_msg = (
        f"模板字段：{json.dumps(template_fields, ensure_ascii=False)}\n\n"
        f"原始素材：\n{materials_text[:60000]}"
    )
    result = _chat_json(
        config,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    if not isinstance(result, dict):
        raise ExternalDependencyError("AI 返回结构异常：期望 JSON 对象但得到其他类型。")
    return result.get("fields", [])


def review_report(config: Config, report_text: str) -> list[dict]:
    """审查报告内容，检查缺失、矛盾、疑似捏造。返回 [{field, issue, severity}]"""
    if not is_configured(config):
        ai = config.get("ai", {}) or {}
        if not ai.get("enabled"):
            raise ExternalDependencyError(
                "AI 辅助已关闭：当前不会上传任何数据。如需使用，请在「设置」中启用 AI 辅助。"
            )
        raise ExternalDependencyError("AI 模式未启用或未配置，请先在 AI 设置中配置。")
    user_msg = (
        "请审查以下实验报告。检查：缺失字段、前后矛盾、疑似无依据的数据。\n"
        '对每个问题返回 {"issues":[{"field":"字段","issue":"问题描述",'
        '"severity":"error|warning"}]}。没有问题则返回 {"issues":[]}。\n\n'
        f"报告内容：\n{report_text[:60000]}"
    )
    result = _chat_json(
        config,
        [
            {
                "role": "system",
                "content": "你是一名严谨的报告审查者，只依据给定内容判断，不臆测。",
            },
            {"role": "user", "content": user_msg},
        ],
    )
    if not isinstance(result, dict):
        raise ExternalDependencyError("AI 返回结构异常：期望 JSON 对象但得到其他类型。")
    return result.get("issues", [])


def test_connection(base_url: str, model: str, api_key: str) -> str:
    """用一次最小请求验证 API 连接。成功返回模型响应摘要；失败抛 ExternalDependencyError。"""
    if not base_url or not model or not api_key:
        raise ExternalDependencyError("请填写 API 地址、模型和密钥。")
    body = _post_chat(
        base_url,
        model,
        api_key,
        [{"role": "user", "content": "ping"}],
        temperature=0,
        json_mode=False,
        timeout=20,
    )
    try:
        return body["choices"][0]["message"]["content"][:200]
    except Exception as e:
        raise ExternalDependencyError(f"模型响应异常: {e}")
