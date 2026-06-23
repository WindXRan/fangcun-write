"""
蛙蛙写作投稿自动填表 — 用户手动提交

用法：
    python .agents/skills/story-publish/submit.py --config configs/xxx.json
    python .agents/skills/story-publish/submit.py --book "生娃躺赢2" --author "宜莀" --file "export/xxx.txt"
"""

import os
import re
import json
import argparse
import time
from pathlib import Path

# 页面数据
SUBMIT_URL = "https://wawawriter.com/app/submission/create"

# 简介模板
BLURB = """周小荷是十里八乡出了名的笨姑娘。

种地下田样样不会，烧饭做菜回回翻车，连喂鸡都能把鸡喂丢。爹娘走后，她带着弟弟妹妹熬了一年，把家底熬得只剩三间破屋和半缸米。

为换弟妹活路，她把自己嫁给了镇上陈家做填房。

谁料这个年代生娃难，多少媳妇三年五年没动静。

偏偏周小荷天赋异禀，干啥啥不行，生娃没人比得上，一年一胎从不间断。

她不想争宠也不想管家，好在陈家婆婆明事理，大嫂能干活，丈夫知道她笨但知道她心肠好。

从前人人都说她没出息，如今凭一副好肚皮翻身，被婆家护着、妯娌帮着、弟妹敬着、孩子围着，躺赢一辈子。

沙雕又圆满，啥都不会，也过得很好。"""


def fill_form(page, data):
    """填充投稿表单的所有字段。"""

    # === 1. 文件上传 ===
    file_input = page.locator('input[type="file"]').first
    if file_input.count() > 0 and data.get("file"):
        abs_path = str(Path(data["file"]).resolve())
        file_input.set_input_files(abs_path)
        print(f"  [OK] 上传文件: {abs_path}")
    else:
        print(f"  [WARN] 未找到文件上传控件或文件不存在")

    # === 2. 文本字段 ===
    text_fields = {
        "作品名称": data.get("book_name", ""),
        "笔名": data.get("author", ""),
        "作品字数": str(data.get("word_count", "")),
        "作品简介": BLURB.strip(),
    }
    for label, value in text_fields.items():
        if not value:
            continue
        # 找 label 对应的 input/textarea
        inp = page.locator(f'input[placeholder*="{label}"]').first
        if inp.count() == 0:
            inp = page.locator(f'textarea[placeholder*="{label}"]').first
        if inp.count() == 0:
            # 尝试通用查找
            inp = page.get_by_label(label).first
        if inp.count() > 0:
            inp.fill(value)
            print(f"  [OK] {label}: {value[:30]}{'...' if len(value) > 30 else ''}")

    # === 3. 作品分类 — 长篇（已默认选中，跳过） ===

    # === 4. 作品频道 — 女频 ===
    channel_map = {"男频": "男频", "女频": "女频", "全频": "全频"}
    channel = data.get("channel", "女频")
    ch_label = channel_map.get(channel, channel)
    try:
        page.get_by_text(ch_label, exact=True).first.click()
        print(f"  [OK] 作品频道: {ch_label}")
    except Exception:
        print(f"  [WARN] 作品频道选择失败: {ch_label}")

    # === 5. 作品状态 — 连载中 ===
    status_map = {"连载中": "连载中", "已完结": "已完结"}
    status = data.get("status", "连载中")
    st_label = status_map.get(status, status)
    try:
        page.get_by_text(st_label, exact=True).first.click()
        print(f"  [OK] 作品状态: {st_label}")
    except Exception:
        print(f"  [WARN] 作品状态选择失败: {st_label}")

    # === 6. 小说类目（三级级联） ===
    class_path = data.get("category", [])
    if class_path and len(class_path) == 3:
        for i, cat in enumerate(class_path):
            try:
                page.get_by_text(cat, exact=True).first.click()
                time.sleep(0.5)
            except Exception:
                print(f"  [WARN] 类目第{i+1}级选择失败: {cat}")
        print(f"  [OK] 小说类目: {' > '.join(class_path)}")

    # === 7. 标签（多选 + 自定义） ===
    tags = data.get("tags", [])
    if tags:
        for tag in tags:
            try:
                # 尝试匹配预设标签
                el = page.get_by_text(tag, exact=True).first
                if el.count() > 0:
                    el.click()
                    print(f"  [OK] 标签: {tag}")
                else:
                    # 自定义标签输入
                    tag_input = page.locator('input[placeholder*="自定义标签"]').first
                    if tag_input.count() > 0:
                        tag_input.fill(tag)
                        # 点「添加」按钮
                        page.get_by_text("添加", exact=True).first.click()
                        print(f"  [OK] 自定义标签: {tag}")
            except Exception as e:
                print(f"  [WARN] 标签失败: {tag}: {e}")

    print(f"\n  表单已填充完毕，请检查后手动点击「提交」")


def main():
    parser = argparse.ArgumentParser(description="蛙蛙写作投稿自动填表")
    parser.add_argument("--config", default=None, help="项目 config.json")
    parser.add_argument("--book", default="生娃躺赢2")
    parser.add_argument("--author", default="宜莀")
    parser.add_argument("--file", default=None)
    parser.add_argument("--channel", default="女频", choices=["男频", "女频", "全频"])
    parser.add_argument("--status", default="连载中", dest="book_status", choices=["连载中", "已完结"])
    parser.add_argument("--dry-run", action="store_true", help="只展示要填的内容，不操作浏览器")
    args = parser.parse_args()

    data = {
        "book_name": args.book,
        "author": args.author,
        "channel": args.channel,
        "status": args.book_status,
        "word_count": "",
        "file": args.file,
        "category": ["现代言情", "种田经商", "年代种田"],
        "tags": ["年代", "种田", "养娃", "日常", "治愈", "轻松", "锦鲤"],
    }

    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            data["book_name"] = cfg.get("book_name", data["book_name"])
            data["author"] = cfg.get("author", data["author"])
            data["file"] = os.path.join(cfg.get("rewrites_dir", ""), "export", f"{data['book_name']}.txt")

    if data["file"]:
        # 统计字数
        fp = Path(data["file"])
        if fp.exists():
            text = fp.read_text(encoding="utf-8")
            data["word_count"] = len(re.sub(r'\s', '', text))

    if args.dry_run:
        print("=== 投稿预览（dry-run） ===\n")
        for k, v in data.items():
            print(f"  {k}: {v}")
        return

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # 使用持久化浏览器上下文（复用登录态）
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"  打开: {SUBMIT_URL}")
        page.goto(SUBMIT_URL, wait_until="networkidle")
        time.sleep(2)

        print(f"  填写: {data['book_name']}")
        fill_form(page, data)

        input("\n  按 Enter 关闭浏览器...")
        browser.close()


if __name__ == "__main__":
    main()
