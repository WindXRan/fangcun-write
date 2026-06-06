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

# 只测试一个榜单
RANK_CONFIGS = [
    {"gender": 1, "type": 1, "name": "男频新书榜", "prefix": "male_new",    "entry_cat": "1141"},
]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def scrape_rank_type(page, rank_config, limit=5, sleep_sec=2):
    """抓取指定类型的排行榜（只抓取5本书测试）"""
    gender = rank_config["gender"]
    rank_type = rank_config["type"]
    rank_name = rank_config["name"]
    prefix = rank_config["prefix"]
    entry_cat = rank_config["entry_cat"]
    
    print(f"\n🔍 开始抓取 {rank_name}...")
    
    # 访问番茄小说排行榜页面
    url = f"https://fanqienovel.com/rank/{gender}_{rank_type}_{entry_cat}"
    print(f"  📍 访问: {url}")
    
    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=10000)
        print(f"  ✅ 页面加载完成")
        
        # 获取页面标题
        title = page.title()
        print(f"  📄 页面标题: {title}")
        
        # 等待一下
        time.sleep(2)
        
        # 尝试获取一些内容
        content = page.content()
        print(f"  📏 页面内容长度: {len(content)} 字符")
        
        # 尝试查找书籍列表
        books = page.query_selector_all('[class*="book"], [class*="rank"], [class*="item"]')
        print(f"  📚 找到 {len(books)} 个可能的书籍元素")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 抓取失败: {e}")
        return False

def run_scraper(limit=5, sleep_sec=2):
    """抓取测试"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            context = browser.new_context(user_agent=ua)
            page = context.new_page()
            
            # 只测试一个榜单
            for rank_config in RANK_CONFIGS:
                scrape_rank_type(page, rank_config, limit, sleep_sec)
        finally:
            browser.close()

    print(f"\n🎉 测试完成！")

if __name__ == "__main__":
    print("开始测试番茄小说排行榜抓取...")
    run_scraper(limit=5, sleep_sec=2)