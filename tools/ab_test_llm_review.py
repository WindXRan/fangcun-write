"""LLM 审读 A/B 四版输出，定性评价擦边质量而非数关键词"""
import sys, json, time
from pathlib import Path

sys.path.insert(0, '.agents/skills/story-engine/tools')
sys.path.insert(0, '.agents/skills/story-engine/tools/lib')
from lib.api_client import call_api as api_call, get_api_url, get_api_key
from utils import get_source_text

CONFIG_PATH = 'configs/config_执掌女监.json'
AB_DIR = Path('projects/今入画/执掌女监，女犯看我心慌慌！/rewrites/女监风云：开局被美女包围/ab_test')
CHAPTERS = [1, 2, 3]
VARIANTS = {'A': 'flash+105行规则', 'B': 'pro+示例', 'C': 'flash+示例', 'D': 'pro+示例+字数约束'}

cfg = json.loads(open(CONFIG_PATH, encoding='utf-8').read())
cfg['base_dir'] = '.'
api_key = get_api_key(cfg)
api_url = get_api_url(cfg)

for ch in CHAPTERS:
    print(f"\n{'='*60}")
    print(f"  第{ch}章")
    print(f"{'='*60}")

    source = get_source_text(cfg, ch) or "(无法读取)"
    source_short = source[:1000]

    texts = {}
    for k in ['A','B','C','D']:
        f = AB_DIR / k / f'ch_{ch:03d}.txt'
        texts[k] = f.read_text(encoding='utf-8') if f.exists() else "(无)"

    prompt = f"""你是网文编辑，正在审读都市擦边小说的四版写章输出。源文是参考基准，**源文也要参与评分**。

## 源文（第{ch}章）— 也作为一版参与评分
{source_short}

## 四版输出（各取开头片段）

### A版 (flash+105行规则)
{texts['A'][:800]}

### B版 (pro+示例)
{texts['B'][:800]}

### C版 (flash+示例)
{texts['C'][:800]}

### D版 (pro+示例+字数约束)
{texts['D'][:800]}

## 评价标准

擦边质量看的是"能不能硬"，不是数身体部位词。具体看：
1. **画面感** — 读的时候脑子里有没有画面？还是堆砌词库？
2. **留白** — 是写"温热的手掌贴上胸口"让读者自己想象，还是写"她的体温通过布料传过来，掌心的纹路隔着衬衫印在他胸膛上"把感觉说死？
3. **节奏** — 擦边是推进剧情的，还是停下来展览的？
4. **态度** — 男主是被动接收还是主动互动？有没有角色感？
5. **自然度** — 读起来像小说还是像在过 checklist？

## 输出格式

**源文先评**：给一个擦边质量分（1-10）+ 一句话评价。
然后对 **A/B/C/D 各版**给分（1-10）+ 一句话评价。
然后排出**五者名次**（1st/2nd/3rd/4th/5th）。
最后说：哪一版最接近源文的擦边气质？哪一版可以合并优点？"""

    print(f"  调用 LLM 审读...", end='', flush=True)
    try:
        result = api_call(api_key, "deepseek-v4-flash", prompt,
                         reasoning_effort="low", max_tokens=2048,
                         system_prompt="你是专业网文编辑，擅长评鉴擦边类小说的质量。不数关键词，只凭阅读感受判断。",
                         api_url=api_url)
        print(f" OK ({len(result)}字)")
        print(result)
    except Exception as e:
        print(f" FAIL: {e}")
