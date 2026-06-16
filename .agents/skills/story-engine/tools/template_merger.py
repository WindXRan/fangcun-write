"""
模板合并工具：把 AI 输出的带标签内容填入模板。

用法：
  python template_merger.py --template templates/plot-guide-output.md --content output.txt --output plot_1.md
  
  # 在代码中使用
  from template_merger import merge_tagged_output
  result = merge_tagged_output(template_path, ai_output)
"""

import re
import argparse
from pathlib import Path


def load_template(template_path):
    """加载模板文件。"""
    return Path(template_path).read_text(encoding='utf-8')


def parse_tagged_output(text):
    """解析带标签的 AI 输出。
    
    格式：
      标签：内容
      标签：
      内容（续行）
      ...
    
    返回：
      {标签: 内容} 字典
    """
    result = {}
    current_tag = None
    current_content = []
    
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # 检查是否是标签行（标签：内容 或 标签:内容）
        # 支持加粗标记（**标签：**）
        # 标签名不能以特殊字符开头，必须是中文/英文/数字
        match = re.match(r'^(?:\*\*)?([a-zA-Z\u4e00-\u9fa5][a-zA-Z0-9\u4e00-\u9fa5]*)(?:\*\*)?(?:\*\*)?[：:](?:\*\*)?\s*(.*)', line)
        if match:
            # 保存之前的标签内容
            if current_tag:
                result[current_tag] = '\n'.join(current_content).strip()
            
            # 开始新标签
            current_tag = match.group(1).strip()
            content_part = match.group(2).strip()
            current_content = [content_part] if content_part else []
        elif current_tag:
            # 继续当前标签的内容
            current_content.append(line)
    
    # 保存最后一个标签
    if current_tag:
        result[current_tag] = '\n'.join(current_content).strip()
    
    return result


def merge_tagged_output(template_path, ai_output):
    """把 AI 输出的带标签内容填入模板。
    
    Args:
        template_path: 模板文件路径
        ai_output: AI 输出的文本（带标签格式）
    
    Returns:
        合并后的文本
    """
    template = load_template(template_path)
    
    # 解析带标签输出
    tags = parse_tagged_output(ai_output)
    
    # 替换模板中的占位符
    result = template
    for tag, content in tags.items():
        placeholder = f'{{{tag}}}'
        if placeholder in result:
            # 去掉 AI 输出中的表格头（避免与模板中的表格头重复）
            cleaned_content = _remove_table_header(content)
            result = result.replace(placeholder, cleaned_content)
    
    return result


def _remove_table_header(content):
    """去掉内容开头的表格头（|...|...|格式的行和分隔行）。"""
    lines = content.split('\n')
    # 跳过开头的表格头行
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 跳过表格头行（以 | 开头的行）
        if stripped.startswith('|') and i < 3:
            start = i + 1
        # 跳过分隔行（|---|---|格式）
        elif re.match(r'^\|[\s\-|]+\|$', stripped):
            start = i + 1
        else:
            break
    return '\n'.join(lines[start:]).strip()


def merge_lines_to_template(template_path, lines):
    """把 AI 输出的行按顺序填入模板（兼容旧接口）。"""
    template = load_template(template_path)
    
    if isinstance(lines, str):
        lines = lines.strip().split('\n')
    
    result = template
    for i, line in enumerate(lines, 1):
        placeholder = f'{{{i}}}'
        if placeholder in result:
            result = result.replace(placeholder, line.strip())
    
    return result


def merge_json_to_template(template_path, json_content):
    """把 JSON 内容填入模板（兼容旧接口）。"""
    import json
    template = load_template(template_path)
    
    if isinstance(json_content, str):
        json_content = json.loads(json_content)
    
    result = template
    for key, value in json_content.items():
        if isinstance(value, str):
            result = result.replace(f'{{{key}}}', value)
        elif isinstance(value, list):
            result = result.replace(f'{{{key}}}', '\n'.join(str(v) for v in value))
    
    return result


def main():
    parser = argparse.ArgumentParser(description='模板合并工具')
    parser.add_argument('--template', required=True, help='模板文件路径')
    parser.add_argument('--content', required=True, help='AI输出内容文件路径')
    parser.add_argument('--output', required=True, help='输出文件路径')
    parser.add_argument('--format', choices=['tagged', 'lines', 'json'], default='tagged', help='内容格式')
    args = parser.parse_args()
    
    content = Path(args.content).read_text(encoding='utf-8')
    
    if args.format == 'tagged':
        result = merge_tagged_output(args.template, content)
    elif args.format == 'json':
        result = merge_json_to_template(args.template, content)
    else:
        result = merge_lines_to_template(args.template, content)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result, encoding='utf-8')
    
    print(f"[OK] 合并完成: {args.output}")


if __name__ == '__main__':
    main()
