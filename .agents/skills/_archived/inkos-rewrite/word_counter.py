"""
word_counter.py — 统一字数统计模块
与番茄小说网站的统计方式保持一致。

番茄字数统计规则：
1. 只统计汉字（中文字符）
2. 不统计标点符号（中文/英文标点都不统计）
3. 不统计空格、换行符
4. 不统计数字
5. 不统计英文字母
6. 标题、作者名等不计入正文字数

用法：
    from word_counter import count_words, count_words_from_file
    
    # 统计文本字数
    words = count_words("这是一段测试文本")
    
    # 统计文件字数
    words = count_words_from_file("chapter.txt")
"""

import re
import os


def count_words(text: str) -> int:
    """
    统计文本字数（与番茄小说一致）
    
    番茄统计方式：只统计汉字
    包括：汉字（CJK统一汉字）
    不包括：标点符号、数字、英文字母、空格、换行符
    
    Args:
        text: 要统计的文本
        
    Returns:
        字数（纯汉字数）
    """
    if not text:
        return 0
    
    return len(re.findall(r'[\u4e00-\u9fff]', text))


def count_words_from_file(filepath: str) -> int:
    """
    统计文件字数
    
    Args:
        filepath: 文件路径
        
    Returns:
        汉字数量
        
    Raises:
        FileNotFoundError: 文件不存在
        UnicodeDecodeError: 文件编码错误
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return count_words(content)


def count_words_exclude_title(text: str, title_pattern: str = r'^第\d+章\s+.*\n') -> int:
    """
    统计正文字数（排除标题）
    
    Args:
        text: 要统计的文本
        title_pattern: 标题正则模式
        
    Returns:
        正文汉字数量
    """
    if not text:
        return 0
    
    # 移除标题
    content = re.sub(title_pattern, '', text, count=1)
    return count_words(content)


def get_word_stats(text: str) -> dict:
    """
    获取详细的字数统计
    
    Args:
        text: 要统计的文本
        
    Returns:
        包含各种统计数据的字典
    """
    if not text:
        return {
            'total_chars': 0,
            'chinese_chars': 0,
            'punctuation': 0,
            'spaces': 0,
            'digits': 0,
            'english': 0,
            'other': 0,
            'word_count': 0,  # 番茄标准字数
        }
    
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    punctuation_pattern = re.compile(r'[，。！？；：\u201c\u201d\u2018\u2019（）【】《》、,.!?;:(){}\\[\\]<>"\']')
    punctuation = len(punctuation_pattern.findall(text))
    spaces = len(re.findall(r'\s', text))
    digits = len(re.findall(r'\d', text))
    english = len(re.findall(r'[a-zA-Z]', text))
    other = len(text) - chinese_chars - punctuation - spaces - digits - english
    
    # 番茄标准字数：所有非空格字符
    word_count = len(re.sub(r'[\s\n\r]', '', text))
    
    return {
        'total_chars': len(text),
        'chinese_chars': chinese_chars,
        'punctuation': punctuation,
        'spaces': spaces,
        'digits': digits,
        'english': english,
        'other': max(0, other),
        'word_count': word_count,
    }


def format_word_stats(stats: dict) -> str:
    """
    格式化字数统计结果
    
    Args:
        stats: get_word_stats返回的字典
        
    Returns:
        格式化的字符串
    """
    return f"""字数统计：
  总字符数：{stats['total_chars']}
  汉字数量：{stats['chinese_chars']}（番茄统计）
  标点符号：{stats['punctuation']}
  空格换行：{stats['spaces']}
  数字：{stats['digits']}
  英文字母：{stats['english']}
  其他：{stats['other']}"""


# 命令行工具
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python word_counter.py <txt文件或目录>")
        sys.exit(1)
    
    target = sys.argv[1]
    
    if os.path.isdir(target):
        # 统计目录下所有txt文件
        total_words = 0
        for f in sorted(os.listdir(target)):
            if f.endswith('.txt'):
                filepath = os.path.join(target, f)
                words = count_words_from_file(filepath)
                total_words += words
                print(f"{f}: {words}字")
        print(f"\n总计: {total_words}字")
    elif os.path.isfile(target):
        # 统计单个文件
        words = count_words_from_file(target)
        stats = get_word_stats(open(target, 'r', encoding='utf-8').read())
        print(f"文件: {os.path.basename(target)}")
        print(f"字数: {words}字")
        print()
        print(format_word_stats(stats))
    else:
        print(f"错误: {target} 不存在")
        sys.exit(1)
