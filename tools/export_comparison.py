"""把四版输出+源文整理成并排对比，供人工审读"""
import sys
from pathlib import Path

AB_DIR = Path('projects/今入画/执掌女监，女犯看我心慌慌！/rewrites/女监风云：开局被美女包围/ab_test')

# 读源文
sys.path.insert(0, '.agents/skills/story-engine/tools')
from utils import get_source_text
import json
cfg = json.loads(open('configs/config_执掌女监.json', encoding='utf-8').read())
cfg['base_dir'] = '.'

for ch in [1, 2, 3]:
    source = get_source_text(cfg, ch) or "(无)"
    out = []
    out.append(f"# 第{ch}章 五版对比\n")
    out.append(f"## 源文\n```\n{source.strip()}\n```\n")
    for k in ['A','B','C','D']:
        f = AB_DIR / k / f'ch_{ch:03d}.txt'
        label = {'A':'flash+105行规则','B':'pro+示例','C':'flash+示例','D':'pro+示例+字数约束'}[k]
        if f.exists():
            text = f.read_text(encoding='utf-8')
            wc = len(text.replace('\n','').replace(' ','').replace('\r',''))
            src_chars = len(source.replace('\n','').replace(' ','').replace('\r','')) if source else 0
            dev = ((wc - src_chars) / src_chars * 100) if src_chars else 0
            out.append(f"## {k}版 ({label}) — {wc}字 (目标{src_chars}, 偏差{dev:+.0f}%)\n```\n{text.strip()}\n```\n")
        else:
            out.append(f"## {k}版 ({label}) — (无)\n")

    report_path = AB_DIR / f"ch{ch:03d}_对比.md"
    report_path.write_text('\n'.join(out), encoding='utf-8')
    print(f"[OK] {report_path}")
