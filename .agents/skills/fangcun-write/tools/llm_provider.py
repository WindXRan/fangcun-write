"""LLM 调用接口。"""
import os, json
from urllib.request import Request, urlopen

def call_llm(messages: list, temperature: float = 0.7):
    """调用 LLM。"""
    api_key = os.environ.get("API_KEY", "") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    if not api_key:
        return None, "未设置 API_KEY"
    _base = os.environ.get("API_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    if not _base.endswith("/v1"):
        _base += "/v1"
    api_url = _base + "/chat/completions"
    model = os.environ.get("FANGCUN_MODEL", "deepseek-v4-pro")
    body = json.dumps({"model": model, "messages": messages, "temperature": temperature}).encode()
    req = Request(api_url, data=body, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=180) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, str(e)


# ─── 项目初始化 ──────────────────────────────────────────

