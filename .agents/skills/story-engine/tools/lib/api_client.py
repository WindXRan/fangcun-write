"""API 客户端：带指数退避重试的 DeepSeek API 调用。"""

import os
import time
import requests

DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"


def call_llm(config, prompt_type, user_prompt, system_prompt=None):
    """统一 LLM 调用入口。

    从 prompt 的 frontmatter + config.prompt_overrides 读取模型参数，
    自动处理 api_key / api_url / model / temperature / max_tokens / reasoning_effort。

    Args:
        config: 项目配置字典
        prompt_type: prompt 文件名（如 "plot-guide", "write-chapter"）
        user_prompt: 已格式化的用户 prompt 文本
        system_prompt: 可选的 system prompt 覆盖

    Returns:
        str: API 返回文本

    Raises:
        ValueError: API_KEY 未配置
        Exception: API 调用失败
    """
    from prompt_loader import get_prompt_config_with_overrides, load_system_prompt, get_system_prompt_name

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY，请设置 $env:API_KEY 或 config.api_key")

    api_url = get_api_url(config)
    pc = get_prompt_config_with_overrides(f"{prompt_type}.md", config)
    model = pc.get("model", "deepseek-v4-pro")
    temperature = pc.get("temperature", 0.8)
    max_tokens = pc.get("max_tokens", 8192)
    reasoning_effort = pc.get("reasoning_effort", "high")

    if not system_prompt:
        sp_name = get_system_prompt_name(f"{prompt_type}.md") or "system-generic.md"
        system_prompt = load_system_prompt(sp_name) or ""

    return call_api(api_key, model, user_prompt, reasoning_effort, max_tokens,
                    system_prompt, api_url, temperature=temperature)


def get_api_url(config=None):
    """获取 API URL，确保包含 /v1。"""
    base = None
    if config and config.get("api_base_url"):
        base = config["api_base_url"].rstrip("/")
    elif os.environ.get("API_BASE_URL"):
        base = os.environ.get("API_BASE_URL").rstrip("/")
    if base:
        if not base.endswith("/v1"):
            base = base + "/v1"
        return base + "/chat/completions"
    return DEFAULT_API_URL


def get_api_key(config=None):
    """获取 API Key。"""
    if config and config.get("api_key"):
        return config["api_key"]
    return os.environ.get("API_KEY")


def call_api(api_key, model, user_prompt, reasoning_effort="low",
             max_tokens=8192, system_prompt=None, api_url=None, max_retries=3,
             temperature=0.8):
    """调用 API，带指数退避重试。

    Args:
        temperature: 默认 0.8。审稿推荐 0.3，修复推荐 0.6。

    重试策略：
    - 429 (限流): 指数退避 10/20/40 秒
    - 5xx (服务端错误): 指数退避 5/10/20 秒
    - 超时: 重试，超时时间翻倍
    - 其他错误: 不重试
    """
    from prompt_loader import load_system_prompt

    url = api_url or DEFAULT_API_URL
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    sys_prompt = system_prompt or load_system_prompt("system-generic.md") or ""
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # reasoning_effort 仅对 reasoning 模型生效
    if reasoning_effort:
        data["reasoning_effort"] = reasoning_effort

    timeout = 120

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=timeout)

            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]

            if resp.status_code == 429:
                wait = 10 * (2 ** attempt)
                print(f"    [429] 限流，等待 {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code >= 500:
                wait = 5 * (2 ** attempt)
                print(f"    [{resp.status_code}] 服务端错误，等待 {wait}s...")
                time.sleep(wait)
                continue

            # 其他错误不重试
            raise Exception(f"API 错误 {resp.status_code}: {resp.text[:200]}")

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                timeout *= 2
                print(f"    [TIMEOUT] 超时，重试 (timeout={timeout}s)...")
                continue
            raise

        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                wait = 5 * (2 ** attempt)
                print(f"    [CONN] 连接失败，等待 {wait}s...")
                time.sleep(wait)
                continue
            raise

    raise Exception(f"API 调用失败，已重试 {max_retries} 次")


def test_api_connection(config=None, timeout=10):
    """测试 API 连接是否正常。
    
    Returns:
        dict: {
            "success": bool,
            "url": str,
            "model": str,
            "latency_ms": float or None,
            "error": str or None
        }
    """
    import requests
    
    api_key = get_api_key(config)
    api_url = get_api_url(config)
    model = (config or {}).get("model", "deepseek-v4-pro")
    
    if not api_key:
        return {
            "success": False,
            "url": api_url,
            "model": model,
            "latency_ms": None,
            "error": "未配置 API_KEY"
        }
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": "test"}
        ],
        "max_tokens": 5,
    }
    
    try:
        start_time = time.time()
        resp = requests.post(api_url, headers=headers, json=data, timeout=timeout)
        latency_ms = (time.time() - start_time) * 1000
        
        if resp.status_code == 200:
            return {
                "success": True,
                "url": api_url,
                "model": model,
                "latency_ms": round(latency_ms, 2),
                "error": None
            }
        else:
            return {
                "success": False,
                "url": api_url,
                "model": model,
                "latency_ms": round(latency_ms, 2),
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}"
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "url": api_url,
            "model": model,
            "latency_ms": None,
            "error": f"连接超时 ({timeout}s)"
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "url": api_url,
            "model": model,
            "latency_ms": None,
            "error": f"连接失败: {str(e)[:200]}"
        }
    except Exception as e:
        return {
            "success": False,
            "url": api_url,
            "model": model,
            "latency_ms": None,
            "error": f"未知错误: {str(e)[:200]}"
        }

