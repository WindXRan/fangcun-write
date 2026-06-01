# -*- coding: utf-8 -*-
"""
Style Injection 引擎
从 meta.json + SKILL.md 提取 section 内容，供 story-rewrite 注入 prompt。

用法：
  python extract-injection.py --style=wenqi
  python extract-injection.py --meta=path/to/meta.json
  python extract-injection.py --style=wenqi --keys=voice,rules

输出：JSON 格式的注入内容
"""

import re
import sys
import json
import argparse
from pathlib import Path


def read_file(filepath):
    """读取文件，自动尝试多种编码"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def find_meta_json(style_name):
    """根据风格名查找 meta.json"""
    # 尝试多个可能的路径
    candidates = [
        Path(f"skills/story-style/{style_name}/meta.json"),
        Path(f".claude/skills/story-style/{style_name}/meta.json"),
        Path(f"skills/story-rewrite/styles/{style_name}/meta.json"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def extract_section(content, heading, heading_level=2):
    """从 markdown 提取指定 heading 到下一个同级 heading 之间的内容"""
    prefix = '#' * heading_level
    
    # 构建正则：匹配 heading 行（允许有后缀）
    pattern = rf'^{re.escape(prefix)}\s+{re.escape(heading)}.*$'
    match = re.search(pattern, content, re.MULTILINE)
    
    if not match:
        return None
    
    start = match.end()
    
    # 找下一个同级 heading
    next_heading_pattern = rf'^{re.escape(prefix)}\s+\S'
    next_match = re.search(next_heading_pattern, content[start:], re.MULTILINE)
    
    if next_match:
        end = start + next_match.start()
    else:
        end = len(content)
    
    return content[start:end].strip()


def extract_sub_sections(content, heading, sub_headings):
    """提取指定 heading 下的特定子节内容"""
    section = extract_section(content, heading, heading_level=2)
    if not section:
        return None
    
    if not sub_headings:
        return section
    
    results = []
    for sub_heading in sub_headings:
        sub_content = extract_section(section, sub_heading, heading_level=3)
        if sub_content:
            results.append(f"### {sub_heading}\n{sub_content}")
    
    return '\n\n'.join(results) if results else None


def extract_multi_headings(content, headings, description=""):
    """合并多个 heading 的内容"""
    results = []
    for heading in headings:
        section = extract_section(content, heading, heading_level=2)
        if section:
            results.append(f"## {heading}\n{section}")
    
    return '\n\n'.join(results) if results else None


def validate_injection(meta, skill_content):
    """验证 injection 配置与 SKILL.md 的兼容性"""
    errors = []
    warnings = []
    
    if 'injections' not in meta:
        errors.append("meta.json 缺少 'injections' 字段")
        return errors, warnings
    
    for key, config in meta['injections'].items():
        # 检查 source_heading
        if 'source_heading' in config:
            heading = config['source_heading']
            # 提取 heading 名称（去掉 ## 前缀）
            heading_name = re.sub(r'^##\s+', '', heading)
            if not extract_section(skill_content, heading_name, heading_level=2):
                warnings.append(f"[{key}] source_heading '{heading}' 在 SKILL.md 中不存在")
        
        # 检查 source_headings
        if 'source_headings' in config:
            for heading in config['source_headings']:
                heading_name = re.sub(r'^##\s+', '', heading)
                if not extract_section(skill_content, heading_name, heading_level=2):
                    warnings.append(f"[{key}] source_heading '{heading}' 在 SKILL.md 中不存在")
    
    return errors, warnings


def extract_injections(meta, skill_content, keys=None):
    """执行 injection 提取"""
    result = {}
    
    injections = meta.get('injections', {})
    
    for key, config in injections.items():
        if keys and key not in keys:
            continue
        
        content = None
        
        # 提取逻辑
        if 'source_heading' in config:
            heading = re.sub(r'^##\s+', '', config['source_heading'])
            sub_headings = config.get('source_sub_headings', [])
            
            if sub_headings:
                content = extract_sub_sections(skill_content, heading, sub_headings)
            else:
                content = extract_section(skill_content, heading, heading_level=2)
        
        elif 'source_headings' in config:
            headings = [re.sub(r'^##\s+', '', h) for h in config['source_headings']]
            content = extract_multi_headings(skill_content, headings)
        
        result[key] = {
            'target': config.get('target', ''),
            'content': content,
            'found': content is not None,
            'description': config.get('description', '')
        }
    
    return result


def main():
    import io
    import os
    
    # 设置环境变量确保 UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except AttributeError:
        pass
    
    parser = argparse.ArgumentParser(description='Style Injection 引擎')
    parser.add_argument('--style', help='风格名称（如 wenqi）')
    parser.add_argument('--meta', help='meta.json 路径')
    parser.add_argument('--keys', help='只提取指定的 injection key（逗号分隔）')
    parser.add_argument('--validate', action='store_true', help='只验证，不提取')
    parser.add_argument('--chapter-word-count', action='store_true', help='只输出章数字数配置')
    
    args = parser.parse_args()
    
    # 确定 meta.json 路径
    if args.meta:
        meta_path = Path(args.meta)
    elif args.style:
        meta_path = find_meta_json(args.style)
        if not meta_path:
            print(json.dumps({'error': f'找不到风格 {args.style} 的 meta.json'}, ensure_ascii=False))
            sys.exit(1)
    else:
        parser.error('必须指定 --style 或 --meta')
    
    # 读取 meta.json
    try:
        meta = json.loads(read_file(meta_path))
    except Exception as e:
        print(json.dumps({'error': f'读取 meta.json 失败: {e}'}, ensure_ascii=False))
        sys.exit(1)
    
    # 读取 source_skill
    source_skill_path = meta.get('source_skill', '')
    if not source_skill_path:
        print(json.dumps({'error': 'meta.json 缺少 source_skill 字段'}, ensure_ascii=False))
        sys.exit(1)
    
    # 解析 source_skill 路径（相对于项目根目录）
    skill_path = Path(source_skill_path)
    if not skill_path.exists():
        # 尝试相对于 meta.json 所在目录
        skill_path = meta_path.parent / source_skill_path
    if not skill_path.exists():
        print(json.dumps({'error': f'source_skill 文件不存在: {source_skill_path}'}, ensure_ascii=False))
        sys.exit(1)
    
    skill_content = read_file(skill_path)
    
    # 只输出章数字数配置
    if args.chapter_word_count:
        print(json.dumps(meta.get('chapter_word_count', {}), ensure_ascii=False))
        return
    
    # 验证模式
    if args.validate:
        errors, warnings = validate_injection(meta, skill_content)
        print(json.dumps({
            'style': meta.get('name', 'unknown'),
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }, ensure_ascii=False, indent=2))
        return
    
    # 提取模式
    keys = args.keys.split(',') if args.keys else None
    injections = extract_injections(meta, skill_content, keys)
    
    output = {
        'style': meta.get('name', 'unknown'),
        'label': meta.get('label', ''),
        'source_skill': str(skill_path),
        'chapter_word_count': meta.get('chapter_word_count', {}),
        'features': meta.get('features', {}),
        'injections': injections
    }
    
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
