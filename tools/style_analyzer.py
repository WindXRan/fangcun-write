"""源文风格分析 + 生成 style_guide 模板（一键完成）"""
import re
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 修辞模式（与 inkos 一致）
RHETORICAL_PATTERNS = [
    {"name": "比喻(像/如/仿佛)", "regex": r"(?:像|如|仿佛|似)(?:是|同|一般|一样)"},
    {"name": "排比", "regex": r"[，。；]([^，。；]{2,6})[，。；]\1"},
    {"name": "反问", "regex": r"难道|怎么可能|岂不是|何尝不"},
    {"name": "夸张", "regex": r"天崩地裂|惊天动地|翻天覆地|震耳欲聋"},
    {"name": "拟人", "regex": r"[风雨雪月花树草石](?:在|像|仿佛).*?(?:笑|哭|叹|呻|吟|怒|舞)"},
    {"name": "短句节奏", "regex": r"[。！？][^。！？]{1,8}[。！？]"},
]


def extract_metrics(text):
    """提取风格指标"""
    clean = re.sub(r'\s', '', text)
    total_chars = len(clean)
    
    sentences = re.split(r'[。！？\n]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 2]
    
    sent_lens = [len(re.sub(r'\s', '', s)) for s in sentences]
    avg_sent_len = sum(sent_lens) / len(sent_lens) if sent_lens else 0
    sent_len_std = 0
    if len(sent_lens) > 1:
        variance = sum((x - avg_sent_len) ** 2 for x in sent_lens) / len(sent_lens)
        sent_len_std = variance ** 0.5
    
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if len(p.strip()) > 5]
    para_lens = [len(p) for p in paragraphs]
    avg_para_len = sum(para_lens) / len(para_lens) if para_lens else 0
    para_range = {"min": min(para_lens), "max": max(para_lens)} if para_lens else {"min": 0, "max": 0}
    
    chars = re.sub(r'[\s\n\r，。！？、：；""''（）【】《》0-9]', '', text)
    unique_chars = set(chars)
    vocab_diversity = len(unique_chars) / len(chars) if chars else 0
    
    opening_counts = {}
    for s in sentences:
        if len(s) >= 2:
            opening = s[:2]
            opening_counts[opening] = opening_counts.get(opening, 0) + 1
    top_patterns = sorted(opening_counts.items(), key=lambda x: -x[1])[:5]
    top_patterns = [f"{p}({c}次)" for p, c in top_patterns if c >= 3]
    
    rhetorical_features = []
    for pattern in RHETORICAL_PATTERNS:
        matches = re.findall(pattern["regex"], text)
        if len(matches) >= 2:
            rhetorical_features.append(f"{pattern['name']}({len(matches)}处)")
    
    simile_count = len(re.findall(r'(?:像|仿佛|犹如|恍如)', text))
    ai_markers = ['首先', '其次', '然后', '最后', '与此同时', '值得注意的是', '此外']
    ai_marker_count = sum(text.count(w) for w in ai_markers)
    direct_emotion = ['充满了', '感到无比', '心中涌起', '不由得', '不禁']
    direct_emotion_count = sum(text.count(w) for w in direct_emotion)
    ellipsis_count = text.count('……') + text.count('...')
    
    has_said_tag = bool(re.search(r'(?:他|她|我)说|(?:他|她|我)道|(?:他|她|我)问', text))
    emotion_words = ['感到', '心中', '涌起', '不由得', '不禁', '无比']
    has_emotion_words = any(w in text for w in emotion_words)
    
    end_punctuations = {'句号': 0, '问号': 0, '叹号': 0, '引号': 0}
    for p in paragraphs:
        if p.endswith('"') or p.endswith('"'):
            end_punctuations['引号'] += 1
        elif p.endswith('？') or p.endswith('?'):
            end_punctuations['问号'] += 1
        elif p.endswith('！') or p.endswith('!'):
            end_punctuations['叹号'] += 1
        elif p.endswith('。'):
            end_punctuations['句号'] += 1
    
    return {
        "total_chars": total_chars,
        "avg_sentence_len": round(avg_sent_len, 1),
        "sentence_len_std": round(sent_len_std, 1),
        "avg_paragraph_len": round(avg_para_len),
        "paragraph_len_range": para_range,
        "vocabulary_diversity": round(vocab_diversity, 3),
        "top_patterns": top_patterns,
        "rhetorical_features": rhetorical_features,
        "simile_count": simile_count,
        "ai_marker_count": ai_marker_count,
        "direct_emotion_count": direct_emotion_count,
        "ellipsis_count": ellipsis_count,
        "has_said_tag": has_said_tag,
        "has_emotion_words": has_emotion_words,
        "end_punctuations": end_punctuations,
    }


def generate_template(d, chapter_num):
    """生成 style_guide 模板（定量数据 + 占位符）"""
    target = d['total_chars']
    min_chars = int(target * 0.9)
    max_chars = int(target * 1.1)
    
    tag_rule = "源文用「XX说」→ 仿写可用动作/神态替代" if d['has_said_tag'] else "源文无「XX说」→ 仿写禁止，只用动作/神态"
    emotion_rule = "源文有直抒情 → 仿写可少量用（≤2次）" if d['has_emotion_words'] else "源文无直抒情 → 仿写禁止（感到/心中涌起/不由得/不禁）"
    
    ellipsis_count = d['ellipsis_count']
    ellipsis_rule = "源文0个 → 仿写最多1个" if ellipsis_count == 0 else f"源文{ellipsis_count}个 → 仿写最多{ellipsis_count+1}个"
    
    end_p = d['end_punctuations']
    dominant_end = max(end_p, key=end_p.get)
    
    return f"""# 第{chapter_num}章 风格速查

## 定量锚点（自动生成）

| 指标 | 源文值 | 仿写范围 |
|------|--------|----------|
| 总字数 | {d['total_chars']}字 | {min_chars}~{max_chars}字 |
| 平均句长 | {d['avg_sentence_len']}字 | ±20% |
| 句长标准差 | {d['sentence_len_std']} | - |
| 平均段长 | {d['avg_paragraph_len']}字 | - |
| 词汇多样性(TTR) | {d['vocabulary_diversity']} | - |
| 比喻句 | {d['simile_count']}句 | ±2 |
| AI路标词 | {d['ai_marker_count']}次 | **必须0** |
| 省略号 | {ellipsis_count}个 | {ellipsis_rule} |

## 修辞特征（自动生成）

{', '.join(d['rhetorical_features']) if d['rhetorical_features'] else '无特殊修辞'}

## 句首高频模式（自动生成）

{', '.join(d['top_patterns'][:3]) if d['top_patterns'] else '无明显模式'}

## 执行规则（LLM 填充）

### 句式规则
- 平均句长{d['avg_sentence_len']}字，标准差{d['sentence_len_std']}
- 段落长度{d['paragraph_len_range']['min']}~{d['paragraph_len_range']['max']}字
- 段落结尾偏好：{dominant_end}

（LLM 补充：从源文提取 2-3 条具体句式规则，每条含 ✅正向示例 + ❌反向示例）

### 对话规则
- 对话标签：{tag_rule}

（LLM 补充：从源文提取 2 条对话规则，每条含 ✅正向示例 + ❌反向示例）

### 描写规则
- 情绪表达：{emotion_rule}

（LLM 补充：从源文提取 2 条描写规则，每条含 ✅正向示例 + ❌反向示例）

### 防AI检测（自动生成）
- **禁止**：首先/其次/然后/最后/与此同时/此外/值得注意的是
- **禁止**：对仗句式（他不……也不……更不……）

### 字数控制（自动生成）
- 目标：{d['total_chars']}字，范围：{min_chars}~{max_chars}字
"""


def run(src_dir, output_dir):
    """一键分析 + 生成 style_guide 模板"""
    src_path = Path(src_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    files = sorted(src_path.glob("第*章.txt"), key=lambda x: int(re.search(r'(\d+)', x.stem).group(1)))
    
    if not files:
        print(f"未找到章节文件: {src_dir}")
        return
    
    all_metrics = []
    
    for f in files:
        chapter_num = re.search(r'(\d+)', f.stem).group(1)
        text = f.read_text(encoding='utf-8')
        metrics = extract_metrics(text)
        metrics['chapter'] = int(chapter_num)
        metrics['file'] = f.name
        
        # 保存 JSON
        json_file = out_path / f"style_{chapter_num}.json"
        with open(json_file, 'w', encoding='utf-8') as fout:
            json.dump(metrics, fout, ensure_ascii=False, indent=2)
        
        # 生成 style_guide 模板
        template = generate_template(metrics, int(chapter_num))
        template_file = out_path / f"style_{chapter_num}.md"
        template_file.write_text(template, encoding='utf-8')
        
        all_metrics.append(metrics)
    
    print(f"已分析 {len(files)} 章，输出到: {output_dir}")
    print(f"  - JSON: {len(files)} 个")
    print(f"  - style_guide 模板: {len(files)} 个")
    print(f"\n下一步：用 LLM 填充模板中的「LLM 补充」部分")
    print(f"  python tools/fill_style_guides.py <guides目录> [api_key]")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python style_analyzer.py <源文目录> <输出目录>")
        print("Example: python style_analyzer.py projects/奶糖酥/酸涩湿吻/源文 projects/奶糖酥/酸涩湿吻/style_analysis")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
