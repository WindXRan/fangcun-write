"""Debug: run the actual fix_agent and see what happens."""
import json, sys, re
sys.path.insert(0, '.agents/skills/story-engine/tools')
from pathlib import Path
from lib.constants import AI_MARKERS, AI_MARKER_PATTERN
from lib.text_metrics import count_metrics
from lib.source_locator import get_source_text

cfg = json.loads(open('configs/config_执掌女监.json', encoding='utf-8').read())
ch_dir = Path(cfg['rewrites_dir']) / 'chapters'

# Simulate what the full pipeline does for ch2 and ch3
for ch in [2, 3]:
    print(f'\n===== ch{ch} =====')
    ch_file = ch_dir / f'ch_{ch:03d}.txt'
    text = ch_file.read_text(encoding='utf-8')
    original = text
    
    # Run _algo_check logic
    metrics = count_metrics(text)
    src = get_source_text(cfg, ch)
    src_metrics = count_metrics(src) if src else None
    
    # Generate issues
    issues = []
    
    # ai_trace
    for marker in AI_MARKERS:
        pat = r'(?:^|[\n。！？])\s*' + re.escape(marker)
        found = re.findall(pat, text)
        if found:
            issues.append({'type': 'ai_trace', 'severity': 'medium', 'auto_fixable': True})
    
    # ai_marker
    if src_metrics:
        limit = max(src_metrics['ai_markers'] + 1, 1)
        if metrics['ai_markers'] > limit:
            issues.append({'type': 'ai_marker', 'severity': 'high', 'auto_fixable': True})
    
    print(f'  Issues found: {[i["type"] for i in issues]}')
    
    # Now run _fix_mechanical
    count = 0
    for iss in issues:
        if iss['type'] == 'ai_trace':
            for marker in AI_MARKERS:
                pat = r'(?:^|[\n。！？])\s*' + re.escape(marker)
                found = re.findall(pat, text)
                if found:
                    count += len(found)
                    text = re.sub(pat, lambda m: m.group()[:1] if m.group() else '', text)
        elif iss['type'] == 'ai_marker':
            found = re.findall(AI_MARKER_PATTERN, text)
            if found:
                count += len(found)
                text = re.sub(AI_MARKER_PATTERN, '', text)
    
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    print(f'  After fix: text changed={text != original}, mech_count={count}')
    if text != original:
        # show diff
        for i, (a, b) in enumerate(zip(original.splitlines(), text.splitlines())):
            if a != b:
                print(f'    diff L{i+1}: OLD={a[:80]}')
                print(f'              NEW={b[:80]}')
                break
