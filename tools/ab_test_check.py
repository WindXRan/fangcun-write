"""Import check and A/B test dry run"""
import sys, json, re
sys.path.insert(0, '.agents/skills/story-engine/tools')
sys.path.insert(0, '.agents/skills/story-engine/tools/lib')

from prompt_loader import load_prompt
from utils import call_api, get_source_text, count_source_chars, get_total_chapters
from lib.api_client import get_api_url, get_api_key

print("All imports OK")

config = json.loads(open('configs/config_执掌女监.json', encoding='utf-8').read())
config['base_dir'] = '.'
config['prompts_dir'] = '.agents/skills/story-engine/prompts'
print(f"Config: genre={config.get('genre')}")

text = get_source_text(config, 1)
print(f"Source ch1: {len(text) if text else 0} chars")

prompt_a = load_prompt('.agents/skills/story-engine/prompts/write-chapter.md', '.',
    {'N':'1','新书名':'Test','作者名':'Test','源书名':'Test','N03d':'001','N_plus1':'2','N03d_plus1':'002','总章数':'100','源文字数':'1909','目标字数':'1909','目标字数_min':'1718','目标字数_max':'2100','genre':'都市擦边'},
    mode='api', rewrites_dir=config['rewrites_dir'])
print(f"Prompt A length: {len(prompt_a)} chars")
has_rules = '触觉词库' in prompt_a or '擦边执行清单' in prompt_a
print(f"Has genre rules: {has_rules}")

# Test the EroticPassage extractor (copy of the function from ab_test_write.py)
def extract_erotic_passages(source_text):
    body_parts = r'(胸|腿|腰|锁骨|皮肤|手|肩|臀|背|颈|唇|舌|大[腿]|脚踝|手腕|手心|虎口|胸口|肩胛|后颈|腰窝)'
    contact_verbs = r'(贴|靠|蹭|\b摸\b|贴|压|抱|搂|圈|顶|\b抵\b|擦|碰|缠|勾|揽|抚|握|捏|揉|抓)'
    sensory_adj = r'(温热|滑腻|柔软|微凉|细腻|发烫|紧贴|发麻|滚烫|冰凉|发软|发硬|紧绷|僵住|屏住|跳动|加速)'
    gaze_words = r'(视线|目光|看着|映入|扫过|掠过|瞥见|打量|审视)'
    desire_words = r'(心跳|呼吸|喉结|攥紧|耳根|发烫|冲动|燥热|按捺|克制|本能|反应|敏感|颤抖|电流|酥麻)'
    paragraphs = re.split(r'\n\s*\n', source_text)
    scored = []
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if len(para) < 30:
            continue
        score = 0
        score += len(re.findall(body_parts, para)) * 2
        score += len(re.findall(contact_verbs, para)) * 2
        score += len(re.findall(sensory_adj, para)) * 3
        score += len(re.findall(gaze_words, para)) * 1
        score += len(re.findall(desire_words, para)) * 3
        if score > 0:
            scored.append((score, i, para))
    scored.sort(key=lambda x: -x[0])
    passages = [p for _, _, p in scored[:6]]
    return passages

passages = extract_erotic_passages(text)
print(f"Extracted {len(passages)} erotic passages:")
for i, p in enumerate(passages):
    print(f"  Passage {i+1}: {len(p)} chars - {p[:80]}...")

# Check if API key is available
api_key = get_api_key(config)
if api_key:
    masked = api_key[:8] + "..." + api_key[-4:]
    print(f"API Key found: {masked}")
else:
    print("API Key NOT found in config or env")

print("\nAll checks passed!")
