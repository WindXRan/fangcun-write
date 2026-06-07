"""读源文章节，输出：句长/对话占比/段长/句首分布/词频TOP20 + 情绪节拍表"""
import re, sys, json, os
from collections import Counter

def load_text(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def count_sentences(text):
    raw = re.split(r'[。！？\n]+', text)
    return [s.strip() for s in raw if len(s.strip()) > 2]

def dialogue_ratio(text):
    in_q = False
    chars = 0
    for ch in text:
        if ch in '\u201c\u201d\u300c\u300e"':
            in_q = not in_q
        elif in_q:
            chars += 1
    return chars / len(text) if text else 0

def colloquial_index(text):
    particles = set('啊吧吗呢嘛哦呀啦哟嗯哈噢')
    count = sum(1 for ch in text if ch in particles)
    return count / len(text) if text else 0

def sentence_starts(sentences):
    total = len(sentences)
    if total == 0:
        return {}
    pronouns = {'他','她','它','你','我','你们','我们','他们','她们','它们','这','那','谁','什么','怎么'}
    conj = {'但','但是','可','可是','然而','不过','虽然','因为','所以','如果','而且','然后','于是','结果','却','便','就','才','又','也','还','再','更'}
    cats = {'代词':0,'连词':0,'名词':0,'动词':0,'其他':0}
    for s in sentences:
        w = s[0]
        if w in pronouns:
            cats['代词'] += 1
        elif w in conj:
            cats['连词'] += 1
        elif w in '天地人大小上下来去走说是看好想':
            cats['动词'] += 1
        elif w in '你我他她它':
            cats['代词'] += 1
        else:
            cats['其他'] += 1
    return {k: round(v/total*100,1) for k,v in cats.items()}

def bigram_freq(text, top_n=20):
    chars = re.findall(r'[\u4e00-\u9fff]', text)
    bigrams = [chars[i]+chars[i+1] for i in range(len(chars)-1)]
    return [{'word':w,'count':c} for w,c in Counter(bigrams).most_common(top_n)]

def split_paragraphs(text):
    paras = [p.strip() for p in text.split('\n') if len(p.strip()) > 5]
    return paras

def emotion_keywords(text):
    """基于关键词的简单情绪标注（替代LLM分析）"""
    emotion_map = {
        '憋屈': ['忍','委屈','不甘','咽','憋','难受','痛苦','心酸','苦','涩','酸','疼','痛','哭','泪','哽咽','颤抖'],
        '愤怒': ['怒','恨','骂','摔','砸','吼','叫','打','踢','咬','气','火','暴','狠','恶','凶'],
        '震惊': ['愣','呆','傻','惊','吓','不敢相信','怎么可能','居然','竟然','没想到','突然'],
        '甜': ['笑','甜','暖','柔','轻','亲','抱','吻','爱','喜欢','心疼','宠','撒娇','甜蜜'],
        '爽': ['爽','痛快','解气','打脸','反击','赢','胜','碾压','嚣张','得意','霸气','帅'],
        '虐': ['伤','离','别','忘','放','舍','弃','走','远','冷','淡','沉默','无言','放手','离开'],
        '悬念': ['？','秘密','真相','隐瞒','骗','谎','不知道','背后','暗中','偷偷','悄悄'],
    }
    scores = {}
    for emo, keywords in emotion_map.items():
        count = sum(text.count(kw) for kw in keywords)
        scores[emo] = count
    return scores

def extract_beats(paragraphs):
    """逐段提取情绪类型和强度"""
    beats = []
    for i, para in enumerate(paragraphs):
        scores = emotion_keywords(para)
        if max(scores.values()) == 0:
            emo = '叙事'
            intensity = 2
        else:
            emo = max(scores, key=scores.get)
            raw = scores[emo]
            intensity = min(5, max(1, raw // 2 + 1))
        beats.append({
            '段': i+1,
            '情绪': emo,
            '强度': intensity,
        })
    return beats

def calc(text):
    sentences = count_sentences(text)
    sents = len(sentences)
    chars = len(text)
    paras = split_paragraphs(text)
    
    return {
        'avg_sent_len': round(chars / sents, 1) if sents else 0,
        'dialogue_pct': round(dialogue_ratio(text) * 100, 1),
        'avg_para_len': round(sents / len(paras), 1) if paras else 0,
        'colloquial_idx': round(colloquial_index(text) * 1000, 2),
        'sent_start_pct': sentence_starts(sentences),
        'top20_bigrams': bigram_freq(text, 20),
        'emotion_beats': extract_beats(paras),
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python calc_style_profile.py <源文第N章.txt> [-o output.json]')
        sys.exit(1)
    
    txt = load_text(sys.argv[1])
    result = calc(txt)
    
    output = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == '-o' else None
    if output:
        dirname = os.path.dirname(output)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f'Saved to {output}')
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
