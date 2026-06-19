import os
import re

prompts_dir = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\story-engine\prompts'

for filename in os.listdir(prompts_dir):
    if not filename.endswith('.md'):
        continue
    
    file_path = os.path.join(prompts_dir, filename)
    
    # 尝试多种编码
    content = None
    for encoding in ['utf-8', 'gbk', 'gb18030', 'latin-1']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        print('跳过(编码错误):', filename)
        continue
    
    # 移除model字段
    content = re.sub(r'"model"\s*:\s*"[^"]*"\s*,?\s*', '', content)
    
    # 清理空的defaults
    content = re.sub(r'defaults:\s*\{\s*\}\s*\n?', '', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print('处理:', filename)

print('完成')
