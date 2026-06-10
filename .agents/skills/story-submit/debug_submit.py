"""Debug: upload file then inspect preview dialog buttons"""
import time, subprocess, socket
from playwright.sync_api import sync_playwright

QUARK_EXE = r'C:\Users\裴浩然\AppData\Local\Programs\Quark\quark.exe'
QUARK_USER_DATA = r'C:\Users\裴浩然\AppData\Local\Quark\User Data'
CDP_PORT = 9222

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0

if not is_port_open(CDP_PORT):
    subprocess.Popen([QUARK_EXE, f'--remote-debugging-port={CDP_PORT}',
                      f'--user-data-dir={QUARK_USER_DATA}', '--no-sandbox',
                      'https://wawawriter.com/app/submission/create'])
    for i in range(30):
        time.sleep(1)
        if is_port_open(CDP_PORT): break

time.sleep(5)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(f'http://127.0.0.1:{CDP_PORT}')
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto('https://wawawriter.com/app/submission/create', timeout=30000)
    time.sleep(5)

    tx = "C:/Users/裴浩然/Desktop/AI网文项目/oh-novel-writer/projects/散打饼干/漂亮美人在年代文被偏执疯狗缠上/rewrites/穿书七零偏执疯狗的娇气包/export/穿书七零被偏执狂盯上了.txt"
    
    print(">> 上传文件...", flush=True)
    try:
        page.locator('input[type="file"]').first.set_input_files(tx)
        print(">> set_input_files ok", flush=True)
    except Exception as e:
        print(f">> set_input_files failed: {e}", flush=True)
    
    # 等待预览弹窗出现
    for i in range(30):
        time.sleep(2)
        btns = page.eval_on_selector_all('button', 'els => els.map(el => el.innerText.trim())')
        vis_btns = [b for b in btns if b]
        print(f"  t={i*2+2}s buttons={vis_btns}", flush=True)
        if '下一步' in vis_btns or 'next' in str(vis_btns).lower():
            print(">> 找到下一步按钮!", flush=True)
            break
    
    time.sleep(30)
