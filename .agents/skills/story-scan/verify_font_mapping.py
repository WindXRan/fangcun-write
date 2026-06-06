"""
验证 CHAR_SEQUENCE 字体映射完整性。

原理：番茄小说使用自定义字体做反爬，页面源码中的文字是 Unicode 私有区字符（U+E3E0 起始），
浏览器通过 @font-face 加载自定义 .woff 字体来渲染为正常中文。
Playwright 抓取时，innerText 返回的是浏览器渲染后的可见文字（真实中文），
而 innerHTML 中仍保留原始的私有区字符。

本脚本同时获取 innerHTML（含私有区编码）和 innerText（浏览器渲染的真实文字），
逐字符对比，找出 CHAR_SEQUENCE 中映射为替换字符的位置对应的真实文字。

用法：
    python verify_font_mapping.py
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import json
from playwright.sync_api import sync_playwright

START_CODE = 58344  # 0xE3E0
CHAR_SEQUENCE = [
    "D", "在", "主", "特", "家", "军", "然", "表", "场", "4", "要", "只", "v", "和", "�", "6", "别", "还", "g", "现", "儿", "岁", "�", "�", "此", "象", "月", "3", "出", "战", "工", "相", "o", "男", "直", "失", "世", "F", "都", "平", "文", "什", "V", "O", "将", "真", "T", "那", "当", "�", "会", "立", "些", "u", "是", "十", "张", "学", "气", "大", "爱", "两", "命", "全", "后", "东", "性", "通", "被", "1", "它", "乐", "接", "而", "感", "车", "山", "公", "了", "常", "以", "何", "可", "话", "先", "p", "i", "叫", "轻", "M", "士", "w", "着", "变", "尔", "快", "l", "个", "说", "少", "色", "里", "安", "花", "远", "7", "难", "师", "放", "t", "报", "认", "面", "道", "S", "�", "克", "地", "度", "I", "好", "机", "U", "民", "写", "把", "万", "同", "水", "新", "没", "书", "电", "吃", "像", "斯", "5", "为", "y", "白", "几", "日", "教", "看", "但", "第", "加", "候", "作", "上", "拉", "住", "有", "法", "r", "事", "应", "位", "利", "你", "声", "身", "国", "问", "马", "女", "他", "Y", "比", "父", "x", "A", "H", "N", "s", "X", "边", "美", "对", "所", "金", "活", "回", "意", "到", "z", "从", "j", "知", "又", "内", "因", "点", "Q", "三", "定", "8", "R", "b", "正", "或", "夫", "向", "德", "听", "更", "�", "得", "告", "并", "本", "q", "过", "记", "L", "让", "打", "f", "人", "就", "者", "去", "原", "满", "体", "做", "经", "K", "走", "如", "孩", "c", "G", "给", "使", "物", "�", "最", "笑", "部", "�", "员", "等", "受", "k", "行", "一", "条", "果", "动", "光", "门", "头", "见", "往", "自", "解", "成", "处", "天", "能", "于", "名", "其", "发", "总", "母", "的", "死", "手", "入", "路", "进", "心", "来", "h", "时", "力", "多", "开", "已", "许", "d", "至", "由", "很", "界", "n", "小", "与", "Z", "想", "代", "么", "分", "生", "口", "再", "妈", "望", "次", "西", "风", "种", "带", "J", "�", "实", "情", "才", "这", "�", "E", "我", "神", "格", "长", "觉", "间", "年", "眼", "无", "不", "亲", "关", "结", "0", "友", "信", "下", "却", "重", "己", "老", "2", "音", "字", "m", "呢", "明", "之", "前", "高", "P", "B", "目", "太", "e", "9", "起", "稜", "她", "也", "W", "用", "方", "子", "英", "每", "理", "便", "四", "数", "期", "中", "C", "外", "样", "a", "海", "们", "任"
]

# 找出所有替换字符的索引
replacement_indices = {i for i, ch in enumerate(CHAR_SEQUENCE) if ch == "�"}


def decode_text(text: str) -> str:
    if not text:
        return ""
    result = []
    for char in text:
        code = ord(char)
        idx = code - START_CODE
        if 0 <= idx < len(CHAR_SEQUENCE):
            result.append(CHAR_SEQUENCE[idx])
        else:
            result.append(char)
    return "".join(result)


def is_private_use(char):
    """判断字符是否在 Unicode 私有使用区"""
    code = ord(char)
    return (0xE000 <= code <= 0xF8FF or  # BMP PUA
            0xF0000 <= code <= 0xFFFFD or  # Supplementary PUA-A
            0x100000 <= code <= 0x10FFFD)  # Supplementary PUA-B


def main():
    # 抓取一个排行榜页面，对比 innerHTML 和 innerText
    url = "https://fanqienovel.com/rank/0_1_1139"  # 女频新书榜-古风世情

    print(f"正在访问: {url}")
    print("请等待页面加载...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(url, wait_until="load", timeout=15000)
        page.wait_for_selector('a[href^="/page/"]', timeout=10000)

        # 滚动加载更多内容
        for _ in range(3):
            page.evaluate("window.scrollBy(0, window.innerHeight)")
            import time; time.sleep(1)

        # 提取所有书名卡片的 innerHTML 和 innerText 进行对比
        comparison_data = page.evaluate("""
        () => {
            const results = [];
            const links = document.querySelectorAll('a[href^="/page/"]');
            const seen = new Set();
            links.forEach(link => {
                let container = link.parentElement;
                let depth = 0;
                while (container && depth < 6) {
                    if (container.querySelector('img') && container.innerText.includes('在读')) {
                        const href = link.getAttribute('href');
                        if (seen.has(href)) break;
                        seen.add(href);

                        // 获取 innerHTML（含私有区字符）
                        const htmlContent = container.innerHTML;
                        // 获取 innerText（浏览器渲染后的可见文字）
                        const visibleText = container.innerText;

                        // 提取 img alt 作为书名
                        const img = container.querySelector('img');
                        const altText = img ? img.getAttribute('alt') : '';

                        results.push({
                            href: href,
                            html: htmlContent.substring(0, 500),
                            text: visibleText.substring(0, 200),
                            alt: altText || ''
                        });
                        break;
                    }
                    container = container.parentElement;
                    depth++;
                }
            });
            return results.slice(0, 10);  // 只取前10条
        }
        """)

        browser.close()

    if not comparison_data:
        print("未提取到任何书籍数据，可能页面加载失败。")
        return

    print(f"提取到 {len(comparison_data)} 条书籍数据\n")
    print("=" * 80)

    # 统计发现的私有区字符
    found_private_chars = {}  # {unicode_code: set of rendered chars}

    for i, item in enumerate(comparison_data):
        print(f"\n--- 书籍 #{i+1} ---")
        print(f"  链接: {item['href']}")
        print(f"  alt书名: {item['alt']}")
        print(f"  渲染文本(前100): {item['text'][:100]}")

        # 从 innerHTML 中找出私有区字符
        html = item['html']
        pua_chars_in_html = set()
        for ch in html:
            if is_private_use(ch):
                pua_chars_in_html.add(ch)

        if pua_chars_in_html:
            print(f"  发现 {len(pua_chars_in_html)} 个私有区字符:")
            for ch in sorted(pua_chars_in_html, key=lambda c: ord(c)):
                code = ord(ch)
                idx = code - START_CODE
                mapped = CHAR_SEQUENCE[idx] if 0 <= idx < len(CHAR_SEQUENCE) else "?"
                is_replacement = idx in replacement_indices
                status = " *** 替换字符! ***" if is_replacement else ""
                print(f"    U+{code:04X} (idx={idx}) -> '{mapped}'{status}")

                if is_replacement:
                    if code not in found_private_chars:
                        found_private_chars[code] = set()
                    # 尝试从上下文推断真实字符
                    # 找这个字符在 innerHTML 中的上下文
                    pos = html.find(ch)
                    while pos != -1:
                        context_start = max(0, pos - 5)
                        context_end = min(len(html), pos + 6)
                        context = html[context_start:context_end]
                        print(f"      上下文: ...{repr(context)}...")
                        pos = html.find(ch, pos + 1)
        else:
            print("  未发现私有区字符（可能该区域文本未使用自定义字体）")

    # 总结
    print("\n" + "=" * 80)
    print("\n验证结论：")
    print(f"CHAR_SEQUENCE 中共有 {len(replacement_indices)} 个替换字符 (�)")

    # 检查已抓取数据中是否实际用到了这些替换字符位置
    used_replacement_indices = set()
    for item in comparison_data:
        for ch in item['html']:
            if is_private_use(ch):
                idx = ord(ch) - START_CODE
                if idx in replacement_indices:
                    used_replacement_indices.add(idx)

    if used_replacement_indices:
        print(f"\n在页面中实际用到的替换字符位置: {sorted(used_replacement_indices)}")
        print("这些位置需要补充正确的映射字符！")
        print("\n建议：对比浏览器中显示的正确文字，更新 CHAR_SEQUENCE 中对应索引的值。")
    else:
        print("\n在本次抓取的页面中，未发现使用替换字符位置的私有区编码。")
        print("这些位置可能对应极少使用的生僻字，暂时不影响正常抓取。")
        print("建议持续观察，如果发现抓取结果中出现 '�' 或乱码，再补充映射。")

    # 额外：列出所有替换字符位置供参考
    print(f"\n所有替换字符位置列表：")
    for idx in sorted(replacement_indices):
        code = START_CODE + idx
        print(f"  索引 {idx:3d} | U+{code:04X}")


if __name__ == "__main__":
    main()
