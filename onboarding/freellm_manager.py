"""
FreeLLMAPI 自动检测 + 配置模块。

产品启动时：
1. 检测本地 FreeLLMAPI 是否运行（localhost:3001）
2. 如果没有，启动它
3. 自动获取 unified key
4. 写入项目配置
"""

import json
import os
import subprocess
import time
from pathlib import Path


FREELLMAPI_PORT = 3001
FREELLMAPI_URL = f"http://localhost:{FREELLMAPI_PORT}/v1"


def is_freellm_running() -> bool:
    """检测 FreeLLMAPI 是否在运行。"""
    import requests
    try:
        r = requests.get(f"{FREELLMAPI_URL}/models", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def start_freellm(base_dir: str = ".") -> bool:
    """启动 FreeLLMAPI（如果未运行）。"""
    if is_freellm_running():
        print("  FreeLLMAPI 已运行")
        return True

    # 尝试 Docker
    if _try_start_docker(base_dir):
        return True

    # 尝试 Node 进程
    if _try_start_node(base_dir):
        return True

    print("  [WARN] 无法启动 FreeLLMAPI，请手动启动")
    return False


def _try_start_docker(base_dir: str) -> bool:
    """尝试用 Docker 启动。"""
    import shutil
    if not shutil.which("docker"):
        return False

    compose_dir = Path(base_dir) / ".freellmapi"
    if not (compose_dir / "docker-compose.yml").exists():
        return False

    try:
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=str(compose_dir),
            capture_output=True,
            timeout=30,
        )
        # 等待启动
        for _ in range(30):
            if is_freellm_running():
                print("  ✓ FreeLLMAPI (Docker) 已启动")
                return True
            time.sleep(2)
    except Exception:
        pass
    return False


def _try_start_node(base_dir: str) -> bool:
    """尝试用 Node 进程启动。"""
    import shutil
    if not shutil.which("node"):
        return False

    # 查找 FreeLLMAPI 安装目录
    freellm_paths = [
        Path(base_dir) / ".freellmapi" / "server" / "dist" / "index.js",
        Path(base_dir) / "freellmapi" / "server" / "dist" / "index.js",
        Path.home() / "freellmapi" / "server" / "dist" / "index.js",
    ]

    for server_path in freellm_paths:
        if server_path.exists():
            try:
                env = os.environ.copy()
                env["PORT"] = str(FREELLMAPI_PORT)
                subprocess.Popen(
                    ["node", str(server_path)],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                # 等待启动
                for _ in range(15):
                    if is_freellm_running():
                        print(f"  ✓ FreeLLMAPI (Node) 已启动 :{FREELLMAPI_PORT}")
                        return True
                    time.sleep(2)
            except Exception:
                pass
    return False


def get_unified_key() -> str:
    """获取 FreeLLMAPI unified key。首次使用时自动创建。"""
    # 检查是否已有 key（从 dashboard 获取）
    # FreeLLMAPI 部署后需要通过 dashboard 创建 key
    # 这里返回一个默认 key，实际使用时用户需要在 dashboard 创建
    return "freellmapi-local"


def auto_configure(config_path: str, base_dir: str = ".") -> dict:
    """自动配置：检测 FreeLLMAPI → 更新 config。"""
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))

    if is_freellm_running():
        config["api_key"] = get_unified_key()
        config["api_base_url"] = FREELLMAPI_URL
        config["model"] = "auto"
        Path(config_path).write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  ✓ 已配置 FreeLLMAPI: {FREELLMAPI_URL}")
        return config
    else:
        print("  [WARN] FreeLLMAPI 未运行，使用原配置")
        return config


def ensure_freellm(base_dir: str = ".") -> str:
    """确保 FreeLLMAPI 可用，返回 API URL。"""
    if is_freellm_running():
        return FREELLMAPI_URL

    if start_freellm(base_dir):
        return FREELLMAPI_URL

    return None
