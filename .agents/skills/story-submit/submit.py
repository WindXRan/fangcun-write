"""
story-submit: 自动投稿到蛙蛙写作平台
用playwright操作Element Plus表单。
"""
import os, re, sys, time, argparse, subprocess, socket
from pathlib import Path

DEFAULT_PEN_NAME = "一盏清酒"
QUARK_EXE = r"C:\Users\Administrator\AppData\Local\Programs\Quark\quark.exe"
QUARK_USER_DATA = r"C:\Users\Administrator\AppData\Local\Quark\User Data"
CDP_PORT = 9222


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
    """选择Element Plus下拉框选项 - 用mouse.click直接点击坐标"""
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
    
    # 获取select触发器的坐标
    rect = page.evaluate("""(ph) => {
        for (let el of document.querySelectorAll('.el-select')) {
            let inp = el.querySelector('input');
            if (inp && inp.placeholder && inp.placeholder.includes(ph)) {
                let r = el.getBoundingClientRect();
                return {x: r.x + r.width/2, y: r.y + r.height/2, w: r.width, h: r.height};
            }
        }
        return null;
    }""", placeholder_text)
    
    if not rect or rect['w'] == 0:
        # 备用：用JS直接设值
        page.evaluate("""([ph, val]) => {
            for (let el of document.querySelectorAll('.el-select')) {
                let inp = el.querySelector('input');
                if (inp && inp.placeholder && inp.placeholder.includes(ph)) {
                    // 找到对应的dropdown并设值
                    let items = document.querySelectorAll('.el-select-dropdown__item');
                    for (let item of items) {
                        if (item.innerText.trim() === val) {
                            item.click();
                            return true;
                        }
                    }
                }
            }
            return false;
        }""", [placeholder_text, option_text])
        time.sleep(0.5)
        return
    
    # 用mouse.click点击触发器
    page.mouse.click(rect['x'], rect['y'])
    time.sleep(1.5)
    
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
    
    if option_rect:
        page.mouse.click(option_rect['x'], option_rect['y'])
        time.sleep(0.5)
    else:
        # 备用：强制显示dropdown再点击
        page.evaluate("""() => {
            document.querySelectorAll('.el-popper, .el-select-dropdown, .el-select__popper').forEach(el => {
                el.style.display = 'block';
                el.style.visibility = 'visible';
                el.style.opacity = '1';
                el.style.position = 'fixed';
                el.style.top = '200px';
                el.style.left = '400px';
                el.style.zIndex = '99999';
                el.style.width = '200px';
                el.style.background = '#fff';
                el.style.border = '1px solid #ccc';
                el.style.pointerEvents = 'auto';
            });
            document.querySelectorAll('.el-select-dropdown__item').forEach(el => {
                el.style.display = 'block';
                el.style.padding = '8px 12px';
                el.style.cursor = 'pointer';
            });
        }""")
        time.sleep(0.5)
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


def select_cascader_option(page, options):
    """选择Element Plus级联选择器"""
    # 强制显示cascader面板
    page.evaluate("""() => {
        document.querySelectorAll('.el-cascader-panel, .el-cascader-menu, .el-popper').forEach(el => {
            el.style.display = 'block';
            el.style.visibility = 'visible';
            el.style.opacity = '1';
            el.style.width = '200px';
            el.style.height = 'auto';
            el.style.minHeight = '100px';
            el.style.position = 'fixed';
            el.style.top = '300px';
            el.style.left = '400px';
            el.style.zIndex = '99999';
            el.style.background = '#fff';
            el.style.border = '1px solid #ccc';
            el.style.pointerEvents = 'auto';
        });
        document.querySelectorAll('.el-cascader-node__label, .el-cascader-menu__item').forEach(el => {
            el.style.display = 'block';
            el.style.padding = '8px 12px';
            el.style.cursor = 'pointer';
        });
    }""")
    time.sleep(0.5)
    # 逐级选择
    for opt in options:
        page.evaluate("""(text) => {
            for (let el of document.querySelectorAll('.el-cascader-node__label, .el-cascader-menu__item')) {
                if (el.innerText.trim() === text) {
                    el.click();
                    return true;
                }
            }
            return false;
        }""", opt)
        time.sleep(1)


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

        page = None
        for ctx in browser.contexts:
            for pg in ctx.pages:
                if "wawawriter" in pg.url:
                    page = pg
        if not page:
            page = browser.contexts[0].new_page()

        # 设置viewport
        page.set_viewport_size({"width": 1280, "height": 900})
        time.sleep(1)

        print("打开投稿页...", flush=True)
        try: page.goto("https://wawawriter.com/app/submission/create", timeout=30000)
        except: pass
        time.sleep(8)
        print(f"URL={page.url}", flush=True)

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

        print("[1] 上传文件...", flush=True)
        try:
            page.locator('input[type="file"]').first.set_input_files(txt_abs)
            print("[OK] 已上传", flush=True)
            time.sleep(8)
        except Exception as e:
            print(f"[X] 上传失败: {e}", flush=True)

        print("[2] 关闭预览弹窗...", flush=True)
        page.locator('button').filter(has_text='下一步').first.click(force=True, timeout=10000)
        time.sleep(3)
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
        print("[跳过] 请手动选择频道（女频）", flush=True)

        print("[7] 作品状态...", flush=True)
        print("[跳过] 请手动选择状态（连载中）", flush=True)

        print("[8] 小说类目...", flush=True)
        try:
            select_cascader_option(page, ['现代', '言情'])
            print("[OK]", flush=True)
        except:
            print("[跳过] 请手动选择类目", flush=True)

        print("[9] 标签...", flush=True)
        print("[跳过] 请手动选择标签", flush=True)

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
