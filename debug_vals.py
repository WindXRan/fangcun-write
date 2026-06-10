from playwright.sync_api import sync_playwright

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
for ctx in browser.contexts:
    for pg in ctx.pages:
        if 'wawawriter' in pg.url and 'submission/create' in pg.url:
            pg.set_viewport_size({"width": 1280, "height": 900})
            
            # 检查标签状态
            result = pg.evaluate("""() => {
                let r = [];
                document.querySelectorAll('div, span').forEach(el => {
                    let text = (el.innerText || '').trim();
                    if ((text === '言情' || text === 'HE') && el.children.length === 0) {
                        let bg = window.getComputedStyle(el).backgroundColor;
                        let cls = el.className;
                        r.push({text, bg, cls: cls.substring(0, 80)});
                    }
                });
                return r;
            }""")
            for r in result:
                print(f"{r['text']} | bg={r['bg']} | cls={r['cls']}", flush=True)
            
            # 检查已选中的标签（el-tag元素）
            tags = pg.evaluate("""() => {
                let r = [];
                document.querySelectorAll('.el-tag').forEach(t => {
                    r.push(t.innerText.trim());
                });
                return r;
            }""")
            print(f"el-tags: {tags}", flush=True)
            
            break
p.stop()
