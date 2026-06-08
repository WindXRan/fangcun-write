"""提取源文风格指标（脚本，不靠LLM）"""
import re
import sys
from pathlib import Path

# 设置stdout为UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')


def extract_metrics(text):
    """提取源文风格指标"""
    # 去除空白
    clean = re.sub(r'\s', '', text)
    total_chars = len(clean)
    
    # 分句（按句号、问号、感叹号、省略号分）
    sentences = re.split(r'[。！？…]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    total_sentences = len(sentences)
    
    # 平均句长
    avg_sentence_len = total_chars / total_sentences if total_sentences > 0 else 0
    
    # 对话占比（引号内的内容）
    dialogue_chars = 0
    # 匹配中文引号（简化版）
    for match in re.finditer(r'\u201c([^\u201d]*)\u201d', text):
        dialogue_chars += len(re.sub(r'\s', '', match.group(1)))
    dialogue_ratio = dialogue_chars / total_chars * 100 if total_chars > 0 else 0
    
    # 短句占比（≤15字）
    short_sentences = sum(1 for s in sentences if len(re.sub(r'\s', '', s)) <= 15)
    short_ratio = short_sentences / total_sentences * 100 if total_sentences > 0 else 0
    
    # 长句占比（≥30字）
    long_sentences = sum(1 for s in sentences if len(re.sub(r'\s', '', s)) >= 30)
    long_ratio = long_sentences / total_sentences * 100 if total_sentences > 0 else 0
    
    # 最长句
    longest = max(sentences, key=lambda s: len(re.sub(r'\s', '', s))) if sentences else ""
    longest_len = len(re.sub(r'\s', '', longest))
    
    return {
        "total_chars": total_chars,
        "total_sentences": total_sentences,
        "avg_sentence_len": round(avg_sentence_len, 1),
        "dialogue_ratio": round(dialogue_ratio, 1),
        "short_ratio": round(short_ratio, 1),
        "long_ratio": round(long_ratio, 1),
        "longest_sentence": longest[:100],
        "longest_len": longest_len,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_style.py <text_file>")
        sys.exit(1)
    
    text_file = Path(sys.argv[1])
    if not text_file.exists():
        print(f"File not found: {text_file}")
        sys.exit(1)
    
    text = text_file.read_text(encoding='utf-8')
    metrics = extract_metrics(text)
    
    print(f"字数：{metrics['total_chars']}字")
    print(f"句数：{metrics['total_sentences']}句")
    print(f"平均句长：{metrics['avg_sentence_len']}字")
    print(f"对话占比：{metrics['dialogue_ratio']}%")
    print(f"短句（≤15字）占比：{metrics['short_ratio']}%")
    print(f"长句（≥30字）占比：{metrics['long_ratio']}%")
    print(f"最长句：{metrics['longest_len']}字")
