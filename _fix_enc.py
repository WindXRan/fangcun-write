from pathlib import Path

d = Path(".prompts/user")
problem_files = ["写章纲.md", "分析.md", "审查.md", "开书.md", "骨架映射.md"]

for name in problem_files:
    f = d / name
    if not f.exists():
        print(f"{name}: NOT FOUND")
        continue
    
    raw = f.read_bytes()
    
    # 尝试不同编码
    for enc in ["gbk", "gb2312", "gb18030", "latin-1"]:
        try:
            text = raw.decode(enc)
            # 验证解码结果是否合理（包含中文）
            if any('\u4e00' <= c <= '\u9fff' for c in text):
                f.write_text(text, encoding="utf-8")
                print(f"{name}: fixed ({enc} -> utf-8)")
                break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        print(f"{name}: could not fix")
