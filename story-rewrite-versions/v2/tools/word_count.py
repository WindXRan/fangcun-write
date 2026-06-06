# -*- coding: utf-8 -*-
"""
缁熶竴瀛楁暟缁熻妯″潡
鍙傝€冪暘鑼勫皬璇淬€佽捣鐐逛腑鏂囩綉銆佺煡涔庣瓑缃戞枃骞冲彴鐨勭粺璁℃柟寮?"""

import re
from typing import Dict, Optional

# Unicode鑼冨洿瀹氫箟
CJK_RANGE = r'\u4e00-\u9fff'  # CJK缁熶竴姹夊瓧
CN_PUNCT = r'锛屻€傦紒锛熴€侊紱锛毬凤綖""''銆愩€戙€娿€嬶紙锛夈€堛€夈€屻€嶃€庛€忋€斻€曪經锝?  # 涓枃鏍囩偣
ELLIPSIS = r'鈥︹€?  # 鐪佺暐鍙凤紙鏁翠綋绠?瀛楋級
DASH = r'鈥斺€?  # 鐮存姌鍙凤紙鏁翠綋绠?瀛楋級

# 缁熻妯″紡
MODE_STANDARD = 'standard'  # 缃戞枃骞冲彴鏍囧噯锛氫腑鏂?鏍囩偣+鑻辨枃鍗曡瘝+鏁板瓧浣嶆暟
MODE_STRICT = 'strict'      # 涓ユ牸妯″紡锛氫粎涓枃瀛楃+涓枃鏍囩偣
MODE_LOOSE = 'loose'        # 瀹芥澗妯″紡锛氭墍鏈夊彲瑙佸瓧绗?

def count_words(text: str, mode: str = MODE_STANDARD) -> Dict[str, int]:
    """
    缁熶竴瀛楁暟缁熻

    Args:
        text: 杈撳叆鏂囨湰
        mode: 缁熻妯″紡
            - 'standard': 涓枃瀛楃+涓枃鏍囩偣+鑻辨枃鍗曡瘝+鏁板瓧浣嶆暟锛堢綉鏂囧钩鍙版爣鍑嗭級
            - 'strict': 浠呬腑鏂囧瓧绗?涓枃鏍囩偣+鐪佺暐鍙?鐮存姌鍙?            - 'loose': 鎵€鏈夊彲瑙佸瓧绗?
    Returns:
        {
            'total': 鎬诲瓧鏁?
            'chinese': 涓枃瀛楃鏁?
            'punctuation': 涓枃鏍囩偣鏁?
            'ellipsis': 鐪佺暐鍙锋暟,
            'dash': 鐮存姌鍙锋暟,
            'english': 鑻辨枃鍗曡瘝鏁?
            'digits': 鏁板瓧浣嶆暟,
            'mode': 缁熻妯″紡
        }
    """
    # 淇濆瓨鍘熷鏂囨湰鐢ㄤ簬瀹芥澗妯″紡
    original_text = text

    # 娓呯悊绌虹櫧瀛楃锛堢┖鏍笺€佹崲琛屻€佸埗琛ㄧ绛夛級
    text = re.sub(r'\s+', '', text)

    # 1. 缁熻鐪佺暐鍙峰拰鐮存姌鍙凤紙鏁翠綋绠?瀛楋紝鍏堟彁鍙栭伩鍏嶈鎷嗘暎锛?    ellipsis_count = len(re.findall(ELLIPSIS, text))
    dash_count = len(re.findall(DASH, text))
    # 绉婚櫎宸茬粺璁＄殑鐪佺暐鍙峰拰鐮存姌鍙?    text = re.sub(ELLIPSIS, '', text)
    text = re.sub(DASH, '', text)

    # 2. 缁熻涓枃瀛楃
    chinese_chars = re.findall(f'[{CJK_RANGE}]', text)
    chinese = len(chinese_chars)

    # 3. 缁熻涓枃鏍囩偣
    punct_chars = re.findall(f'[{CN_PUNCT}]', text)
    punctuation = len(punct_chars)

    # 4. 缁熻鑻辨枃鍗曡瘝锛堣繛缁瓧姣嶇畻1涓瘝锛?    english_words = re.findall(r'[a-zA-Z]+', text)
    english = len(english_words)

    # 5. 缁熻鏁板瓧浣嶆暟锛堟瘡涓暟瀛楀瓧绗︾畻1锛?    digit_chars = re.findall(r'\d', text)
    digits = len(digit_chars)

    # 6. 鏍规嵁妯″紡璁＄畻鎬绘暟
    if mode == MODE_STANDARD:
        # 缃戞枃骞冲彴鏍囧噯锛氫腑鏂?鏍囩偣+鐪佺暐鍙?鐮存姌鍙?鑻辨枃鍗曡瘝+鏁板瓧浣嶆暟
        total = chinese + punctuation + ellipsis_count + dash_count + english + digits
    elif mode == MODE_STRICT:
        # 涓ユ牸妯″紡锛氫粎涓枃+鏍囩偣+鐪佺暐鍙?鐮存姌鍙?        total = chinese + punctuation + ellipsis_count + dash_count
    elif mode == MODE_LOOSE:
        # 瀹芥澗妯″紡锛氭墍鏈夊彲瑙佸瓧绗︼紙涓嶅惈绌虹櫧锛?        total = len(re.sub(r'\s+', '', original_text))
    else:
        raise ValueError(f"鏈煡缁熻妯″紡: {mode}")

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
    缁熻绔犺妭瀛楁暟锛堣繑鍥炴€绘暟锛?
    Args:
        text: 绔犺妭鏂囨湰
        mode: 缁熻妯″紡

    Returns:
        瀛楁暟锛堟暣鏁帮級
    """
    return count_words(text, mode)['total']


def format_word_count(text: str, mode: str = MODE_STANDARD) -> str:
    """
    鏍煎紡鍖栧瓧鏁扮粺璁＄粨鏋?
    Args:
        text: 杈撳叆鏂囨湰
        mode: 缁熻妯″紡

    Returns:
        鏍煎紡鍖栫殑缁熻缁撴灉瀛楃涓?    """
    stats = count_words(text, mode)

    if mode == MODE_STANDARD:
        return (
            f"鎬诲瓧鏁? {stats['total']} | "
            f"涓枃: {stats['chinese']} | "
            f"鏍囩偣: {stats['punctuation']} | "
            f"鐪佺暐鍙? {stats['ellipsis']} | "
            f"鐮存姌鍙? {stats['dash']} | "
            f"鑻辨枃璇? {stats['english']} | "
            f"鏁板瓧: {stats['digits']}"
        )
    elif mode == MODE_STRICT:
        return f"瀛楁暟(涓ユ牸): {stats['total']} | 涓枃: {stats['chinese']} | 鏍囩偣: {stats['punctuation']}"
    else:
        return f"瀛楁暟(瀹芥澗): {stats['total']}"


def count_file(filepath: str, mode: str = MODE_STANDARD) -> Dict[str, int]:
    """
    缁熻鏂囦欢瀛楁暟

    Args:
        filepath: 鏂囦欢璺緞
        mode: 缁熻妯″紡

    Returns:
        瀛楁暟缁熻缁撴灉
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    return count_words(text, mode)


# 鍛戒护琛屾帴鍙?if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("鐢ㄦ硶: python word_count.py <鏂囦欢璺緞> [妯″紡]")
        print("妯″紡: standard(榛樿) | strict | loose")
        sys.exit(1)

    filepath = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else MODE_STANDARD

    try:
        stats = count_file(filepath, mode)
        print(f"鏂囦欢: {filepath}")
        print(format_word_count(open(filepath, 'r', encoding='utf-8').read(), mode))
    except Exception as e:
        print(f"閿欒: {e}")
        sys.exit(1)
