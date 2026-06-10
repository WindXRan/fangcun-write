"""用 LLM 填充 style_guide 模板中的执行规则"""
import re
import sys
import json
import os
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')


def load_src_text(src_dir, chapter_num):
    """加载源文"""
    src_path = Path(src_dir)
    patterns = [f"第{chapter_num}章.txt", f"第{chapter_num:03d}章.txt"]
    for pattern in patterns:
        for f in src_path.glob(pattern):
            return f.read_text(encoding='utf-8')
    return None


def call_llm(prompt, api_key=None):
    """调用 LLM"""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key or os.environ.get("API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个专业的网文风格分析师。从源文中提取具体的写作规则，每条规则必须包含 ✅正向示例 和 ❌反向示例。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        return None


def fill_template(template, src_text, chapter_num):
    """用 LLM 填充模板"""
    prompt = f"""从以下源文中提取第{chapter_num}章的写作规则。

源文片段（前2000字）：
{src_text[:2000]}

请提取：
1. 句式规则（2-3条）：从源文中找出具体的句式特点，如短句占比、段落长度、结尾标点偏好等
2. 对话规则（2条）：对话标签方式、对话占比、口语化程度等
3. 描写规则（2条）：情绪表达方式、环境描写密度、肖像描写风格等

每条规则格式：
**规则N：做什么 / 不做什么**
- ✅ 正向：（源文怎么写）+ 示例
- ❌ 反向：（写了什么就违规）+ 违例示例

只输出规则，不要其他内容。"""
    
    result = call_llm(prompt)
    if not result:
        return template
    
    # 将 LLM 输出插入到模板中
    # 找到 "（LLM 补充：" 的位置，替换为 LLM 输出
    lines = template.split('\n')
    new_lines = []
    skip_until_next_section = False
    
    for line in lines:
        if '（LLM 补充：' in line:
            # 跳过这行，插入 LLM 输出
            new_lines.append(result)
            skip_until_next_section = True
        elif skip_until_next_section:
            # 跳过直到下一个 ### 或 ##
            if line.startswith('###') or line.startswith('##'):
                new_lines.append(line)
                skip_until_next_section = False
        else:
            new_lines.append(line)
    
    return '\n'.join(new_lines)


def run(guides_dir, src_dir, api_key=None):
    """批量填充 style_guide 模板"""
    guides_path = Path(guides_dir)
    src_path = Path(src_dir)
    
    # 查找所有模板文件
    template_files = sorted(guides_path.glob("style_*.md"), key=lambda x: int(x.stem.split('_')[1]))
    
    if not template_files:
        print(f"未找到 style_guide 模板: {guides_dir}")
        return
    
    print(f"找到 {len(template_files)} 个模板文件")
    
    success_count = 0
    fail_count = 0
    
    for template_file in template_files:
        chapter_num = int(template_file.stem.split('_')[1])
        
        # 检查是否已填充（跳过已填充的）
        template = template_file.read_text(encoding='utf-8')
        if '（LLM 补充：' not in template:
            print(f"跳过第{chapter_num}章（已填充）")
            success_count += 1
            continue
        
        # 加载源文
        src_text = load_src_text(src_path, chapter_num)
        if not src_text:
            print(f"警告：源文不存在 第{chapter_num}章.txt")
            fail_count += 1
            continue
        
        # 填充模板
        print(f"正在填充第{chapter_num}章...")
        filled = fill_template(template, src_text, chapter_num)
        
        # 保存
        template_file.write_text(filled, encoding='utf-8')
        print(f"✓ 第{chapter_num}章填充完成")
        success_count += 1
    
    print(f"\n完成！成功: {success_count}, 失败: {fail_count}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python fill_style_guides.py <guides目录> <源文目录> [api_key]")
        print("Example: python fill_style_guides.py projects/奶糖酥/酸涩湿吻/rewrites/酸涩湿吻/guides projects/奶糖酥/酸涩湿吻/源文")
        sys.exit(1)
    
    api_key = sys.argv[3] if len(sys.argv) > 3 else None
    run(sys.argv[1], sys.argv[2], api_key)
