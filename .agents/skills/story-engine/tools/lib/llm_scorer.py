"""LLM 编辑打分 — 像真人编辑一样评分。"""

import re
import requests


def llm_score_chapter(api_key, api_url, model, chapter_text, chapter_num, book_name):
    """LLM 编辑打分，返回 0-100 分。"""
    prompt = f"""你是资深网文编辑，给《{book_name}》第{chapter_num}章打分。

评分维度（每项 0-20 分）：
1. 开头钩子：前 200 字是否吸引人
2. 文笔质量：句式变化、比喻新鲜度、感官描写
3. 角色塑造：对话有个性、行为有逻辑
4. 节奏控制：长短交替、信息密度、有无拖沓
5. 章尾悬念：结尾是否有往下读的冲动

规则：
- 只看文本本身，不猜后续
- 有 AI 痕迹（路标词/情绪公式/感官堆叠）直接扣 10 分
- 对话没双引号扣 5 分
- 最后一行必须是：总分：XX

章文：
{chapter_text[:3000]}"""

    try:
        resp = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是资深网文编辑，打分严格，标准高。输出最后一行必须是：总分：XX"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 1024,
            },
            timeout=120,
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"].strip()
            # 提取总分 — 支持多种格式
            m = re.search(r'总分[：:]\s*(\d+)', content)
            if m:
                return int(m.group(1)), content
            # 尝试 "总分 XX" 格式
            m = re.search(r'总分\s+(\d+)', content)
            if m:
                return int(m.group(1)), content
            # 尝试从最后提取数字
            numbers = re.findall(r'(\d+)', content)
            if numbers:
                score = int(numbers[-1])
                if 0 <= score <= 100:
                    return score, content
            return 0, f"无法解析分数: {content[:200]}"
        else:
            return 0, f"API error: {resp.status_code}"
    except Exception as e:
        return 0, str(e)
