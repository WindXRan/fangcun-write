"""
蒸馏文件验证工具 — 检查蒸馏文件的章节号是否正确。
"""
import re
import sys
import os


def verify_distill(distill_dir: str, source_dir: str = None) -> list:
    """验证蒸馏文件的章节号是否正确。
    
    Args:
        distill_dir: 蒸馏文件目录
        source_dir: 源文目录（可选，用于验证源文是否存在）
    
    Returns:
        问题列表，每项为 (章节号, 问题类型, 问题描述)
    """
    issues = []
    
    # 检查plot_guide
    for i in range(1, 200):  # 检查到200章，覆盖大部分小说
        for prefix in ['plot_guide', 'style_guide']:
            d_file = os.path.join(distill_dir, f'{prefix}_{i}.md')
            if not os.path.exists(d_file):
                continue
            
            with open(d_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查章节号
            if prefix == 'plot_guide':
                m = re.search(r'情节指南：第(\d+)章', content)
            else:
                m = re.search(r'风格指南：第(\d+)章', content)
            
            if m:
                written_ch = int(m.group(1))
                if written_ch != i:
                    issues.append((i, '章节号不匹配', f'{prefix}_{i}.md 写的是第{written_ch}章'))
            
            # 检查来源行
            m2 = re.search(r'来源：认亲后，大家的画风一起跑偏了 第(\d+)章', content)
            if m2:
                src_ch = int(m2.group(1))
                if src_ch != i:
                    issues.append((i, '来源行不匹配', f'{prefix}_{i}.md 来源写第{src_ch}章'))
            
            # 检查是否有模板占位符
            if '（填入' in content:
                issues.append((i, '未完成', f'{prefix}_{i}.md 仍有模板占位符'))
    
    # 检查style_profile
    for i in range(1, 200):
        p_file = os.path.join(distill_dir, f'style_profile_{i}.json')
        if not os.path.exists(p_file):
            continue
        
        # 检查文件大小
        if os.path.getsize(p_file) < 100:
            issues.append((i, 'style_profile过小', f'style_profile_{i}.json 可能不完整'))
    
    # 检查源文是否存在
    if source_dir:
        for i in range(1, 200):
            s_file = os.path.join(source_dir, f'第{i}章.txt')
            if os.path.exists(s_file):
                # 检查对应的蒸馏文件是否存在
                for prefix in ['plot_guide', 'style_guide']:
                    d_file = os.path.join(distill_dir, f'{prefix}_{i}.md')
                    if not os.path.exists(d_file):
                        issues.append((i, '蒸馏缺失', f'源文第{i}章存在但{prefix}_{i}.md不存在'))
    
    return issues


def fix_distill(distill_dir: str) -> int:
    """修复蒸馏文件中的章节号问题。
    
    Returns:
        修复的文件数量
    """
    fixed = 0
    
    for i in range(1, 200):
        for prefix in ['plot_guide', 'style_guide']:
            d_file = os.path.join(distill_dir, f'{prefix}_{i}.md')
            if not os.path.exists(d_file):
                continue
            
            with open(d_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            
            # 修复章节号
            if prefix == 'plot_guide':
                content = re.sub(r'情节指南：第\d+章', f'情节指南：第{i}章', content)
            else:
                content = re.sub(r'风格指南：第\d+章', f'风格指南：第{i}章', content)
            
            # 修复来源行
            content = re.sub(
                r'来源：认亲后，大家的画风一起跑偏了 第\d+章',
                f'来源：认亲后，大家的画风一起跑偏了 第{i}章',
                content
            )
            
            # 移除来源行中的额外信息
            content = re.sub(
                r'(来源：认亲后，大家的画风一起跑偏了 第\d+章)（[^）]*）',
                r'\1',
                content
            )
            
            if content != original:
                with open(d_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed += 1
    
    return fixed


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法:')
        print('  验证：python verify_distill.py verify <蒸馏目录> [源文目录]')
        print('  修复：python verify_distill.py fix <蒸馏目录>')
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == 'verify':
        distill_dir = sys.argv[2]
        source_dir = sys.argv[3] if len(sys.argv) > 3 else None
        issues = verify_distill(distill_dir, source_dir)
        
        if issues:
            print(f'发现 {len(issues)} 个问题:')
            for ch, issue_type, msg in issues:
                print(f'  [{issue_type}] 第{ch}章: {msg}')
        else:
            print('所有蒸馏文件验证通过')
    
    elif action == 'fix':
        distill_dir = sys.argv[2]
        fixed = fix_distill(distill_dir)
        print(f'修复了 {fixed} 个文件')
