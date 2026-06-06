# -*- coding: utf-8 -*-
"""
统一字数统计模块
参考番茄小说、起点中文网、知乎等网文平台的统计方式
"""

import re
from typing import Dict, Optional

# Unicode范围定义
CJK_RANGE = r'\u4e00-\u9fff'  # CJK统一汉字
CN_PUNCT = r'，。！？、；：·～""''【】《》（）〈〉「」『』〔〕｛｝'  # 中文标点
ELLIPSIS = r'……'  # 省略号（整体算1字）
DASH = r'——'  # 破折号（整体算1字）

# 统计模式
MODE_STANDARD = 'standard'  # 网文平台标准：中文+标点+英文单词+数字位数
MODE_STRICT = 'strict'      # 严格模式：仅中文字符+中文标点
MODE_LOOSE = 'loose'        # 宽松模式：所有可见字符


def count_words(text: str, mode: str = MODE_STANDARD) -> Dict[str, int]:
    """
    统一字数统计

    Args:
        text: 输入文本
        mode: 统计模式
            - 'standard': 中文字符+中文标点+英文单词+数字位数（网文平台标准）
            - 'strict': 仅中文字符+中文标点+省略号+破折号
            - 'loose': 所有可见字符

    Returns:
        {
            'total': 总字数,
            'chinese': 中文字符数,
            'punctuation': 中文标点数,
            'ellipsis': 省略号数,
            'dash': 破折号数,
            'english': 英文单词数,
            'digits': 数字位数,
            'mode': 统计模式
        }
    """
    # 保存原始文本用于宽松模式
    original_text = text

    # 清理空白字符（空格、换行、制表符等）
    text = re.sub(r'\s+', '', text)

    # 1. 统计省略号和破折号（整体算1字，先提取避免被拆散）
    ellipsis_count = len(re.findall(ELLIPSIS, text))
    dash_count = len(re.findall(DASH, text))
    # 移除已统计的省略号和破折号
    text = re.sub(ELLIPSIS, '', text)
    text = re.sub(DASH, '', text)

    # 2. 统计中文字符
    chinese_chars = re.findall(f'[{CJK_RANGE}]', text)
    chinese = len(chinese_chars)

    # 3. 统计中文标点
    punct_chars = re.findall(f'[{CN_PUNCT}]', text)
    punctuation = len(punct_chars)

    # 4. 统计英文单词（连续字母算1个词）
    english_words = re.findall(r'[a-zA-Z]+', text)
    english = len(english_words)

    # 5. 统计数字位数（每个数字字符算1）
    digit_chars = re.findall(r'\d', text)
    digits = len(digit_chars)

    # 6. 根据模式计算总数
    if mode == MODE_STANDARD:
        # 网文平台标准：中文+标点+省略号+破折号+英文单词+数字位数
        total = chinese + punctuation + ellipsis_count + dash_count + english + digits
    elif mode == MODE_STRICT:
        # 严格模式：仅中文+标点+省略号+破折号
        total = chinese + punctuation + ellipsis_count + dash_count
    elif mode == MODE_LOOSE:
        # 宽松模式：所有可见字符（不含空白）
        total = len(re.sub(r'\s+', '', original_text))
    else:
        raise ValueError(f"未知统计模式: {mode}")

    return {
        'total': total,
        'chinese': chinese,
        'punctuation': punctuation,
        'ellipsis': ellipsis_count,
        'dash': dash_count,
        'english': english,
        'digits': digits,
        'mode': mode
    }


def count_chapter_words(text: str, mode: str = MODE_STANDARD) -> int:
    """
    统计章节字数（返回总数）

    Args:
        text: 章节文本
        mode: 统计模式

    Returns:
        字数（整数）
    """
    return count_words(text, mode)['total']


def format_word_count(text: str, mode: str = MODE_STANDARD) -> str:
    """
    格式化字数统计结果

    Args:
        text: 输入文本
        mode: 统计模式

    Returns:
        格式化的统计结果字符串
    """
    stats = count_words(text, mode)

    if mode == MODE_STANDARD:
        return (
            f"总字数: {stats['total']} | "
            f"中文: {stats['chinese']} | "
            f"标点: {stats['punctuation']} | "
            f"省略号: {stats['ellipsis']} | "
            f"破折号: {stats['dash']} | "
            f"英文词: {stats['english']} | "
            f"数字: {stats['digits']}"
        )
    elif mode == MODE_STRICT:
        return f"字数(严格): {stats['total']} | 中文: {stats['chinese']} | 标点: {stats['punctuation']}"
    else:
        return f"字数(宽松): {stats['total']}"


def count_file(filepath: str, mode: str = MODE_STANDARD) -> Dict[str, int]:
    """
    统计文件字数

    Args:
        filepath: 文件路径
        mode: 统计模式

    Returns:
        字数统计结果
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    return count_words(text, mode)


# 命令行接口
if __name__ == '__main__':
    import sys
    import os
    import glob
    import statistics

    if len(sys.argv) < 2:
        print("用法: python word_count.py <文件或目录> [模式] [--median]")
        print("模式: standard(默认) | strict | loose")
        print("--median: 对目录下所有章节文件取中位数")
        sys.exit(1)

    path = sys.argv[1]
    mode = MODE_STANDARD
    median_mode = False

    for arg in sys.argv[2:]:
        if arg in (MODE_STANDARD, MODE_STRICT, MODE_LOOSE):
            mode = arg
        elif arg == '--median':
            median_mode = True

    if median_mode and os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, '第*章*.txt')))
        if not files:
            print(f"错误: 目录 {path} 下没有找到章节文件")
            sys.exit(1)
        counts = []
        for f in files:
            stats = count_file(f, mode)
            counts.append(stats['total'])
        med = int(statistics.median(counts))
        avg = int(statistics.mean(counts))
        print(f"章节数: {len(counts)}")
        print(f"中位数: {med}")
        print(f"平均值: {avg}")
        print(f"最小值: {min(counts)}")
        print(f"最大值: {max(counts)}")
        print(f"建议基准: {med}")
        print(f"建议上限: {int(med * 1.15)}")
    elif os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, '第*章*.txt')))
        if not files:
            print(f"错误: 目录 {path} 下没有找到章节文件")
            sys.exit(1)
        total = 0
        for f in files:
            stats = count_file(f, mode)
            total += stats['total']
            print(f"{os.path.basename(f)}: {stats['total']}字")
        print(f"---")
        print(f"合计: {total}字 ({len(files)}章)")
    else:
        try:
            stats = count_file(path, mode)
            print(f"文件: {path}")
            print(format_word_count(open(path, 'r', encoding='utf-8').read(), mode))
        except Exception as e:
            print(f"错误: {e}")
            sys.exit(1)
