"""修复台词同构（8字以上连续匹配）"""
import os
import re
import sys
import json
import argparse
from pathlib import Path


def find_plagiarisms(new_text, source_text):
    """查找台词同构（连续8字以上匹配）。"""
    # 清理文本，只保留中文
    new_clean = re.sub(r'[。！？…\n\s]+', '', new_text)
    src_clean = re.sub(r'[。！？…\n\s]+', '', source_text)
    
    # 构建源文8-gram集合
    src_grams = set()
    for i in range(len(src_clean) - 7):
        src_grams.add(src_clean[i:i+8])
    
    # 检测匹配
    plagiarisms = []
    matched_ranges = []
    i = 0
    while i < len(new_clean) - 7:
        gram = new_clean[i:i+8]
        if gram in src_grams:
            # 找到匹配，扩展找最长匹配
            j = i + 8
            while j < len(new_clean) and new_clean[i:j+1] in src_grams:
                j += 1
            match_len = j - i
            # 避免重叠计数
            if not matched_ranges or i >= matched_ranges[-1][1]:
                plagiarisms.append({
                    'text': new_clean[max(0,i-5):i+20],
                    'length': match_len,
                    'position': i
                })
                matched_ranges.append((i, j))
            i = j
        else:
            i += 1
    
    return plagiarisms


def fix_plagiarism(new_text, source_text, api_key, api_url, model):
    """修复台词同构，调用AI重写。"""
    import requests
    
    plagiarisms = find_plagiarisms(new_text, source_text)
    
    if not plagiarisms:
        return new_text, 0
    
    # 构建重写prompt
    plagiarism_list = "\n".join([f"- '{p['text']}...' ({p['length']}字重合)" for p in plagiarisms[:10]])
    
    prompt = f"""请修改以下章节中的台词，消除与源文的雷同。

【雷同台词】
{plagiarism_list}

【原始章节】
{new_text}

【修改要求】
1. 只修改雷同的台词，其他内容保持不变
2. 修改后的台词要保持原有的意思和情感
3. 使用不同的表达方式，避免8字以上连续匹配
4. 直接输出修改后的完整章节，不要解释

【输出】
修改后的完整章节内容。"""
    
    try:
        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是专业网文写手，擅长改写台词避免雷同。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 8000
            },
            timeout=180
        )
        
        if response.status_code == 200:
            fixed_text = response.json()["choices"][0]["message"]["content"]
            
            # 验证修复效果
            remaining = find_plagiarisms(fixed_text, source_text)
            if len(remaining) < len(plagiarisms):
                return fixed_text, len(plagiarisms) - len(remaining)
            else:
                return new_text, 0
        else:
            print(f"    [FAIL] API错误: {response.status_code}")
            return new_text, 0
            
    except Exception as e:
        print(f"    [FAIL] {e}")
        return new_text, 0


def get_source_text(config, ch):
    """获取源文章节文本。"""
    import glob
    author = config.get('author', '')
    source_book = config.get('source_book', '')
    base_dir = config.get('base_dir', '.')
    
    patterns = [
        f"projects/{author}/{source_book}/_cache/chapters/第{ch}章*.txt",
        f"projects/{author}/{source_book}/_cache/chapters/第{ch:03d}章*.txt",
    ]
    
    for pat in patterns:
        for f in sorted(glob.glob(os.path.join(base_dir, pat))):
            return Path(f).read_text(encoding='utf-8')
    
    return None


def main():
    parser = argparse.ArgumentParser(description="修复台词同构")
    parser.add_argument("--config", required=True, help="配置文件")
    parser.add_argument("--start", type=int, default=1, help="起始章")
    parser.add_argument("--end", type=int, default=101, help="结束章")
    parser.add_argument("--dry-run", action="store_true", help="只检测不修复")
    
    args = parser.parse_args()
    
    # 读取配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)
    
    config = json.loads(config_path.read_text(encoding='utf-8'))
    chapters_dir = Path(config['rewrites_dir']) / 'chapters'
    
    # API配置
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = config.get("api_base_url", "https://api.deepseek.com/v1") + "/chat/completions"
    model = config.get("model", "deepseek-chat")
    
    if not api_key:
        print("未配置API_KEY")
        sys.exit(1)
    
    print(f"\n{'=' * 50}")
    print(f"修复台词同构 (ch{args.start}-{args.end})")
    print("=" * 50)
    
    total_fixed = 0
    total_plagiarisms = 0
    
    for ch in range(args.start, args.end + 1):
        ch_file = chapters_dir / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        
        # 获取源文
        source_text = get_source_text(config, ch)
        if not source_text:
            continue
        
        # 检测同构
        new_text = ch_file.read_text(encoding='utf-8')
        plagiarisms = find_plagiarisms(new_text, source_text)
        
        if not plagiarisms:
            continue
        
        total_plagiarisms += len(plagiarisms)
        print(f"  ch{ch:03d}: 发现{len(plagiarisms)}处同构")
        
        if args.dry_run:
            for p in plagiarisms[:3]:
                print(f"    - '{p['text']}...' ({p['length']}字)")
            continue
        
        # 修复
        fixed_text, fixed_count = fix_plagiarism(new_text, source_text, api_key, api_url, model)
        
        if fixed_count > 0:
            ch_file.write_text(fixed_text, encoding='utf-8')
            total_fixed += 1
            print(f"  ch{ch:03d}: 修复{fixed_count}处")
    
    print(f"\n完成：{total_fixed}章被修复，共发现{total_plagiarisms}处同构")


if __name__ == "__main__":
    main()
