"""API 客户端：带指数退避重试的 MiMo API 调用。"""

import os
import time
from pathlib import Path
import requests
from datetime import datetime

DEFAULT_API_URL = os.environ.get("DEFAULT_API_URL", "https://token-plan-cn.xiaomimimo.com/v1/chat/completions")


def call_llm(config, prompt_type, user_prompt, system_prompt=None, ch=None, max_tokens=None):
    """统一 LLM 调用入口。

    从 prompt 的 frontmatter + config.prompt_overrides 读取模型参数，
    自动处理 api_key / api_url / model / temperature。

    Args:
        config: 项目配置字典
        prompt_type: prompt 文件名（如 "plot-guide", "write-chapter"）
        user_prompt: 已格式化的用户 prompt 文本
        system_prompt: 可选的 system prompt 覆盖
        ch: 可选，当前章节号（用于 token 日志）
        max_tokens: 可选，最大输出 token 数（覆盖 prompt 配置）

    Returns:
        str: API 返回文本

    Raises:
        ValueError: API_KEY 未配置
        Exception: API 调用失败
    """
    from prompt_meta import get_prompt_config_with_overrides, load_system_prompt, get_system_prompt_name

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY，请设置环境变量 API_KEY 或 config.api_key")

    api_url = get_api_url(config)
    provider = config.get("provider", "")
    pc = get_prompt_config_with_overrides(f"{prompt_type}.md", config)
    # 优先级：config.json 的 model > prompt defaults 的 model > 默认值
    model = config.get("model") or pc.get("model") or "mimo-v2.5-pro"
    temperature = pc.get("temperature", 0.8)
    if max_tokens is None:
        max_tokens = pc.get("max_tokens", None)

    if not system_prompt:
        sp_name = get_system_prompt_name(f"{prompt_type}.md") or "system-generic.md"
        system_prompt = load_system_prompt(sp_name) or ""

    rewrites_dir = config.get("rewrites_dir", "")
    usage_log_path = str(Path(rewrites_dir) / "_log/api_usage.jsonl") if rewrites_dir else ""

    content, usage = call_api(api_key, model, user_prompt,
                              system_prompt, api_url, temperature=temperature,
                              max_tokens=max_tokens,
                              return_usage=True, provider=provider)

    if usage and rewrites_dir:
        try:
            from lib.token_tracker import log_usage
            log_usage(rewrites_dir, {
                "prompt_type": prompt_type,
                "ch": ch,
                "model": model,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            })
        except Exception:
            pass

    return content


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


def call_api(api_key, model, user_prompt,
             system_prompt=None, api_url=None, max_retries=3,
             temperature=0.8, max_tokens=None, return_usage=False, provider=None):
    """调用 API，带指数退避重试。

    Args:
        temperature: 默认 0.8。审稿推荐 0.3，修复推荐 0.6。
        max_tokens: 最大输出 token 数。None 表示不限制。
        return_usage: 是否返回 (content, usage_dict) 元组。
        provider: API 提供商（"deepseek", "openai", "mimo" 等）

    Returns:
        str 或 (str, dict): 返回内容。return_usage=True 时额外返回 usage。

    重试策略：
    - 429 (限流): 指数退避 10/20/40 秒
    - 5xx (服务端错误): 指数退避 5/10/20 秒
    - 402 (余额不足): 立即停止，不重试
    - 超时: 重试，超时时间翻倍
    - 其他错误: 不重试
    """
    from prompt_meta import load_system_prompt

    url = api_url or DEFAULT_API_URL

    # 认证格式：MiMo 用 api-key，其他用 Authorization: Bearer
    if "mimo" in url or "xiaomimimo" in url:
        headers = {"api-key": api_key, "Content-Type": "application/json"}
    else:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    sys_prompt = system_prompt or load_system_prompt("system-generic.md") or ""
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
    }
    if max_tokens:
        data["max_tokens"] = max_tokens

    timeout = 300  # 初始超时 5 分钟

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=timeout)

            if resp.status_code == 200:
                body = resp.json()
                content = body["choices"][0]["message"]["content"]
                usage = body.get("usage", {})
                if return_usage:
                    return content, usage
                return content

            # 402 余额不足 - 立即停止
            if resp.status_code == 402:
                error_msg = resp.text[:200]
                raise Exception(f"余额不足，请充值后重试: {error_msg}")

            # 401 认证失败 - 立即停止
            if resp.status_code == 401:
                error_msg = resp.text[:200]
                raise Exception(f"API Key 无效: {error_msg}")

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
            raise Exception(f"请求超时，已重试 {max_retries} 次")

        except requests.exceptions.ConnectionError as e:
            # 连接失败 - 快速失败，不重试（可能是断网）
            raise Exception(f"连接失败，请检查网络: {str(e)[:100]}")

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
    
    # 根据 provider 选择不同的 header 格式
    provider = (config or {}).get("provider", "")
    if provider == "deepseek" or "deepseek" in api_url:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    else:
        headers = {"api-key": api_key, "Content-Type": "application/json"}
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

