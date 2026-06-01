# -*- coding: utf-8 -*-
"""
de-ai-connectors.py
去AI：连接词降频 + 得地的修正

用法：python de-ai-connectors.py "文件路径" [--dry-run]
"""

import sys
import re
import os

def process_file(path, dry_run=False):
    if not os.path.exists(path):
        print(f"ERROR: {path}")
        return
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    changes = []
    
    # ============================================================
    # 1. 得地的修正
    # ============================================================
    
    # 地(dì) 排除列表
    di_exclusions = [
        '土地','地方','地面','地上','地下','地理','地质','地道','地震','地铁',
        '地址','地段','地步','地势','地带','地域','地壳','地层','地窖','地洞',
        '地毯','地皮','地板','地基','地契','地租','地主','地狱','地图','地球',
        '地形','天地','阵地','领地','境地','驻地','落地','各地','内地','外地',
        '本地','基地','陆地','湿地','荒地','田地','林地','园地','空地','绿地',
        '草地','菜地','耕地','洼地','高地','低地','平地','大地','满地','遍地',
        '一地','整地','着地','席地','失地','飞地','目的地','发源地','根据地',
        '策源地','处女地','惊天动地','天翻地覆','天长地久','天经地义',
        '天寒地冻','天罗地网','天南地北','脚踏实地','设身处地','因地制宜',
        '一败涂地','斯文扫地','五体投地','死心塌地','翻天覆地','冰天雪地',
        '开天辟地','改天换地','欢天喜地','昏天暗地','呼天抢地','花天酒地',
        '顶天立地','肝脑涂地','幕天席地'
    ]
    
    # 得(děi) 排除列表
    dei_exclusions = [
        '得走了','得想办法','得赶紧','得注意','得小心','得抓紧','得尽快',
        '得看','得说','得做','得去','得来','得想','得找','得用','得拿',
        '得买','得卖','得吃','得喝','得睡','得醒','得站','得坐','得躺',
        '得蹲','得跪','得爬','得跳','得飞','得游','得跑','得走','得打',
        '得骂','得夸','得恨','得爱','得怕','得急','得气','得累','得困',
        '得饿','得渴','得冷','得热','得疼','得痒','得酸','得麻','得辣',
        '得甜','得苦','得咸','得淡','得浓','得稠','得稀','得硬','得软',
        '得脆','得韧','得滑','得粗','得细','得厚','得薄','得宽','得窄',
        '得长','得短','得高','得矮','得大','得小','得多','得少','得快',
        '得慢','得早','得晚','得远','得近','得深','得浅','得亮','得暗',
        '得响','得轻','得重','得紧','得松','得弯','得直','得斜','得歪',
        '得正','得偏','得反','得倒','得竖','得横','得平','得陡','得险',
        '得稳','得牢','得严','得密','得清','得浊','得净','得脏','得干',
        '得湿','得潮','得润','得燥','得黏','得涩','得糙','得光','得毛',
        '得皱','得鼓','得瘪','得凸','得凹','得圆','得扁','得方','得尖',
        '得钝','得利','得急','得缓','得猛','得烈','得强','得弱','得弹',
        '得粘'
    ]
    
    # 保护地(dì)词
    di_pattern = '|'.join(re.escape(w) for w in di_exclusions)
    di_matches = list(re.finditer(di_pattern, content))
    protected = {}
    for i, m in enumerate(di_matches):
        key = f"<<<{i}>>>"
        protected[key] = m.group()
        content = content[:m.start()] + key + content[m.end():]
    
    # 保护得(děi)词
    dei_pattern = '|'.join(re.escape(w) for w in dei_exclusions)
    dei_matches = list(re.finditer(dei_pattern, content))
    for i, m in enumerate(dei_matches):
        key = f"<<<d{i}>>>"
        protected[key] = m.group()
        content = content[:m.start()] + key + content[m.end():]
    
    # 替换得(de) → 的
    before = content
    content = content.replace('得', '的')
    if content != before:
        changes.append('得(de)→的')
    
    # 替换地(de) → 的
    before = content
    content = content.replace('地', '的')
    if content != before:
        changes.append('地(de)→的')
    
    # 恢复被保护的词
    for key, value in protected.items():
        content = content.replace(key, value)
    
    # ============================================================
    # 2. 单字连接词降频（非对话行）
    # ============================================================
    
    lines = content.split('\n')
    new_lines = []
    conn_count = 0
    
    for line in lines:
        # 对话行保留（包含引号）
        if any(c in line for c in ['\u201c', '\u201d', '\u2018', '\u2019', '\u300c', '\u300d', '"', '"']):
            new_lines.append(line)
            continue
        
        original_line = line
        
        # 逗号后的连接词
        line = re.sub(r'，但', '，', line)
        line = re.sub(r'，又', '，', line)
        line = re.sub(r'，却', '，', line)
        line = re.sub(r'，就', '，', line)
        line = re.sub(r'，也', '，', line)
        line = re.sub(r'，还', '，', line)
        
        # 句首连接词（行首或标点后）
        line = re.sub(r'^但', '', line)
        line = re.sub(r'^又', '', line)
        line = re.sub(r'^却', '', line)
        line = re.sub(r'^就', '', line)
        line = re.sub(r'^也', '', line)
        line = re.sub(r'^还', '', line)
        
        # 其他位置的连接词
        line = re.sub(r'但仍旧', '仍旧', line)
        line = re.sub(r'但确实', '确实', line)
        line = re.sub(r'但勉强', '勉强', line)
        line = re.sub(r'但没有', '没有', line)
        line = re.sub(r'但还是', '还是', line)
        line = re.sub(r'但眼神', '眼神', line)
        line = re.sub(r'但你', '你', line)
        line = re.sub(r'但她', '她', line)
        line = re.sub(r'但他', '他', line)
        line = re.sub(r'又取出', '取出', line)
        line = re.sub(r'又去', '去', line)
        line = re.sub(r'又从', '从', line)
        line = re.sub(r'又撕下', '撕下', line)
        line = re.sub(r'又给他', '给他', line)
        line = re.sub(r'又闭上', '闭上', line)
        line = re.sub(r'又弯腰', '弯腰', line)
        line = re.sub(r'又在', '在', line)
        line = re.sub(r'又睡了', '睡了', line)
        line = re.sub(r'又稳了', '稳了', line)
        line = re.sub(r'又继续', '继续', line)
        line = re.sub(r'又停下', '停下', line)
        line = re.sub(r'却没', '没', line)
        line = re.sub(r'却暗了', '暗了', line)
        line = re.sub(r'却变得', '变得', line)
        line = re.sub(r'却只是', '只是', line)
        line = re.sub(r'却带着', '带着', line)
        line = re.sub(r'就能', '能', line)
        line = re.sub(r'就会', '会', line)
        line = re.sub(r'就开始', '开始', line)
        
        if line != original_line:
            conn_count += 1
        
        new_lines.append(line)
    
    content = '\n'.join(new_lines)
    if conn_count > 0:
        changes.append(f'连接词降频 x{conn_count}')
    
    # ============================================================
    # 3. 输出
    # ============================================================
    
    if dry_run:
        print(f"DRY RUN: {path}")
        print(f"修改: {len(changes)} 类")
        for c in changes:
            print(f"  - {c}")
    else:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"OK: {path} ({len(changes)} 类修改)")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python de-ai-connectors.py <文件路径> [--dry-run]")
        sys.exit(1)
    
    path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    
    process_file(path, dry_run)
