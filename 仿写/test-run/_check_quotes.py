import re
with open("C:/Users/Administrator/Documents/trae_projects/AI网文小说项目/仿写/test-run/_src_ch1.txt", "r", encoding="utf-8") as f:
    text = f.read()

# find all unique chars that look like quotes
for i, c in enumerate(text):
    cp = ord(c)
    if cp in (0x201C, 0x201D, 0x2018, 0x2019, 0x300C, 0x300D, 0xFF02):
        ctx = text[max(0,i-10):i+10]
        print(f"pos={i} U+{cp:04X} {c!r} ctx={ctx!r}")
        break

# count chinese chars
chinese_total = len(re.findall(r'[\u4e00-\u9fff]', text))

# try each quote pattern
for name, pattern in [
    ("\u201c\u201d", re.compile(r'\u201c([^\u201d]*)\u201d')),
    ("\u2018\u2019", re.compile(r'\u2018([^\u2019]*)\u2019')),
    ("\u300c\u300d", re.compile(r'\u300c([^\u300d]*)\u300d')),
    ('"" ASCII', re.compile(r'"([^"]*)"')),
]:
    in_q = 0
    count = 0
    for m in pattern.finditer(text):
        in_q += len(re.findall(r'[\u4e00-\u9fff]', m.group(1)))
        count += 1
    pct = in_q / chinese_total * 100 if chinese_total > 0 else 0
    print(f"{name}: {count} matches, {in_q} chars, {pct:.1f}%")

# total from style_analyzer approach
total_in_quotes = 0
for name, pattern in [
    ("\u201c\u201d", re.compile(r'\u201c([^\u201d]*)\u201d')),
    ("\u2018\u2019", re.compile(r'\u2018([^\u2019]*)\u2019')),
    ("\u300c\u300d", re.compile(r'\u300c([^\u300d]*)\u300d')),
    ('"" ASCII', re.compile(r'"([^"]*)"')),
    ("\u2014\u2014", re.compile(r'\u2014\u2014([^\u2014\u2014]*)\u2014\u2014')),
]:
    for m in pattern.finditer(text):
        total_in_quotes += len(re.findall(r'[\u4e00-\u9fff]', m.group(1)))
print(f"\nTotal from style_analyzer approach: {total_in_quotes}/{chinese_total} = {total_in_quotes/chinese_total*100:.1f}%")

# actually just run style_analyzer
import sys
sys.path.insert(0, "C:/Users/Administrator/Documents/trae_projects/AI网文小说项目/.agents/skills/story-engine/tools")
from style_analyzer import analyze_style
prof = analyze_style(text)
print(f"\nstyle_analyzer 对话占比: {prof['dialogue_ratio']*100:.1f}%")
print(f"dialogue_chars: {prof['dialogue_ratio'] * chinese_total:.0f}")
print(f"total_chinese: {chinese_total}")
