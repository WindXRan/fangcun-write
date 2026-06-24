"""
自动生成配置文件
用户说"帮我仿写这本书"或"用XXX的风格写"，系统自动创建配置
"""

import json
import os
from pathlib import Path


def create_imitation_config(source_book, author, book_name=None, model="deepseek-chat"):
    """创建仿写配置（章对章仿写）。
    
    Args:
        source_book: 源书名
        author: 作者名
        book_name: 新书名（可选，默认自动生成）
        model: 使用的模型
    
    Returns:
        配置文件路径
    """
    base_dir = os.getcwd()
    
    # 自动生成新书名
    if not book_name:
        book_name = f"{source_book}仿写"
    
    # 构建路径
    rewrites_dir = f"projects/{author}/{source_book}/rewrites/{book_name}"
    
    # 创建目录
    os.makedirs(rewrites_dir, exist_ok=True)
    os.makedirs(os.path.join(rewrites_dir, "chapters"), exist_ok=True)
    os.makedirs(os.path.join(rewrites_dir, "guides"), exist_ok=True)
    os.makedirs(os.path.join(rewrites_dir, "compare"), exist_ok=True)
    
    # 创建配置
    config = {
        "base_dir": base_dir,
        "author": author,
        "source_book": source_book,
        "book_name": book_name,
        "rewrites_dir": rewrites_dir,
        "api_key": None,
        "api_base_url": "https://api.deepseek.com/v1",
        "model": model,
        "execution_mode": "api"
    }
    
    # 保存配置
    config_path = f"configs/imitate_{book_name}.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 仿写配置已创建: {config_path}")
    print(f"   源书: {source_book}")
    print(f"   新书: {book_name}")
    print(f"   输出: {rewrites_dir}")
    
    return config_path


def create_avatar_config(author_name, source_dir=None, model="deepseek-chat"):
    """创建分身配置（作者风格写作）。
    
    Args:
        author_name: 作者名
        source_dir: 源文目录（可选，用于自动蒸馏）
        model: 使用的模型
    
    Returns:
        配置文件路径
    """
    base_dir = os.getcwd()
    
    # 检查 knowledge 目录中是否存在作者数据
    knowledge_dir = f"knowledge/{author_name}"
    if not os.path.exists(knowledge_dir):
        print(f"❌ 作者知识库不存在: {knowledge_dir}")
        print(f"   请先使用 /fangcun-analyze 拆解作者作品")
        return None
    
    # 查找作者的 system_prompt
    system_prompt_path = None
    for book_dir in Path(knowledge_dir).iterdir():
        if book_dir.is_dir():
            sp = book_dir / "system_prompt.md"
            if sp.exists():
                system_prompt_path = str(sp)
                break
    
    # 创建配置
    config = {
        "base_dir": base_dir,
        "author": author_name,
        "book_name": f"{author_name}新作",
        "rewrites_dir": f"projects/{author_name}/新书",
        "api_key": None,
        "api_base_url": "https://api.deepseek.com/v1",
        "model": model,
        "execution_mode": "api",
        "mode": "avatar",
        "knowledge_dir": knowledge_dir,
        "system_prompt_path": system_prompt_path or ""
    }
    
    # 保存配置
    config_path = f"configs/avatar_{author_name}.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 分身配置已创建: {config_path}")
    print(f"   作者: {author_name}")
    print(f"   知识库: {knowledge_dir}")
    
    return config_path


def auto_create_config(user_input, source_path=None):
    """根据用户输入自动创建配置。
    
    Args:
        user_input: 用户输入（如"帮我仿写这本书"、"用午夜凶球的风格写"）
        source_path: 源文路径（可选）
    
    Returns:
        配置文件路径
    """
    # 解析用户意图
    if "仿写" in user_input:
        # 仿写模式
        if source_path:
            # 从路径提取信息
            parts = source_path.replace('\\', '/').split('/')
            if 'projects' in parts:
                idx = parts.index('projects')
                if idx + 2 < len(parts):
                    author = parts[idx + 1]
                    source_book = parts[idx + 2]
                    return create_imitation_config(source_book, author)
        
        print("❌ 无法解析源文路径，请提供完整路径")
        return None
    
    elif "风格" in user_input or "分身" in user_input:
        # 分身模式
        # 从输入中提取作者名
        import re
        author_match = re.search(r'用(.+?)的风格', user_input)
        if author_match:
            author_name = author_match.group(1)
            return create_avatar_config(author_name)
        
        print("❌ 无法解析作者名，请说'用XXX的风格写'")
        return None
    
    else:
        print("❌ 无法识别意图，请说'帮我仿写这本书'或'用XXX的风格写'")
        return None


if __name__ == "__main__":
    # 测试
    import sys
    
    if len(sys.argv) > 1:
        user_input = sys.argv[1]
        source_path = sys.argv[2] if len(sys.argv) > 2 else None
        auto_create_config(user_input, source_path)
    else:
        print("用法: python config_generator.py '帮我仿写这本书' [源文路径]")
