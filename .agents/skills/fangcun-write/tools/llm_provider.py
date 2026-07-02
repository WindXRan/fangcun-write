"""LLM 调用接口。"""
import os, json
from urllib.request import Request, urlopen

# ─── .env 加载（本地配置，不上传）──────────
_env_loaded = False
def _load_env():
    global _env_loaded
    if _env_loaded:
        return
    # 从当前目录和项目根目录找 .env
    for _root in [os.getcwd(),
                  os.path.dirname(os.path.dirname(os.path.dirname(
                      os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))]:
        _p = os.path.join(_root, ".env")
        if os.path.isfile(_p):
            with open(_p, encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if not _line or _line.startswith("#") or "=" not in _line:
                        continue
                    _k, _v = _line.split("=", 1)
                    _k, _v = _k.strip(), _v.strip().strip("\"'")
                    if _k and _v:  # .env 覆盖已设置的环境变量
                        os.environ[_k] = _v
            break
    _env_loaded = True

def call_llm(messages: list, temperature: float = 0.7):
    """调用 LLM。"""
    _load_env()
    api_key = os.environ.get("API_KEY", "") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    if not api_key:
        return None, "未设置 API_KEY（在 .env 中设置 API_KEY，或参考 .env.example）"
    _base = os.environ.get("API_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    if not _base.endswith("/v1"):
        _base += "/v1"
    api_url = _base + "/chat/completions"
    model = os.environ.get("FANGCUN_MODEL", "deepseek-v4-flash")
    body = json.dumps({"model": model, "messages": messages, "temperature": temperature}).encode()
    req = Request(api_url, data=body, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=180) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, str(e)


# ─── 项目初始化 ──────────────────────────────────────────

