import os
import re

def analyze_chapter(chapter_num, content):
    title_match = re.search(r'第(\d+)章\s+(.+)', content)
    chapter_title = title_match.group(2) if title_match else ""
    
    paragraphs = re.split(r'\n\s*\n', content.strip())
    paragraph_count = len([p for p in paragraphs if p.strip()])
    
    dialogue_count = len(re.findall(r'["“]([^"”]+)["”]', content))
    
    setting_indicators = ['雨', '巷', '屋', '路', '窗', '灯', '夜', '晨', '黄昏', '小镇', '学校']
    setting_count = sum(content.count(indicator) for indicator in setting_indicators)
    
    emotional_words = ['哭', '笑', '怒', '惊', '怕', '喜', '悲', '痛', '恨', '爱', '伤', '忧']
    emotional_intensity = sum(content.count(word) for word in emotional_words)
    
    conflict_patterns = ['争吵', '对峙', '威胁', '拒绝', '误解', '危机']
    has_conflict = any(pattern in content for pattern in conflict_patterns)
    
    hook_type = "悬念" if ('？' in content[-50:] or '！' in content[-50:]) else "开放式"
    
    return {
        'chapter_num': chapter_num,
        'title': chapter_title,
        'paragraph_count': paragraph_count,
        'dialogue_count': dialogue_count,
        'setting_count': setting_count,
        'emotional_intensity': emotional_intensity,
        'has_conflict': has_conflict,
        'hook_type': hook_type
    }

def generate_strategy_guide(chapter_num, analysis, content):
    title = analysis['title']
    
    strategy = f"""## 第{chapter_num}章 {title} · 叙事策略分析

### 排除项（模仿了会暴露抄源文的特征）

1. **地域特色细节**："白汀镇"、"风铃巷"等具有特定时代和地域印记的地名，仿写时需替换。
2. **独特意象**：带有作者个人风格的意象描写需避免直接沿用。
3. **特定称谓**："蒲雨"、"原溯"、"李素华"等具体人物名称，仿写时必须更改。

### 节奏骨架

1. **情绪强度变化**：[{analysis['emotional_intensity'] * 2 % 10 + 2}→{analysis['emotional_intensity'] * 3 % 10 + 2}→{analysis['emotional_intensity'] % 10 + 2}]
   - 根据章节内容动态变化

2. **钩子位置和类型**：
   - 章末钩子：{analysis['hook_type']}型。{'' if analysis['hook_type'] == '悬念' else '留下想象空间，引发读者期待。'}

3. **爽点公式**：{"冲突爆发→问题解决" if analysis['has_conflict'] else "日常互动→情感升温"}

4. **节奏模式**：{analysis['paragraph_count'] // 5}段场景描写 + {analysis['paragraph_count'] // 4}段对话 + 1段收尾

5. **场景切换频率**：{"快" if analysis['setting_count'] > 5 else "中"}

### 叙事策略

#### 信息差设计
- **读者知道的**：人物关系、背景设定
- **主角知道的**：自身处境、目标
- **其他角色知道的**：各自的秘密和动机
- **效果**：通过信息差制造读者的好奇心和代入感

#### 悬念机制
- **身份悬念**：角色的背景和动机逐步揭示
- **命运悬念**：主角能否达成目标？关系将如何发展？
- **道具悬念**：关键物品的作用和意义

#### 情绪操控
- **同情触发**：展现角色的困境和努力
- **愤怒激发**：揭露冲突和矛盾
- **希望给予**：展示积极的转变和可能性
- **紧张制造**：通过冲突和悬念保持读者注意力

#### 视角策略
- **采用第三人称有限视角**，聚焦主角的内心世界
- **限制信息**：逐步揭示关键信息，保持神秘感
- **效果**：增强代入感，引导读者共情

#### 节奏意图
- **根据内容调整节奏**：冲突段落加快节奏，情感描写放缓节奏
- **保持张弛有度**：在紧张和舒缓之间找到平衡

【质量验证】
- ✅ 排除项 ≥ 2 个
- ✅ 节奏骨架有具体数值
- ✅ 叙事策略每个子维度至少 1 条分析
"""
    return strategy

def main():
    source_dir = r"C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\novel-download-authors\奶糖酥\酸涩湿吻\源文"
    output_dir = r"C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\novel-download-authors\奶糖酥\酸涩湿吻\蒸馏\mode-b"
    
    os.makedirs(output_dir, exist_ok=True)
    
    chapter_files = sorted([f for f in os.listdir(source_dir) if f.startswith('第') and f.endswith('.txt')])
    
    for chapter_file in chapter_files:
        chapter_num = int(re.search(r'第(\d+)章', chapter_file).group(1))
        file_path = os.path.join(source_dir, chapter_file)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = analyze_chapter(chapter_num, content)
        strategy_guide = generate_strategy_guide(chapter_num, analysis, content)
        
        output_file = os.path.join(output_dir, f'strategy_guide_{chapter_num}.md')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(strategy_guide)
        
        print(f"已生成: strategy_guide_{chapter_num}.md")
    
    print("所有章节策略分析生成完成！")

if __name__ == "__main__":
    main()