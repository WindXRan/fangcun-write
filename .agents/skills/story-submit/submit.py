"""
story-submit: 自动投稿到蛙蛙写作平台
用playwright操作Element Plus表单。
"""
import os, re, sys, time, argparse, subprocess, socket, json
from pathlib import Path

DEFAULT_PEN_NAME = "一盏清酒"
QUARK_EXE = r"C:\Users\Administrator\AppData\Local\Programs\Quark\quark.exe"
QUARK_USER_DATA = r"C:\Users\Administrator\AppData\Local\Quark\User Data"
CDP_PORT = 9222

# 标签缓存文件路径
TAGS_CACHE_PATH = Path(__file__).parent / "tags_cache.json"


def close_popups(page):
    """关闭所有可能的弹窗和通知"""
    try:
        page.evaluate("""() => {
            // 关闭通知弹窗
            document.querySelectorAll('.el-notification__closeBtn, .el-message-box__close, .el-dialog__close').forEach(el => {
                try { el.click(); } catch(e) {}
            });
            // 关闭可能的遮罩层
            document.querySelectorAll('.el-overlay, .el-modal, .v-modal').forEach(el => {
                try { el.click(); } catch(e) {}
            });
            // 关闭右上角通知面板
            document.querySelectorAll('.notification-panel, .message-panel, [class*="notification"], [class*="message"]').forEach(el => {
                try { 
                    if (el.style.display !== 'none') {
                        el.style.display = 'none';
                    }
                } catch(e) {}
            });
            // 关闭所有tooltip
            document.querySelectorAll('.el-popper, .el-tooltip__popper').forEach(el => {
                try {
                    el.style.display = 'none';
                } catch(e) {}
            });
        }""")
    except:
        pass
    time.sleep(0.3)


def parse_book_info(txt_path):
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    info = {}
    m = re.search(r'书名[：:]\s*(.+)', content)
    if m: info['title'] = m.group(1).strip()
    m = re.search(r'简介[：:]\n(.+?)(?:\n={10,}|\Z)', content, re.DOTALL)
    if m: info['blurb'] = m.group(1).strip()
    m = re.search(r'标签[：:]\s*(.+)', content)
    if m: info['tags'] = [t.strip() for t in m.group(1).strip().split('|') if t.strip()]
    m = re.search(r'(?:字数|总字数)[：:]\s*(\d+)', content)
    if m: info['word_count'] = int(m.group(1))
    return info


def select_tags_with_llm(title, blurb):
    """使用LLM根据书名和简介选择标签"""
    import subprocess
    
    # 读取标签缓存
    if not TAGS_CACHE_PATH.exists():
        print("[警告] 标签缓存文件不存在，使用默认标签", flush=True)
        return ['言情', '穿越', '甜宠', '暗恋', '七零年代']
    
    with open(TAGS_CACHE_PATH, 'r', encoding='utf-8') as f:
        tags_data = json.load(f)
    
    # 构建标签说明
    tags_desc = ""
    for category, info in tags_data.items():
        limit = info['limit']
        options = '、'.join(info['options'])
        tags_desc += f"\n{category}（限制：{limit}）：{options}"
    
    # 构建prompt
    prompt = f"""你是一个网文编辑，需要根据书名和简介选择合适的标签。

书名：{title}
简介：{blurb}

平台标签分类如下：
{tags_desc}

请根据书名和简介，从每个分类中选择合适的标签。
要求：
1. 题材：选1-2个
2. 情节：选1-3个
3. 情绪：选2-3个
4. 时空：选0-1个

请直接返回JSON格式，例如：
{{"题材": ["言情", "穿越"], "情节": ["强取豪夺"], "情绪": ["甜宠", "暗恋"], "时空": ["七零年代"]}}"""

    try:
        # 调用LLM
        api_key = os.environ.get("API_KEY", "")
        base_url = os.environ.get("API_BASE_URL", "https://api.deepseek.com")
        model = os.environ.get("API_MODEL", "deepseek-chat")
        
        # 写入临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(f'''
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from openai import OpenAI

client = OpenAI(
    api_key="{api_key}",
    base_url="{base_url}"
)

prompt = """{prompt}"""

response = client.chat.completions.create(
    model="{model}",
    messages=[{{"role": "user", "content": prompt}}],
    temperature=0.3
)

print(response.choices[0].message.content)
''')
            temp_file = f.name
        
        result = subprocess.run(
            ['python', temp_file],
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8'
        )
        
        # 删除临时文件
        os.unlink(temp_file)
        
        if result.returncode == 0:
            # 解析LLM返回的JSON
            response = result.stdout.strip()
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                tags_dict = json.loads(json_match.group())
                # 合并所有标签
                all_tags = []
                for category_tags in tags_dict.values():
                    all_tags.extend(category_tags)
                print(f"[LLM选择标签] {all_tags}", flush=True)
                return all_tags
    except Exception as e:
        print(f"[LLM调用失败] {e}", flush=True)
    
    # 默认标签
    return ['言情', '穿越', '甜宠', '暗恋', '七零年代']


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0


def is_quark_running():
    try:
        r = subprocess.run('tasklist /FI "IMAGENAME eq quark.exe"', capture_output=True, text=True, shell=True)
        return "quark.exe" in r.stdout.lower()
    except: return False


def select_el_option(page, placeholder_text, option_text):
    """选择Element Plus下拉框选项 - 优先使用JS点击"""
    # 设置viewport确保元素有正确尺寸
    page.set_viewport_size({"width": 1280, "height": 900})
    time.sleep(0.5)
    
    # 滚动到select区域
    page.evaluate("""(ph) => {
        for (let el of document.querySelectorAll('.el-select')) {
            let inp = el.querySelector('input');
            if (inp && inp.placeholder && inp.placeholder.includes(ph)) {
                inp.scrollIntoView({behavior:'instant', block:'center'});
                return true;
            }
        }
        return false;
    }""", placeholder_text)
    time.sleep(0.5)
    
    # 用JS直接点击select触发器
    page.evaluate("""(ph) => {
        for (let el of document.querySelectorAll('.el-select')) {
            let inp = el.querySelector('input');
            if (inp && inp.placeholder && inp.placeholder.includes(ph)) {
                el.click();
                return true;
            }
        }
        return false;
    }""", placeholder_text)
    time.sleep(1)
    
    # 找到dropdown面板中的选项并点击
    # dropdown是teleported到body的，需要找可见的dropdown
    option_rect = page.evaluate("""(text) => {
        let dropdowns = document.querySelectorAll('.el-select-dropdown');
        for (let dd of dropdowns) {
            let parent = dd.closest('.el-popper');
            if (parent && parent.style.display === 'none') continue;
            let items = dd.querySelectorAll('.el-select-dropdown__item');
            for (let item of items) {
                if (item.innerText.trim() === text) {
                    let r = item.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) {
                        return {x: r.x + r.width/2, y: r.y + r.height/2};
                    }
                }
            }
        }
        // 备用：找所有可见的dropdown item
        for (let item of document.querySelectorAll('.el-select-dropdown__item')) {
            if (item.innerText.trim() === text) {
                let r = item.getBoundingClientRect();
                if (r.width > 0) return {x: r.x + r.width/2, y: r.y + r.height/2};
            }
        }
        return null;
    }""", option_text)
    
    if option_rect and option_rect['x'] > 50:  # 确保坐标有效
        page.mouse.click(option_rect['x'], option_rect['y'])
        time.sleep(0.5)
    else:
        # 备用：用JS直接点击选项
        page.evaluate("""(text) => {
            for (let item of document.querySelectorAll('.el-select-dropdown__item')) {
                if (item.innerText.trim() === text) {
                    item.click();
                    return true;
                }
            }
            return false;
        }""", option_text)
        time.sleep(0.5)


def select_radio_option(page, group_label, option_text):
    """选择Element Plus radio按钮"""
    page.evaluate("""([group, text]) => {
        // 找到包含group_label的radio组
        const groups = document.querySelectorAll('.el-radio-group, .el-radio-button-group');
        for (const group of groups) {
            const parent = group.closest('.el-form-item');
            if (parent && parent.innerText.includes(group)) {
                // 在组内找到匹配的radio并点击
                const radios = group.querySelectorAll('.el-radio, .el-radio-button');
                for (const radio of radios) {
                    if (radio.innerText.trim().includes(text)) {
                        radio.click();
                        // 也触发input的change事件
                        const input = radio.querySelector('input');
                        if (input) {
                            input.click();
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        return true;
                    }
                }
            }
        }
        // 备用：直接找所有radio
        for (const radio of document.querySelectorAll('.el-radio, .el-radio-button')) {
            if (radio.innerText.trim().includes(text)) {
                radio.click();
                const input = radio.querySelector('input');
                if (input) {
                    input.click();
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
                return true;
            }
        }
        return false;
    }""", [group_label, option_text])
    time.sleep(0.5)


def select_tag_option(page, tag_text):
    """选择蛙蛙写作的标签（非Element Plus标准组件）"""
    # 先滚动到标签区域确保可见
    page.evaluate("""() => {
        const labels = document.querySelectorAll('.form-label');
        for (const label of labels) {
            if (label.innerText.includes('标签')) {
                label.scrollIntoView({behavior: 'instant', block: 'center'});
                break;
            }
        }
    }""")
    time.sleep(0.2)
    
    # 使用JS直接点击标签，避免误点击其他元素
    result = page.evaluate("""(text) => {
        const items = document.querySelectorAll('.flex.flex-wrap .cursor-pointer');
        for (const item of items) {
            if (item.innerText.trim() === text) {
                item.click();
                return true;
            }
        }
        return false;
    }""", tag_text)
    time.sleep(0.3)
    return result


def select_cascader_option(page, options):
    """选择Element Plus级联选择器 - 使用hover触发子菜单"""
    # 强制显示popper
    page.evaluate("""() => {
        document.querySelectorAll('.el-popper, .el-cascader__dropdown').forEach(el => {
            el.style.display = 'block';
            el.style.visibility = 'visible';
            el.style.opacity = '1';
        });
    }""")
    time.sleep(0.5)
    
    # 逐级选择
    for i, opt in enumerate(options):
        if i < len(options) - 1:
            # 非最后一级：用hover触发子菜单
            page.evaluate("""(text) => {
                const menus = document.querySelectorAll('.el-cascader-menu');
                for (const menu of menus) {
                    const items = menu.querySelectorAll('.el-cascader-node');
                    for (const item of items) {
                        const label = item.querySelector('.el-cascader-node__label');
                        if (label && label.innerText.trim() === text) {
                            item.dispatchEvent(new MouseEvent('mouseenter', {bubbles: true}));
                            return true;
                        }
                    }
                }
                return false;
            }""", opt)
            time.sleep(1)
            
            # 强制显示popper
            page.evaluate("""() => {
                document.querySelectorAll('.el-popper, .el-cascader__dropdown').forEach(el => {
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    el.style.opacity = '1';
                });
            }""")
            time.sleep(0.3)
        else:
            # 最后一级：点击选择
            page.evaluate("""(text) => {
                const menus = document.querySelectorAll('.el-cascader-menu');
                const lastMenu = menus[menus.length - 1];
                if (lastMenu) {
                    const items = lastMenu.querySelectorAll('.el-cascader-node');
                    for (const item of items) {
                        const label = item.querySelector('.el-cascader-node__label');
                        if (label && label.innerText.trim() === text) {
                            item.click();
                            return true;
                        }
                    }
                }
                return false;
            }""", opt)
            time.sleep(0.5)


def submit_to_wawawriter(txt_path, headless=False, dry_run=False):
    from playwright.sync_api import sync_playwright

    book_info = parse_book_info(txt_path)
    txt_abs = str(Path(txt_path).resolve())
    if not book_info.get('title'):
        print("无法提取书名", flush=True); return False

    print(f"书名: {book_info['title']}", flush=True)
    print(f"笔名: {DEFAULT_PEN_NAME}", flush=True)
    print(f"字数: {book_info.get('word_count','?')}", flush=True)
    print(f"标签: {book_info.get('tags',[])}", flush=True)

    if not is_port_open(CDP_PORT):
        if is_quark_running():
            print("夸克已运行但未开调试端口。请关闭夸克后重新运行。", flush=True)
            return False
        print("启动夸克...", flush=True)
        subprocess.Popen([
            QUARK_EXE, f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={QUARK_USER_DATA}", "--no-sandbox",
            "https://wawawriter.com/app/submission/create"
        ])
        for i in range(30):
            time.sleep(1)
            if is_port_open(CDP_PORT): print("已启动!", flush=True); break
        else: print("启动超时", flush=True); return False
        time.sleep(5)

    with sync_playwright() as p:
        print("连接浏览器...", flush=True)
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")

        # 每次新开一个页面
        page = browser.contexts[0].new_page()

        # 设置viewport
        page.set_viewport_size({"width": 1280, "height": 900})
        time.sleep(1)

        print("打开投稿页...", flush=True)
        try: page.goto("https://wawawriter.com/app/submission/create", timeout=30000)
        except: pass
        time.sleep(8)
        print(f"URL={page.url}", flush=True)
        
        # 立即关闭通知区域
        close_popups(page)

        if "/login" in page.url:
            print("请在浏览器中登录...", flush=True)
            for i in range(300):
                time.sleep(1)
                if "/login" not in page.url: print("登录成功!", flush=True); break
                if i % 10 == 0: print(f"  等待 {i}s ...", flush=True)
            time.sleep(3)
            page.goto("https://wawawriter.com/app/submission/create", timeout=30000)
            time.sleep(5)
        else:
            print("已登录", flush=True)

        # 如果被重定向到首页，重新导航到投稿页
        if "/submission" not in page.url:
            print("导航到投稿页...", flush=True)
            page.goto("https://wawawriter.com/app/submission/create", timeout=30000)
            time.sleep(5)
            print(f"URL={page.url}", flush=True)

        # 关闭可能的弹窗（通知、邮件等）
        close_popups(page)

        print("[1] 上传文件...", flush=True)
        try:
            page.locator('input[type="file"]').first.set_input_files(txt_abs)
            print("[OK] 已上传", flush=True)
            time.sleep(8)
            close_popups(page)  # 上传后关闭可能的弹窗
        except Exception as e:
            print(f"[X] 上传失败: {e}", flush=True)

        print("[2] 关闭预览弹窗...", flush=True)
        page.locator('button').filter(has_text='下一步').first.click(force=True, timeout=10000)
        time.sleep(3)
        close_popups(page)  # 关闭预览后关闭可能的弹窗
        print("[OK]", flush=True)

        print("[3] 作品名称...", flush=True)
        inp = page.locator('input[placeholder*="作品名称"]').first
        inp.fill(book_info['title'].replace('《','').replace('》',''), force=True, timeout=5000)
        print("[OK]", flush=True)

        print("[4] 笔名...", flush=True)
        inp = page.locator('input[placeholder*="笔名"]').first
        inp.fill(DEFAULT_PEN_NAME, force=True, timeout=5000)
        print("[OK]", flush=True)

        print("[5] 字数...", flush=True)
        inp = page.locator('input[placeholder*="作品字数"]').first
        inp.fill(str(book_info.get('word_count','')), force=True, timeout=5000)
        print("[OK]", flush=True)

        print("[6] 作品频道...", flush=True)
        try:
            select_radio_option(page, '频道', '女频')
            print("[OK] 女频", flush=True)
        except Exception as e:
            print(f"[跳过] 请手动选择频道（女频）: {e}", flush=True)

        print("[7] 作品状态...", flush=True)
        try:
            select_radio_option(page, '状态', '连载中')
            print("[OK] 连载中", flush=True)
        except Exception as e:
            print(f"[跳过] 请手动选择状态（连载中）: {e}", flush=True)

        print("[8] 小说类目...", flush=True)
        try:
            # 先滚动到类目区域
            page.evaluate("""() => {
                const labels = document.querySelectorAll('.form-label');
                for (const label of labels) {
                    if (label.innerText.includes('类目')) {
                        label.scrollIntoView({behavior: 'instant', block: 'center'});
                        break;
                    }
                }
            }""")
            time.sleep(0.5)
            
            # 点击cascader打开面板
            page.locator('.el-cascader').first.click()
            time.sleep(1)
            
            # 选择类目：女频 -> 年代小说 -> 穿书小说
            select_cascader_option(page, ['女频', '年代小说', '穿书小说'])
            close_popups(page)  # 选择类目后关闭可能的弹窗
            print("[OK]", flush=True)
        except Exception as e:
            print(f"[跳过] 请手动选择类目: {e}", flush=True)

        print("[9] 标签...", flush=True)
        try:
            # 先关闭可能的弹窗
            close_popups(page)
            
            # 滚动到标签区域
            page.evaluate("""() => {
                const labels = document.querySelectorAll('.form-label');
                for (const label of labels) {
                    if (label.innerText.includes('标签')) {
                        label.scrollIntoView({behavior: 'instant', block: 'center'});
                        break;
                    }
                }
            }""")
            time.sleep(0.5)
            
            # 点击展开按钮
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.innerText.trim() === '展开') {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }""")
            time.sleep(0.5)
            
            # 使用LLM选择标签
            tags_to_select = select_tags_with_llm(book_info['title'], book_info.get('blurb', ''))
            selected_tags = []
            for tag in tags_to_select:
                if select_tag_option(page, tag):
                    selected_tags.append(tag)
            print(f"[OK] {', '.join(selected_tags)}", flush=True)
        except Exception as e:
            print(f"[跳过] 请手动选择标签: {e}", flush=True)

        print("[10] 简介...", flush=True)
        try:
            area = page.locator('textarea').first
            area.fill(book_info.get('blurb', ''), force=True, timeout=5000)
            print(f"[OK] {len(book_info.get('blurb',''))}字", flush=True)
        except Exception as e:
            print(f"[X] {e}", flush=True)

        if dry_run:
            print("\n[DRY RUN] 已填写，未提交。", flush=True)

        print("\n完成! 请在浏览器中检查并提交。", flush=True)

    return True


def main():
    parser = argparse.ArgumentParser(description='自动投稿到蛙蛙写作平台')
    parser.add_argument('--book', required=True, help='导出的txt文件路径')
    parser.add_argument('--headless', action='store_true', help='无头模式')
    parser.add_argument('--dry-run', action='store_true', help='试运行')
    args = parser.parse_args()

    if not os.path.exists(args.book):
        print(f"文件不存在: {args.book}", flush=True); sys.exit(1)

    try:
        success = submit_to_wawawriter(args.book, args.headless, args.dry_run)
        if not success: sys.exit(1)
    except Exception as e:
        print(f"投稿失败: {e}", flush=True); sys.exit(1)


if __name__ == '__main__':
    main()
