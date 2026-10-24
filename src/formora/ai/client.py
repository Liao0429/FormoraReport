"""OpenAI 兼容 API 客户端。

- 仅用户主动启用 AI 模式时使用。
- 密钥从 Config（DPAPI 加密）读取，不明文落盘。
- 结构化输出：要求模型返回 JSON，并解析。
- 防捏造：prompt 明确要求无依据内容标为「待补充/待确认」。
"""
from __future__ import annotations

import json
import urllib.request

from formora.core.errors import ExternalDependencyError
from formora.services.config import Config

_CHAT_COMPLETIONS_SUFFIX = "/chat/completions"


def is_configured(config: Config) -> bool:
    ai = config.get("ai", {}) or {}
    return bool(ai.get("enabled")) and bool(config.get_ai_api_key()) and bool(ai.get("base_url"))


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
    base_url = base_url.rstrip("/")
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
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ExternalDependencyError(f"AI 请求失败: {e}")


def _chat_json(config: Config, messages: list[dict], temperature: float = 0.2) -> dict:
    ai = config.get("ai", {})
    base_url = (ai.get("base_url") or "").rstrip("/")
    model = ai.get("model") or ""
    api_key = config.get_ai_api_key()
    if not base_url or not model or not api_key:
        raise ExternalDependencyError("AI 配置不完整，请检查 API 地址、模型与密钥。")

    body = _post_chat(base_url, model, api_key, messages, temperature=temperature)
    try:
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        raise ExternalDependencyError(f"AI 返回无法解析为 JSON: {e}")


SYSTEM_PROMPT = (
    "你是一名严谨的实验报告辅助助手。你根据用户提供的实验模板字段与原始素材，"
    "抽取每个字段的内容。规则：\n"
    "1. 只能依据素材中的内容填写，不得编造实验数据、现象、测量结果、参考文献或过程。\n"
    "2. 若某字段在素材中没有依据，value 必须为“待补充”，并置 needs_confirmation=true。\n"
    "3. 对整理生成的内容，在 source 中注明依据（文件名/段落/表格）。\n"
    "4. 返回严格 JSON，格式为 {\"fields\":[{\"field\":\"字段名\",\"value\":\"内容\","
    "\"source\":\"依据\",\"needs_confirmation\":true/false}]}。"
)


def extract_fields(config: Config, materials_text: str, template_fields: list[str]) -> list[dict]:
    """从素材中抽取模板字段内容。返回 [{field, value, source, needs_confirmation}]"""
    if not is_configured(config):
        raise ExternalDependencyError("AI 模式未启用或未配置，请先在 AI 设置中配置。")
    user_msg = (
        f"模板字段：{json.dumps(template_fields, ensure_ascii=False)}\n\n"
        f"原始素材：\n{materials_text[:60000]}"
    )
    result = _chat_json(config, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ])
    return result.get("fields", [])


def review_report(config: Config, report_text: str) -> list[dict]:
    """审查报告内容，检查缺失、矛盾、疑似捏造。返回 [{field, issue, severity}]"""
    if not is_configured(config):
        raise ExternalDependencyError("AI 模式未启用或未配置，请先在 AI 设置中配置。")
    user_msg = (
        "请审查以下实验报告。检查：缺失字段、前后矛盾、疑似无依据的数据。\n"
        "对每个问题返回 {\"issues\":[{\"field\":\"字段\",\"issue\":\"问题描述\","
        "\"severity\":\"error|warning\"}]}。没有问题则返回 {\"issues\":[]}。\n\n"
        f"报告内容：\n{report_text[:60000]}"
    )
    result = _chat_json(config, [
        {"role": "system", "content": "你是一名严谨的报告审查者，只依据给定内容判断，不臆测。"},
        {"role": "user", "content": user_msg},
    ])
    return result.get("issues", [])


def test_connection(base_url: str, model: str, api_key: str) -> str:
    """用一次最小请求验证 API 连接。成功返回模型响应摘要；失败抛 ExternalDependencyError。"""
    if not base_url or not model or not api_key:
        raise ExternalDependencyError("请填写 API 地址、模型和密钥。")
    body = _post_chat(
        base_url, model, api_key,
        [{"role": "user", "content": "ping"}],
        temperature=0, json_mode=False, timeout=20,
    )
    try:
        return body["choices"][0]["message"]["content"][:200]
    except Exception as e:
        raise ExternalDependencyError(f"模型响应异常: {e}")