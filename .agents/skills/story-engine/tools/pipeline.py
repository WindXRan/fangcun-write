"""Pipeline 编排器：整合所有 phase 模块，提供统一的执行入口。"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

# 添加路径
current_dir = str(Path(__file__).parent)
sys.path.insert(0, current_dir)

from state_manager import StateManager
from utils import validate_config, get_chapters_list
from phases import (
    phase_prep, phase_open_book, phase_style_analysis,
    phase_guides, phase_guide_continuity_fix,
    phase_write, phase_validate, validate_one,
    phase_postfix, phase_trim, phase_rewrite, phase_polish, phase_expand,
    phase_compare, phase_review, phase_fix,
    phase_unified_check, phase_unified_fix, phase_unified_review_fix
)


def _genre_skeleton(base_name, genre):
    """品类 prompt 骨架模板。"""
    templates = {
        "write-chapter": f"""# {genre} 品类特化 — 补充覆盖 write-chapter.md

## 🔴 品类规则

在此添加 {genre} 特有的自检项。每条规则必须可验证（打勾 or 不过关）。

- [ ] 规则1：示例
- [ ] 规则2：示例

## 常见偏差

- ❌ 错误写法示例
- ✅ 正确写法示例
""",
        "plot-guide": f"""# {genre} 品类特化 — 补充覆盖 plot-guide.md

## 品类核心规则

- 规则1
- 规则2

## 冲突组合偏好

- 冲突类型优先级
""",
        "style-guide": f"""# {genre} 品类特化 — 补充覆盖 style-guide.md

## 品类特有风格维度

在此添加 {genre} 品类特有的风格定量指标。

## 句式规则补充

- ✅ 正例
- ❌ 反例
""",
        "open-book": f"""# {genre} 品类特化 — 补充覆盖 open-book.md

## 赛道设计约束

- 题材锁定项
- 对标维度表

## 设定层一致性

- {genre} 品类特有的设定一致性要求
""",
    }
    return templates.get(base_name, f"# {genre} 品类特化规则\n")


def open_reader(config):
    """自动启动书库阅读器（story-web），防 404 防重复弹窗。"""
    import webbrowser
    import subprocess
    import urllib.request
    import atexit
    from urllib.error import URLError

    rewrites_dir = config.get("rewrites_dir", "")
    if not rewrites_dir:
        return

    # ── 基于当前脚本目录的绝对路径 ──
    script_dir = Path(__file__).resolve().parent.parent  # .agents/skills/story-engine/
    project_root = script_dir.parent.parent.parent        # 项目根目录
    web_dir = project_root / ".agents" / "skills" / "story-web"
    web_app = web_dir / "app.py"
    if not web_app.exists():
        print(f"[WARN] story-web 不存在: {web_app}")
        return

    web_port = 5000
    base_url = f"http://localhost:{web_port}"
    
    # ── 确保书库索引包含此书 ──
    _ensure_book_in_library(rewrites_dir, project_root)

    # ── 尝试从 rewrites_dir 推断书库索引，打开到对应书 ──
    target_url = derive_book_url(rewrites_dir, base_url, project_root) or f"{base_url}/"

    # ── 防重复标记文件 ──
    flag_file = Path(rewrites_dir) / "._browser_opened"

    # ── 端口冲突检测 ──
    port_in_use = False
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port_in_use = (s.connect_ex(('127.0.0.1', web_port)) == 0)
        s.close()
    except Exception:
        pass

    # ── 检查 web 服务器是否已运行（请求验证，比端口检测更可靠） ──
    web_running = False
    try:
        urllib.request.urlopen(f"{base_url}/", timeout=2)
        web_running = True
    except (URLError, Exception):
        pass

    if not web_running:
        if port_in_use:
            print(f"[WARN] 端口 {web_port} 已被占用（非 story-web 服务），请手动打开: {target_url}")
            return

        print("启动书库服务...")
        try:
            proc = subprocess.Popen(
                [sys.executable or "python", str(web_app)],
                cwd=str(web_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            # 注册退出清理
            _web_procs.append(proc)
            atexit.register(_cleanup_web_procs)

            # 轮询等待服务启动，最长 10 秒
            for _ in range(20):
                time.sleep(0.5)
                try:
                    urllib.request.urlopen(f"{base_url}/", timeout=1)
                    web_running = True
                    break
                except (URLError, Exception):
                    continue
            if not web_running:
                print("[WARN] 书库服务启动超时（10s），请手动刷新")
                return
        except Exception as e:
            print(f"[WARN] 启动书库服务失败: {e}")
            return

    # ── 防重复弹窗 ──
    # 首次（无 flag）：弹窗 + 写 flag
    # 重复（有 flag + 服务运行）：跳过
    # 服务重启过（有 flag + 无服务）：删 flag，下次弹窗
    if flag_file.exists():
        if web_running:
            print(f"书库已打开: {target_url}")
            return
        flag_file.unlink(missing_ok=True)

    print(f"书库地址: {target_url}")
    webbrowser.open(target_url)
    try:
        flag_file.write_text(str(os.getpid()))
    except Exception:
        pass


# ── 子进程生命周期管理 ──
_web_procs: list = []

def _cleanup_web_procs():
    """退出时清理后台 web 子进程"""
    for proc in _web_procs:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


def _ensure_book_in_library(rewrites_dir: str, project_root: Path):
    """如果书库索引中没有当前书，自动刷新索引。"""
    lib_file = project_root / ".agents" / "skills" / "story-web" / "data" / "book_library.json"
    if not lib_file.exists():
        return
    try:
        library = json.loads(lib_file.read_text(encoding="utf-8"))
        books = library.get("books", [])
        p = Path(rewrites_dir)
        # 检查是否已在库中
        for book in books:
            author = book.get("author", "")
            title = book.get("title", "")
            if author and title and author in str(p) and title in str(p):
                return  # 已在库中
        # 不在库中，刷新索引
        sys.path.insert(0, str(project_root / ".agents" / "skills" / "story-web" / "tools"))
        try:
            from book_library import scan_library, save_library_index
            books = scan_library(str(project_root / "projects"))
            save_library_index(books, str(lib_file))
        except ImportError:
            pass
    except Exception:
        pass


def derive_book_url(rewrites_dir: str, base_url: str, project_root: Path | None = None) -> str | None:
    """从 rewrites_dir 反推书库 book_idx，返回直接跳转 URL。"""
    try:
        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
        lib_file = project_root / ".agents" / "skills" / "story-web" / "data" / "book_library.json"
        if not lib_file.exists():
            return None
        library = json.loads(lib_file.read_text(encoding="utf-8"))
        books = library.get("books", [])
        parts = Path(rewrites_dir).parts
        # rewrites_dir 结构: projects/{author}/{book_title}/rewrites/{rewrite_name}
        if len(parts) >= 4:
            # 取最后5部分匹配 projects/author/title
            p = Path(rewrites_dir)
            for idx, book in enumerate(books):
                author = book.get("author", "")
                title = book.get("title", "")
                if author and title and author in str(p) and title in str(p):
                    return f"{base_url}/book/{idx}"
        return None
    except Exception:
        return None


def all_with_fix(config, start, end, workers=10, max_rounds=3, state_mgr=None):
    """一键完成：生成→统一审查→统一修复→输出报告。

    Args:
        config: 配置
        start: 起始章
        end: 结束章
        workers: 并行数
        max_rounds: 最大修复轮数
        state_mgr: StateManager 实例
    """
    print(f"\n{'=' * 60}")
    print(f"一键完成流程 (ch{start}-{end}, 最多{max_rounds}轮修复)")
    print("=" * 60)

    start_time = time.time()

    # ============ 第1步：生成章节 ============
    print(f"\n{'=' * 50}")
    print(f"第1步：生成章节")
    print("=" * 50)

    phase_guides(config, start, end, workers, state_mgr=state_mgr)

    write_batch = config.get("batch_size", {}).get("write", 10)
    for batch_start in range(start, end + 1, write_batch):
        batch_end = min(batch_start + write_batch - 1, end)
        phase_write(config, batch_start, batch_end, workers, state_mgr=state_mgr)
        phase_postfix(config, batch_start, batch_end)

    # ============ 第2步：统一审查+修复 ============
    report = phase_unified_review_fix(config, start, end, workers=workers, state_mgr=state_mgr)

    # ============ 第3步：生成报告 ============
    print(f"\n{'=' * 50}")
    print(f"第3步：生成完本报告")
    print("=" * 50)

    summary = report.get("summary", {}) if report else {}
    final_pass = summary.get("pass", 0)
    final_fail = summary.get("fail", 0)

    all_rounds = []
    if report:
        all_rounds.append({
            "round": 1,
            "pass": final_pass,
            "fail": final_fail,
            "avg_score": summary.get("avg_score", 0),
            "total_issues": summary.get("total_issues", 0),
        })

    generate_completion_report(config, start, end, all_rounds, final_pass, final_fail, start_time)

    # 导出TXT
    print("\n导出完整TXT...")
    try:
        from merge_chapters import merge_chapters
        chapters_dir = f"{config['rewrites_dir']}/chapters"
        export_dir = f"{config['rewrites_dir']}/export"
        export_file = f"{export_dir}/{config['book_name']}.txt"
        concept_path = f"{config['rewrites_dir']}/concept.md"
        os.makedirs(export_dir, exist_ok=True)
        if merge_chapters(chapters_dir, export_file, 'utf-8', concept_path):
            print(f"[OK] 已导出: {export_file}")
    except Exception as e:
        print(f"[WARN] 导出失败: {e}")

    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"一键完成！")
    print("=" * 60)
    print(f"总章节：{end - start + 1}章")
    total = final_pass + final_fail
    if total > 0:
        print(f"最终通过率：{final_pass}/{total} ({final_pass/total*100:.1f}%)")
    print(f"平均分：{summary.get('avg_score', 0)}")
    print(f"总问题数：{summary.get('total_issues', 0)}")
    print(f"总耗时：{total_time:.0f}秒")
    print(f"\n报告位置：{config['rewrites_dir']}/完本报告.md")
    
    return report


def generate_completion_report(config, start, end, all_rounds, final_pass, final_fail, start_time):
    """生成完本报告。"""
    rewrites_dir = config['rewrites_dir']
    report_file = Path(rewrites_dir) / "完本报告.md"
    
    # 计算总字数
    chapters_dir = Path(rewrites_dir) / "chapters"
    total_chars = 0
    chapter_count = 0
    if chapters_dir.exists():
        for ch_file in sorted(chapters_dir.glob("ch_*.txt")):
            content = ch_file.read_text(encoding='utf-8')
            lines = content.strip().split('\n')
            if lines and lines[0].startswith('第'):
                content = '\n'.join(lines[1:])
            total_chars += len(content.replace('\n', '').replace(' ', ''))
            chapter_count += 1
    
    # 生成报告
    report = f"""# 完本报告

## 项目信息

| 项目 | 内容 |
|------|------|
| 书名 | {config.get('book_name', '未知')} |
| 作者 | {config.get('author', '未知')} |
| 总章节 | {chapter_count}章 |
| 总字数 | {total_chars:,}字 |
| 平均每章 | {total_chars//chapter_count if chapter_count else 0:,}字 |

## 修复历史

| 轮次 | 通过 | 未通过 | 修复操作 |
|------|------|--------|----------|
"""
    
    for round_info in all_rounds:
        fixes = '、'.join(round_info.get('fixes', []))
        report += f"| 第{round_info['round']}轮 | {round_info['pass']}章 | {round_info['fail']}章 | {fixes} |\n"
    
    report += f"""
## 最终质量

| 指标 | 数值 |
|------|------|
| 通过章节 | {final_pass}章 |
| 未通过章节 | {final_fail}章 |
| 通过率 | {final_pass/(final_pass+final_fail)*100:.1f}% |

## 文件清单

```
{rewrites_dir}/
├── concept.md
├── guides/
│   ├── plot_*.md
│   └── style_*.md
├── chapters/
│   └── ch_*.txt
├── compare/
│   └── *.md
├── export/
│   └── {config.get('book_name', '书名')}.txt
└── 完本报告.md
```

## 后续建议

"""
    
    if final_fail > 0:
        report += f"""仍有{final_fail}章未通过验证，建议：
1. 手动检查未通过章节
2. 运行 `python tools/rewrite_chapters.py --config {config.get('config_file', 'configs/xxx.json')} --phase review --start {start} --end {end}` 进行审稿修复
"""
    else:
        report += """所有章节已通过验证！可以进行投稿。
"""
    
    report += f"""
---
*报告生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # 保存报告
    report_file.write_text(report, encoding='utf-8')
    print(f"报告已保存：{report_file}")
    
    return report


def main():
    parser = argparse.ArgumentParser(description="统一改写流水线")
    parser.add_argument("--config", required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=10)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--serial", action="store_true",
                        help="plot-guide 串行生成，保持章间连贯（质量模式）")
    parser.add_argument("--phase", default="all",
                        help="all | detect-genre | open-book | extract | guides | guide-fix | write | validate | trim | rewrite | polish | expand | compare | review | fix | unified | unified-check | unified-fix | full-review | health-check")
    parser.add_argument("--detect-genre", action="store_true",
                        help="开书前自动检测品类（覆盖已配置的 genre）")
    parser.add_argument("--include-fanwai", action="store_true",
                        help="包含番外章节（默认不包含）")
    parser.add_argument("--max-fix-rounds", type=int, default=3,
                        help="最大修复轮数（默认3轮）")
    parser.add_argument("--status", action="store_true",
                        help="显示当前项目状态后退出")
    parser.add_argument("--health-check", action="store_true",
                        help="运行健康检查后退出")
    parser.add_argument("--health-output", help="健康检查报告输出文件")

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.setdefault("prompts_dir", ".agents/skills/story-engine/prompts")
    config.setdefault("base_dir", os.getcwd())

    # 配置校验
    errors = validate_config(config)
    if errors:
        print("配置错误:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # 初始化状态管理
    rewrites_dir = config.get("rewrites_dir", "")
    state_mgr = StateManager(rewrites_dir) if rewrites_dir else None
    if state_mgr:
        state_mgr.load()
        print(f"[STATE] {state_mgr.summary()}")

    # --status: 显示状态后退出
    if args.status:
        if state_mgr:
            state_mgr.print_status()
        else:
            print("未初始化状态管理")
        return

    # --health-check: 运行健康检查后退出
    if args.health_check or "health-check" in args.phase.split(","):
        from health_check import run_health_check
        run_health_check(config, args.health_output)
        return

    # 如果没有指定 --end，则自动获取最大章节号（默认不包含番外）
    if not any('--end' in arg for arg in sys.argv):
        chapters = get_chapters_list(config, include_fanwai=args.include_fanwai)
        if chapters:
            args.end = max(chapters)
            print(f"自动检测到最大章节: 第{args.end}章")

    if args.workers is None:
        args.workers = args.end - args.start + 1
        print(f"workers 自动设为章节数: {args.workers}")

    print(f"改写流水线 | {config['book_name']} | ch{args.start}-{args.end} | workers={args.workers}")
    print(f"项目目录: {rewrites_dir}")

    t0 = time.time()
    phases = set(args.phase.split(","))

    # Phase 0: 品类自动检测（genre 为空时走 LLM 判定）
    should_detect = "all" in phases or "detect-genre" in phases or args.detect_genre
    if should_detect:
        if not config.get("genre") or args.detect_genre:
            from detect_genre import detect_genre
            api_key = config.get("api_key") or os.environ.get("API_KEY")
            genre = detect_genre(config, api_key)
            if genre:
                print(f"  [DETECT] 品类: {genre}")
                config["genre"] = genre
                # 写回 config.json
                config_data = json.loads(config_path.read_text(encoding='utf-8'))
                config_data["genre"] = genre
                config_path.write_text(
                    json.dumps(config_data, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                # 自动创建品类 prompt 骨架文件（如果不存在）
                prompts_dir = Path(config.get("prompts_dir", ".agents/skills/story-engine/prompts"))
                if not prompts_dir.is_absolute():
                    prompts_dir = Path(config.get("base_dir", os.getcwd())) / prompts_dir
                for base_name in ("write-chapter", "plot-guide", "style-guide", "open-book"):
                    genre_file = prompts_dir / f"{base_name}.{genre}.md"
                    if not genre_file.exists():
                        genre_file.write_text(
                            _genre_skeleton(base_name, genre),
                            encoding='utf-8'
                        )
                        print(f"  [SKELETON] 创建 {genre_file.name}")
            else:
                print("  [WARN] 品类检测未匹配，genre 留空（使用通用 prompt）")
        else:
            print(f"  [DETECT] 品类已配置: {config['genre']}（跳过检测）")

    if "all" in phases or "prep" in phases or "open-book" in phases:
        phase_prep(config)

    if "all" in phases or "open-book" in phases:
        phase_open_book(config, state_mgr=state_mgr)

    # open-book 后自动提取 book_data.json（为后续阶段提供结构化设定）
    if "all" in phases or "open-book" in phases or "extract" in phases:
        import importlib
        extract_mod = importlib.import_module("extract_book_data")
        bd_data = extract_mod.extract(config)
        if bd_data:
            cv = bd_data.get("meta", {}).get("character_variables", {})
            print(f"  [OK] book_data.json: {len(cv)} 变量"
                  f" (男主={cv.get('男主名','?')}, 女主={cv.get('女主名','?')})")
        else:
            print("  [FAIL] book_data.json 提取失败，角色变量将不可用")
            if "open-book" in phases:
                sys.exit(1)

    # Phase 1.5: 风格分析（脚本提取源文指标，缓存到 style_analysis/）
    if "all" in phases or "open-book" in phases or "style-analysis" in phases:
        phase_style_analysis(config, state_mgr=state_mgr)

    if "all" in phases or "guides" in phases:
        phase_guides(config, args.start, args.end, args.workers, serial=args.serial, state_mgr=state_mgr)

    # guide 衔接修复：在 guide 生成后、写章前，修复章间断裂
    if "guide-fix" in phases:
        phase_guide_continuity_fix(config, args.start, args.end, batch_size=40)

    if "all" in phases or "write" in phases:
        write_batch = config.get("batch_size", {}).get("write", 10)
        for batch_start in range(args.start, args.end + 1, write_batch):
            batch_end = min(batch_start + write_batch - 1, args.end)
            print(f"\n{'#' * 50}")
            print(f" 批次: 第{batch_start}-{batch_end}章")
            print(f"{'#' * 50}")

            phase_write(config, batch_start, batch_end, args.workers, state_mgr=state_mgr)
            phase_postfix(config, batch_start, batch_end)
            phase_compare(config, batch_start, batch_end)

        open_reader(config)

    if "all" in phases or "validate" in phases:
        phase_validate(config, args.start, args.end)

    if "all" in phases or "trim" in phases:
        phase_trim(config, args.start, args.end)

    if "rewrite" in phases:
        phase_rewrite(config, args.start, args.end, args.workers)

    if "polish" in phases:
        phase_polish(config, args.start, args.end, args.workers)

    if "expand" in phases:
        phase_expand(config, args.start, args.end, workers=args.workers)

    if "review" in phases:
        phase_review(config, args.start, args.end, args.workers)

    if "fix" in phases:
        phase_fix(config, args.start, args.end, args.workers)

    # 统一检查（只检查不修复）
    if "unified-check" in phases:
        phase_unified_check(config, args.start, args.end, workers=args.workers, state_mgr=state_mgr)

    # 统一修复（检查+修复一次搞定）
    if "unified-fix" in phases:
        phase_unified_fix(config, args.start, args.end, workers=args.workers)

    # 统一审查+修复（推荐，一次搞定）
    if "unified" in phases:
        phase_unified_review_fix(config, args.start, args.end, workers=args.workers, state_mgr=state_mgr)

    # 自动 Prompt 优化（审稿后自动运行，优化/精简/扩充 prompt）
    if "optimize" in phases:
        try:
            from auto_prompt_optimize import run_optimize
            run_optimize(config, args.start, args.end, mode="auto")
        except ImportError:
            print("[WARN] auto_prompt_optimize.py 未找到，跳过 prompt 优化")

    if "full-review" in phases:
        # 完整审改流程：审核→规划→执行→验证（委托 story-review）
        config_file = config.get("config_file")
        if not config_file:
            print("[FAIL] 未指定配置文件，请在配置中添加 config_file 字段")
        else:
            import subprocess as _sp
            cmd = [
                "python", ".agents/skills/story-review/tools/novel_review_rewrite.py",
                "--config", config_file,
                "--start", str(args.start),
                "--end", str(args.end),
                "--workers", str(args.workers)
            ]
            try:
                result = _sp.run(cmd, capture_output=False, text=True, encoding='utf-8', timeout=3600)
                if result.returncode == 0:
                    print("[OK] 完整审改流程完成")
                else:
                    print(f"[FAIL] 完整审改流程失败")
            except Exception as e:
                print(f"[FAIL] 完整审改流程失败: {e}")

    if "all" in phases or "compare" in phases:
        phase_compare(config, args.start, args.end)

    # all-with-fix：一键完成生成→验证→审稿→修复→重新验证→输出报告
    if "all-with-fix" in phases:
        all_with_fix(config, args.start, args.end, args.workers, args.max_fix_rounds, state_mgr=state_mgr)

    # 自动导出完整TXT
    if "all" in phases or "write" in phases:
        print(f"\n{'=' * 50}")
        print("自动导出完整TXT...")
        print("=" * 50)
        try:
            from merge_chapters import merge_chapters
            chapters_dir = f"{config['rewrites_dir']}/chapters"
            export_dir = f"{config['rewrites_dir']}/export"
            export_file = f"{export_dir}/{config['book_name']}.txt"
            concept_path = f"{config['rewrites_dir']}/concept.md"
            os.makedirs(export_dir, exist_ok=True)
            if merge_chapters(chapters_dir, export_file, 'utf-8', concept_path):
                print(f"[OK] 已导出: {export_file}")
            else:
                print(f"[WARN] 导出失败")
        except Exception as e:
            print(f"[WARN] 导出失败: {e}")

    # 生成最终汇报
    total_time = time.time() - t0
    rewrites_dir = config.get('rewrites_dir', '')
    
    print(f"\n{'=' * 50}")
    print(f"仿写完成！结果：")
    print("=" * 50)
    
    # 生成文件列表
    print(f"\n生成文件：")
    rewrites_path = Path(rewrites_dir)
    if rewrites_path.exists():
        print(f"- {rewrites_dir}/")
        
        # 检查各文件
        files_to_check = [
            ("concept.md", "设定+弧线"),
        ]
        for filename, desc in files_to_check:
            filepath = rewrites_path / filename
            if filepath.exists():
                print(f"  - {filename} - {desc}")
        
        # 检查guides目录
        guides_dir = rewrites_path / "guides"
        if guides_dir.exists():
            plot_files = list(guides_dir.glob("plot_*.md"))
            style_files = list(guides_dir.glob("style_*.md"))
            print(f"  - guides/ - {len(plot_files)}章plot+style指南")
        
        # 检查chapters目录
        chapters_dir = rewrites_path / "chapters"
        if chapters_dir.exists():
            chapter_files = sorted(chapters_dir.glob("ch_*.txt"))
            if chapter_files:
                print(f"  - chapters/ch_001.txt ~ ch_{len(chapter_files):03d}.txt - {len(chapter_files)}章正文")
        
        # 检查compare目录
        compare_dir = rewrites_path / "compare"
        if compare_dir.exists():
            print(f"  - compare/ - 对比报告")
            compare_files = list(compare_dir.glob("*"))
            for cf in compare_files:
                print(f"    - {cf.name}")
    
    # 统计信息
    print(f"\n统计：")
    # 计算总字数
    chapters_dir = rewrites_path / "chapters"
    if chapters_dir.exists():
        total_chars = 0
        for ch_file in chapters_dir.glob("ch_*.txt"):
            content = ch_file.read_text(encoding='utf-8')
            # 去除标题行和空白
            lines = content.strip().split('\n')
            if lines and lines[0].startswith('第'):
                content = '\n'.join(lines[1:])
            total_chars += len(content.replace('\n', '').replace(' ', ''))
        print(f"- 总字数：{total_chars:,}字")
    
    # 获取源文字数
    source_chars = config.get("source_chars", 0)
    if source_chars:
        print(f"- 源文字数：{source_chars:,}字")
    
    print(f"- 耗时：{total_time:.0f}秒")
    
    # 质量验证结果
    if "validate" in phases:
        print(f"\n质量验证：")
        # 这里可以添加验证结果的统计
    
    print(f"\n如需审稿修复，可运行：")
    print(f"python .agents/skills/story-engine/tools/rewrite_chapters.py --config {args.config} --phase review --start {args.start} --end {args.end}")


if __name__ == '__main__':
    main()
