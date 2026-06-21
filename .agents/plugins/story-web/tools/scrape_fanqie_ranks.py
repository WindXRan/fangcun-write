import os
import sys
import json
import time
import tempfile
import random
from datetime import datetime
from playwright.sync_api import sync_playwright

# Windows 控制台默认 GBK 编码，无法输出 emoji，强制使用 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

START_CODE = 58344  # 0xE3E0
CHAR_SEQUENCE = [
    "D", "在", "主", "特", "家", "军", "然", "表", "场", "4", "要", "只", "v", "和", "�", "6", "别", "还", "g", "现", "儿", "岁", "�", "�", "此", "象", "月", "3", "出", "战", "工", "相", "o", "男", "直", "失", "世", "F", "都", "平", "文", "什", "V", "O", "将", "真", "T", "那", "当", "�", "会", "立", "些", "u", "是", "十", "张", "学", "气", "大", "爱", "两", "命", "全", "后", "东", "性", "通", "被", "1", "它", "乐", "接", "而", "感", "车", "山", "公", "了", "常", "以", "何", "可", "话", "先", "p", "i", "叫", "轻", "M", "士", "w", "着", "变", "尔", "快", "l", "个", "说", "少", "色", "里", "安", "花", "远", "7", "难", "师", "放", "t", "报", "认", "面", "道", "S", "�", "克", "地", "度", "I", "好", "机", "U", "民", "写", "把", "万", "同", "水", "新", "没", "书", "电", "吃", "像", "斯", "5", "为", "y", "白", "几", "日", "教", "看", "但", "第", "加", "候", "作", "上", "拉", "住", "有", "法", "r", "事", "应", "位", "利", "你", "声", "身", "国", "问", "马", "女", "他", "Y", "比", "父", "x", "A", "H", "N", "s", "X", "边", "美", "对", "所", "金", "活", "回", "意", "到", "z", "从", "j", "知", "又", "内", "因", "点", "Q", "三", "定", "8", "R", "b", "正", "或", "夫", "向", "德", "听", "更", "�", "得", "告", "并", "本", "q", "过", "记", "L", "让", "打", "f", "人", "就", "者", "去", "原", "满", "体", "做", "经", "K", "走", "如", "孩", "c", "G", "给", "使", "物", "�", "最", "笑", "部", "�", "员", "等", "受", "k", "行", "一", "条", "果", "动", "光", "门", "头", "见", "往", "自", "解", "成", "处", "天", "能", "于", "名", "其", "发", "总", "母", "的", "死", "手", "入", "路", "进", "心", "来", "h", "时", "力", "多", "开", "已", "许", "d", "至", "由", "很", "界", "n", "小", "与", "Z", "想", "代", "么", "分", "生", "口", "再", "妈", "望", "次", "西", "风", "种", "带", "J", "�", "实", "情", "才", "这", "�", "E", "我", "神", "格", "长", "觉", "间", "年", "眼", "无", "不", "亲", "关", "结", "0", "友", "信", "下", "却", "重", "己", "老", "2", "音", "字", "m", "呢", "明", "之", "前", "高", "P", "B", "目", "太", "e", "9", "起", "稜", "她", "也", "W", "用", "方", "子", "英", "每", "理", "便", "四", "数", "期", "中", "C", "外", "样", "a", "海", "们", "任"
]

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

# 排行榜配置：URL模式为 /rank/{gender}_{type}_{category_id}
# gender: 0=女频, 1=男频
# type: 1=新书榜, 2=阅读榜
# entry_cat: 该榜单的首个分类ID（女频用1139，男频用1141）
RANK_CONFIGS = [
    {"gender": 1, "type": 1, "name": "男频新书榜", "prefix": "male_new",    "entry_cat": "1141"},
    {"gender": 1, "type": 2, "name": "男频阅读榜", "prefix": "male_read",   "entry_cat": "1141"},
    {"gender": 0, "type": 1, "name": "女频新书榜", "prefix": "female_new",  "entry_cat": "1139"},
    {"gender": 0, "type": 2, "name": "女频阅读榜", "prefix": "female_read", "entry_cat": "1139"},
]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def scrape_rank_type(page, rank_config, limit=30, sleep_sec=5):
    """抓取指定类型的排行榜（女频新书/阅读、男频新书/阅读）"""
    gender = rank_config["gender"]
    rank_type = rank_config["type"]
    rank_name = rank_config["name"]
    prefix = rank_config["prefix"]
    entry_cat = rank_config.get("entry_cat", "1139")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    output_file = os.path.join(OUTPUT_DIR, f"fanqie_{prefix}_ranks_{date_str}.json")
    state_file = os.path.join(OUTPUT_DIR, f"task_state_{prefix}_{date_str}.json")

    # ------------- 状态恢复逻辑 -------------
    completed_cats = []
    all_categories = []
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            try:
                state = json.load(f)
                completed_cats = state.get("completed", [])
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ 状态文件读取失败，将重新开始: {state_file} ({e})")
    if os.path.exists(output_file) and len(completed_cats) > 0:
        with open(output_file, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
                all_categories = existing.get("categories", [])
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ 数据文件读取失败，将重新开始: {output_file} ({e})")
    # ----------------------------------------

    # 访问该类型排行榜的入口页面
    init_url = f"https://fanqienovel.com/rank/{gender}_{rank_type}_{entry_cat}"
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 开始抓取{rank_name}，入口：{init_url}")

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            page.goto(init_url, wait_until="load", timeout=15000)
            page.wait_for_selector('a[href^="/page/"]', timeout=5000)
            break
        except Exception as e:
            if attempt < max_retries:
                print(f"⚠️ 访问{rank_name}入口页面失败（第{attempt}次），重试中... ({e})")
                time.sleep(3)
            else:
                print(f"❌ 访问{rank_name}入口页面失败（已重试{max_retries}次）: {e}")
                return

    # 动态解析页面左侧拥有的所有类别目录
    categories_js = f"""
    () => {{
        return Array.from(document.querySelectorAll('a'))
            .filter(a => a.href.includes('/rank/{gender}_{rank_type}_'))
            .map(a => ({{
                name: a.innerText.trim(),
                href: a.getAttribute('href')
            }}));
    }}
    """
    categories = page.evaluate(categories_js)
    print(f"✅ 成功提取到 {len(categories)} 个{rank_name}分类标签")

    for cat in categories:
        cat_name = cat["name"]
        cat_href = cat["href"]

        if cat_name in completed_cats:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏭️ 跳过已完成：{cat_name}")
            continue

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📖 抓取{rank_name} - {cat_name}")

        # 分类切换重试机制（最多3次）
        max_cat_retries = 3
        cat_switch_success = False
        for cat_attempt in range(max_cat_retries):
            try:
                page.locator(f"a[href='{cat_href}']").click()
                time.sleep(2)
                page.wait_for_selector('a[href^="/page/"]', timeout=5000)
                cat_switch_success = True
                break
            except Exception as e:
                if cat_attempt < max_cat_retries - 1:
                    print(f"⚠️ 切换分类出错，重试 {cat_attempt + 1}/{max_cat_retries}: {e}")
                    time.sleep(2)
                else:
                    print(f"⚠️ 切换分类出错，跳过 {cat_name}: {e}")

        if not cat_switch_success:
            continue

        # 动态滚动：检测是否已滚动到底部或达到目标数量
        max_scrolls = 25  # 最大滚动次数上限
        target_count = limit + 10  # 多加载一些以确保有足够的书
        scroll_count = 0
        no_new_count = 0  # 连续无新书加载的次数

        while scroll_count < max_scrolls:
            try:
                # 获取当前加载的书籍数量
                current_count = page.evaluate("""
                    () => document.querySelectorAll('a[href^="/page/"]').length
                """)

                # 滚动一屏
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(2)
                scroll_count += 1

                # 检查新加载的书籍数量
                new_count = page.evaluate("""
                    () => document.querySelectorAll('a[href^="/page/"]').length
                """)

                if new_count > current_count:
                    no_new_count = 0  # 有新书加载，重置计数器
                else:
                    no_new_count += 1

                # 如果已加载足够数量或连续5次无新书加载，停止滚动
                if new_count >= target_count or no_new_count >= 5:
                    break
            except Exception as e:
                print(f"  ⚠️ 滚动异常，停止加载: {e}")
                break

        # 提取书籍数据
        extract_js = """
        () => {
            const bookMap = new Map();
            const links = document.querySelectorAll('a[href^="/page/"]');
            links.forEach(link => {
                let container = link.parentElement;
                let depth = 0;
                while (container && depth < 6) {
                    if (container.querySelector('img') && container.innerText.includes('在读')) {
                        const href = link.getAttribute('href');
                        if (!bookMap.has(href)) {
                            bookMap.set(href, container);
                        }
                        break;
                    }
                    container = container.parentElement;
                    depth++;
                }
            });

            const cards = Array.from(bookMap.values());
            const results = [];
            for (const item of cards) {
                let imgNode = item.querySelector('img');
                let cover = imgNode ? imgNode.getAttribute('src') : "";

                let title = "";
                if (imgNode && imgNode.getAttribute('alt')) {
                    title = imgNode.getAttribute('alt').trim();
                }
                if (!title) {
                    let textTitleNode = item.querySelector('h4, .title, h1') || item.querySelector('a[href^="/page/"]');
                    if (textTitleNode) {
                        let text = textTitleNode.innerText.trim();
                        if (text && !/^\d+$/.test(text)) {
                            title = text;
                        }
                    }
                }
                if (!title) title = "未知";
                if (title.includes("榜单说明")) continue;

                let authorNode = item.querySelector('.author, .author-name') || item.querySelector('a[href^="/author-page/"]');
                let author = authorNode ? authorNode.innerText.trim() : "未知";

                let reads = "未知";
                const lines = item.innerText.split('\\n');
                for (let line of lines) {
                    if (line.includes('在读')) {
                        reads = line;
                        break;
                    }
                }

                let introNode = item.querySelector('.intro, .abstract, .desc');
                let intro = introNode ? introNode.innerText.trim() : "暂无简介";

                let chapters = "";
                let status = "";
                for (let line of lines) {
                    let chMatch = line.match(/(\d+)\s*章/);
                    if (chMatch) {
                        chapters = chMatch[1];
                    }
                    if (line.includes('完结') || line.includes('完本')) {
                        status = "完结";
                    } else if (line.includes('连载')) {
                        status = "连载中";
                    }
                }

                results.push({
                    title: title,
                    author: author,
                    reads: reads,
                    intro: intro,
                    cover: cover,
                    chapters: chapters,
                    status: status,
                    url: item.querySelector('a[href^="/page/"]').getAttribute('href')
                });
            }
            return results;
        }
        """

        try:
            books_data = page.evaluate(extract_js)
        except Exception as e:
            print(f"JS抽取失败 {cat_name}: {e}")
            books_data = []

        category_books = []
        for b in books_data[:limit]:
            t = decode_text(b.get("title", ""))
            a = decode_text(b.get("author", ""))
            r_raw = decode_text(b.get("reads", ""))
            i = decode_text(b.get("intro", "")).replace("\\n", " ")
            c = b.get("cover", "")

            if "在读" in r_raw:
                parts = r_raw.split("在读")
                if len(parts) > 1:
                    cleaned_r = parts[1].replace(":", "").replace("：", "").strip()
                else:
                    cleaned_r = r_raw
            else:
                cleaned_r = r_raw

            # 验证URL：处理None、空字符串、完整URL、相对路径等情况
            raw_url = b.get("url", "")
            if not raw_url:
                url = ""
            elif raw_url.startswith("http://") or raw_url.startswith("https://"):
                # 已经是完整URL，直接使用
                url = raw_url
            else:
                # 相对路径，拼接域名
                url = "https://fanqienovel.com" + raw_url

            category_books.append({
                "title": t,
                "author": a,
                "reads": cleaned_r,
                "intro": i,
                "cover": c,
                "chapters": decode_text(b.get("chapters", "")),
                "status": decode_text(b.get("status", "")),
                "url": url
            })

        # 去重：恢复模式下跳过已抓取的分类
        existing_names = {c["name"] for c in all_categories}
        if cat_name in existing_names:
            print(f"  ⏭️ {cat_name}: 已存在，跳过重复写入")
        else:
            all_categories.append({
                "name": cat_name,
                "books": category_books
            })

        # 数据质量校验
        if len(category_books) == 0:
            print(f"  ⚠️ {cat_name}: 未提取到任何书籍，可能页面加载异常")
        elif len(category_books) < 10:
            print(f"  ⚠️ {cat_name}: 仅提取到 {len(category_books)} 本书，数量偏少")

        # 检查是否有"未知"标题
        unknown_count = sum(1 for b in category_books if b["title"] == "未知")
        if unknown_count > 0:
            print(f"  ⚠️ {cat_name}: {unknown_count} 本书标题为'未知'，可能提取异常")

        # 原子写入：先写数据文件，再写状态文件
        # 顺序设计：如果在两步之间崩溃，状态文件不会标记该分类完成，
        # 下次运行会重新抓取（安全重复），而不会丢失数据

        # 先写数据文件（原子写入）
        snapshot = {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "rank_type": rank_name,
            "categories": all_categories
        }
        data_tmp = tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=os.path.dirname(output_file),
            suffix='.tmp', delete=False
        )
        try:
            json.dump(snapshot, data_tmp, ensure_ascii=False, indent=2)
            data_tmp.flush()
            os.fsync(data_tmp.fileno())
            data_tmp.close()
            os.replace(data_tmp.name, output_file)  # 原子替换
        except Exception:
            try:
                os.unlink(data_tmp.name)
            except OSError:
                pass
            raise

        # 再更新状态文件（原子写入）
        completed_cats.append(cat_name)
        state_tmp = tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=os.path.dirname(state_file),
            suffix='.tmp', delete=False
        )
        try:
            json.dump({"completed": completed_cats}, state_tmp, ensure_ascii=False)
            state_tmp.flush()
            os.fsync(state_tmp.fileno())
            state_tmp.close()
            os.replace(state_tmp.name, state_file)  # 原子替换
        except Exception:
            try:
                os.unlink(state_tmp.name)
            except OSError:
                pass
            raise

        print(f"  ✅ {cat_name}: {len(category_books)} 本书")
        time.sleep(sleep_sec)

    # 最终数据质量校验
    cat_names = [c["name"] for c in all_categories]
    duplicates = [name for name in cat_names if cat_names.count(name) > 1]
    if duplicates:
        print(f"  ⚠️ 发现重复分类：{set(duplicates)}，可能存在数据问题")

    total_books = sum(len(c["books"]) for c in all_categories)
    print(f"✅ {rank_name}抓取完成！共 {len(all_categories)} 个分类，{total_books} 本书。数据：{output_file}")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]


def run_scraper(limit=30, sleep_sec=2):
    """抓取所有排行榜类型"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ua = random.choice(USER_AGENTS)
            context = browser.new_context(user_agent=ua)
            page = context.new_page()

            # 依次抓取每种排行榜类型
            for rank_config in RANK_CONFIGS:
                scrape_rank_type(page, rank_config, limit, sleep_sec)
        finally:
            browser.close()

    print(f"\n🎉 所有排行榜抓取完成！数据目录：{OUTPUT_DIR}")

if __name__ == "__main__":
    print("开始执行番茄小说排行榜全量抓取（女频新书/阅读、男频新书/阅读）...")
    run_scraper(limit=30, sleep_sec=2)
