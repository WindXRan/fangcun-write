"""
style-distill: 文风蒸馏工具
从源文自动提取风格，生成分身包。
"""

import os
import json
import re
from pathlib import Path


def extract_style_metrics(text):
    """从文本中提取量化风格指标。"""
    # 对话比例
    dialog_lines = len(re.findall(r'["「」""\u201c\u201d]', text))
    total_chars = len(re.sub(r'\s', '', text))
    dialog_ratio = min(dialog_lines * 10 / total_chars, 1.0) if total_chars > 0 else 0
    
    # 句长
    sentences = re.split(r'[。！？.!?]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
    avg_sent_len = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
    
    # 段落
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0
    
    # 单句段
    single_sent_paras = sum(1 for p in paragraphs if len(re.split(r'[。！？.!?]', p)) <= 2)
    single_ratio = single_sent_paras / len(paragraphs) if paragraphs else 0
    
    # 标点
    exclamation = text.count('！') + text.count('!')
    ellipsis = text.count('……') + text.count('...')
    
    return {
        "dialog_ratio": round(dialog_ratio * 100, 1),
        "avg_sentence_length": round(avg_sent_len, 1),
        "avg_paragraph_length": round(avg_para_len, 1),
        "single_sentence_ratio": round(single_ratio * 100, 1),
        "exclamation_per_1000": round(exclamation / (total_chars / 1000), 1) if total_chars > 0 else 0,
        "ellipsis_per_1000": round(ellipsis / (total_chars / 1000), 1) if total_chars > 1000 else 0,
    }


def extract_dialect_words(text):
    """提取方言词汇。"""
    dongbei_words = ['整', '埋汰', '得瑟', '嘚瑟', '嘎嘎', '贼', '老', '咋', '啥', '呗', '嘛', '呢']
    found = []
    for word in dongbei_words:
        count = len(re.findall(word, text))
        if count > 2:
            found.append(f"{word}({count}次)")
    return found


def generate_avatar_prompt(author_name, metrics, dialect_words, examples):
    """生成分身 prompt。"""
    prompt = f"""# {author_name} 的赛博分身

## 你是谁
你是{author_name}的赛博分身。你拥有他/她的写作风格和创作理念。

## 你的写作风格

### 量化锚点
- 对话比例：{metrics['dialog_ratio']}%
- 平均句长：{metrics['avg_sentence_length']}字
- 平均段长：{metrics['avg_paragraph_length']}字
- 单句段比例：{metrics['single_sentence_ratio']}%
- 感叹号密度：{metrics['exclamation_per_1000']}/千字
- 省略号密度：{metrics['ellipsis_per_1000']}/千字

### 方言特色
{', '.join(dialect_words) if dialect_words else '无明显方言'}

### 参考片段
{examples}

## 你可以做的事
1. **模仿写作**：用这个风格写任何内容
2. **讨论技巧**：用这个视角回答写作问题
3. **分析原文**：解释写作手法
4. **续写故事**：保持风格一致地续写
5. **角色扮演**：以这个作者的身份对话
"""
    return prompt


def distill_author(author_name, source_dir, output_dir):
    """从源文蒸馏作者风格。"""
    source_path = Path(source_dir)
    output_path = Path(output_dir) / author_name
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 读取源文
    all_text = ""
    chapter_files = sorted(source_path.glob("*.txt"))
    
    if not chapter_files:
        print(f"❌ 未找到源文文件: {source_dir}")
        return False
    
    # 只读前5章
    for f in chapter_files[:5]:
        try:
            content = f.read_text(encoding='utf-8')
            all_text += content + "\n\n"
        except:
            continue
    
    if not all_text:
        print("❌ 无法读取源文")
        return False
    
    print(f"✅ 读取了 {min(5, len(chapter_files))} 章源文")
    
    # 提取风格指标
    metrics = extract_style_metrics(all_text)
    print(f"✅ 提取了风格指标: 对话{metrics['dialog_ratio']}%, 句长{metrics['avg_sentence_length']}字")
    
    # 提取方言词汇
    dialect_words = extract_dialect_words(all_text)
    print(f"✅ 提取了方言词汇: {', '.join(dialect_words[:3])}...")
    
    # 提取参考片段（取前3段对话）
    dialog_pattern = re.compile(r'["「」""\u201c\u201d].*?["「」""\u201c\u201d]', re.DOTALL)
    dialogs = dialog_pattern.findall(all_text)[:3]
    examples = "\n".join([f"> {d[:100]}..." for d in dialogs]) if dialogs else "无"
    
    # 生成 avatar.md
    avatar_content = generate_avatar_prompt(author_name, metrics, dialect_words, examples)
    avatar_path = output_path / "avatar.md"
    avatar_path.write_text(avatar_content, encoding='utf-8')
    print(f"✅ 生成了 avatar.md")
    
    # 生成 style.md
    style_content = f"""# {author_name} 风格理解

## 量化锚点
- 对话比例：{metrics['dialog_ratio']}%
- 平均句长：{metrics['avg_sentence_length']}字
- 平均段长：{metrics['avg_paragraph_length']}字
- 单句段比例：{metrics['single_sentence_ratio']}%
- 感叹号密度：{metrics['exclamation_per_1000']}/千字
- 省略号密度：{metrics['ellipsis_per_1000']}/千字

## 方言特色
{', '.join(dialect_words) if dialect_words else '无明显方言'}

## 参考片段
{examples}
"""
    style_path = output_path / "style.md"
    style_path.write_text(style_content, encoding='utf-8')
    print(f"✅ 生成了 style.md")
    
    # 生成 emotions.md（占位）
    emotions_content = f"""# {author_name} 情绪模块

## 爽点模式
（待分析）

## 泪点模式
（待分析）

## 笑点模式
（待分析）

## 情绪弧线模板
（待分析）
"""
    emotions_path = output_path / "emotions.md"
    emotions_path.write_text(emotions_content, encoding='utf-8')
    print(f"✅ 生成了 emotions.md（占位）")
    
    # 生成 rhythm.md（占位）
    rhythm_content = f"""# {author_name} 节奏模式

## 章节节奏
（待分析）

## 段落节奏
（待分析）

## 对话节奏
（待分析）

## 情绪节奏
（待分析）
"""
    rhythm_path = output_path / "rhythm.md"
    rhythm_path.write_text(rhythm_content, encoding='utf-8')
    print(f"✅ 生成了 rhythm.md（占位）")
    
    # 生成 voices.md（占位）
    voices_content = f"""# {author_name} 角色声音指南

## 主角
（待分析）

## 配角
（待分析）
"""
    voices_path = output_path / "voices.md"
    voices_path.write_text(voices_content, encoding='utf-8')
    print(f"✅ 生成了 voices.md（占位）")
    
    print(f"\n✅ 分身包已生成: {output_path}")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="文风蒸馏工具")
    parser.add_argument("--author", required=True, help="作者名")
    parser.add_argument("--source", required=True, help="源文目录")
    parser.add_argument("--output", default="avatars", help="输出目录")
    
    args = parser.parse_args()
    
    distill_author(args.author, args.source, args.output)
