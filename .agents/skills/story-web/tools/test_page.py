from playwright.sync_api import sync_playwright
import sys
sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://fanqienovel.com/rank/0_1_1139', timeout=30000)
    page.wait_for_timeout(3000)
    items = page.query_selector_all('a[href*="/page/"]')
    if items:
        text = items[0].inner_text()
        print('First book card text:')
        print(text[:500])
    browser.close()
