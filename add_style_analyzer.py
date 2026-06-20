import os

writer_path = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\fangcun-write\tools\writer.py'
with open(writer_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 新函数
new_func = '''
def _load_style_fingerprint(config, ch_num):
    """加载文风指纹（自动提取）"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from style_analyzer import load_style_from_cache, generate_and_save_style
    
    # 先尝试从缓存加载
    style = load_style_from_cache(config, ch_num)
    if style:
        return style
    
    # 缓存没有，自动生成
    style = generate_and_save_style(config, ch_num)
    if style:
        return style
    
    return "（文风指纹未提取）"

'''

# 在_save_memory_db函数后面添加
old = '''def _save_memory_db(config, memory_db):
    """保存记忆数据库"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    memory_path = rewrites_dir / "memory_db.json"
    memory_db.save(str(memory_path))


def _load_characters(config):'''

new = '''def _save_memory_db(config, memory_db):
    """保存记忆数据库"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    memory_path = rewrites_dir / "memory_db.json"
    memory_db.save(str(memory_path))

''' + new_func + '''
def _load_characters(config):'''

content = content.replace(old, new)

with open(writer_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('添加 _load_style_fingerprint 函数完成')
