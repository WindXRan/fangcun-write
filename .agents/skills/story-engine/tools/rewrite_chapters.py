"""
统一改写流水线：Agent/API 双模式兼容。

使用同一套 prompt 文件，prompt_loader 自动适配：
- Agent 模式：prompt 原样返回，Agent 用 Read 工具读文件
- API 模式：自动嵌入【标签】引用的文件内容

流水线（3 阶段）：
  1. 开书 (pro): open-book → concept.md（设定+弧线，含固定角色名）
  2. Guide (flash): plot-guide + style-guide → guides/plot_{N}.md + style_{N}.md
  3. 写章 (flash): write-chapter → chapters/ch_{N}.txt
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))
from prompt_loader import load_prompt

# 默认API配置，可通过环境变量或配置文件覆盖
DEFAULT_API_URL = "https://api.deepseek.com/chat/completions"
SYSTEM_PROMPT = "你是一个专业的网文写手，擅长仿写风格迁移。严格按照提供的指南和指令执行。"


def get_api_url(config=None):
    """获取API URL，优先级：配置文件 > 环境变量 > 默认值。"""
    if config and config.get("api_base_url"):
        return config["api_base_url"].rstrip("/") + "/chat/completions"
    env_url = os.environ.get("API_BASE_URL")
    if env_url:
        return env_url.rstrip("/") + "/chat/completions"
    return DEFAULT_API_URL


def call_api(api_key, model, user_prompt, reasoning_effort="low", max_tokens=8192, system_prompt=None, api_url=None):
    """调用 API。"""
    url = api_url or DEFAULT_API_URL
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.8,
        "max_tokens": max_tokens,
        "stream": False
    }
    resp = requests.post(url, headers=headers, json=data, timeout=600)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def load_style_profile(config):
    """加载全局风格画像（如果存在）。"""
    profile_path = Path(config["rewrites_dir"]) / "style-profile.md"
    if profile_path.exists():
        return profile_path.read_text(encoding='utf-8')
    return None


def count_source_chars(config, chapter_num):
    """统计源文章节的中文字数（去空白）。"""
    import re
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    base_dir = config.get("base_dir", os.getcwd())

    patterns = [
        f"projects/{author}/{source_book}/_cache/chapters/第{chapter_num}章*.txt",
        f"novel-download-authors/{author}/{source_book}/源文/第{chapter_num}章*.txt",
    ]
    import glob as g
    for pat in patterns:
        for f in sorted(g.glob(os.path.join(base_dir, pat))):
            text = Path(f).read_text(encoding='utf-8')
            lines = text.strip().split('\n')
            if lines and lines[0].startswith('第'):
                text = '\n'.join(lines[1:])
            return len(re.sub(r'\s', '', text))
    return 0


def run_one(config, prompt_type, chapter_num=None, model=None, reasoning_effort=None, system_prompt=None, extra_replacements=None):
    """执行单次调用。通过 prompt_loader 加载并嵌入文件内容。"""
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY，请设置 $env:API_KEY")

    model = model or config.get("model", "deepseek-v4-flash")
    reasoning_effort = reasoning_effort or config.get("reasoning_effort", "low")
    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    base_dir = config.get("base_dir", os.getcwd())
    api_url = get_api_url(config)

    n = str(chapter_num) if chapter_num else "1"
    n_plus1 = str(chapter_num + 1) if chapter_num else "2"
    replacements = {
        "新书名": config["book_name"],
        "N": n,
        "N_plus1": n_plus1,
        "N03d": f"{chapter_num:03d}" if chapter_num else "001",
        "N03d_plus1": f"{chapter_num+1:03d}" if chapter_num else "002",
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
    }

    # 需要源文字数时，脚本计算（API 无法跑 PowerShell）
    if prompt_type in ("plot-guide", "style-guide", "write-chapter", "trim-chapter") and chapter_num:
        src_chars = count_source_chars(config, chapter_num)
        target_chars = src_chars  # 1:1对标源文字数
        replacements["源文字数"] = str(src_chars)
        replacements["目标字数"] = str(target_chars)
        replacements["目标字数_min"] = str(int(target_chars * 0.9))
        replacements["目标字数_max"] = str(int(target_chars * 1.1))
    
    # style-guide注入源文指标（用脚本提取）
    if prompt_type == "style-guide" and chapter_num:
        metrics = extract_source_metrics(config, chapter_num)
        if metrics:
            replacements["源文指标"] = metrics
        else:
            replacements["源文指标"] = "（提取失败，请手动统计）"

    max_tokens = 8192  # 不限制，靠重跑兜底

    # 合并额外替换变量（如串行模式的上一章摘要）
    if extra_replacements:
        replacements.update(extra_replacements)

    prompt_path = f"{prompts_dir}/{prompt_type}.md"
    user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api")

    # 写章时注入全局风格画像到 system prompt
    sys_prompt = system_prompt or SYSTEM_PROMPT
    if prompt_type == "write-chapter":
        profile = load_style_profile(config)
        if profile:
            sys_prompt = profile + "\n\n---\n\n" + sys_prompt

    label = f"ch{chapter_num or '?'} {prompt_type}"
    t_req = time.time()
    try:
        result = call_api(api_key, model, user_prompt, reasoning_effort, max_tokens, sys_prompt, api_url)
        elapsed = time.time() - t_req
        print(f"  [OK] {label} ({elapsed:.0f}s)")
        return result
    except Exception as e:
        elapsed = time.time() - t_req
        print(f"  [FAIL] {label} ({elapsed:.0f}s): {e}")
        raise


def save_file(dir_path, filename, content):
    """保存文件。"""
    os.makedirs(dir_path, exist_ok=True)
    path = Path(dir_path) / filename
    path.write_text(content, encoding='utf-8')
    return str(path)


def get_source_title(config, chapter_num):
    """从源文章节提取标题（如 第1章 穿、穿书了？）。"""
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    base_dir = config.get("base_dir", os.getcwd())

    # projects/{作者}/{书名}/_cache/chapters/第N章*.txt
    patterns = [
        f"projects/{author}/{source_book}/_cache/chapters/第{chapter_num}章*.txt",
        f"projects/{author}/{source_book}/_cache/chapters/第{chapter_num:03d}章*.txt",
        f"novel-download-authors/{author}/{source_book}/源文/第{chapter_num}章*.txt",
        f"novel-download-authors/{author}/{source_book}/第{chapter_num}章*.txt",
    ]

    import glob
    for pat in patterns:
        for f in sorted(glob.glob(os.path.join(base_dir, pat))):
            try:
                first_line = Path(f).read_text(encoding='utf-8').strip().split('\n')[0]
                if first_line.startswith(f"第{chapter_num}章") or first_line.startswith(f"第{chapter_num:03d}章"):
                    return first_line.strip()
            except:
                pass
            # fallback: from filename
            stem = Path(f).stem
            if stem.startswith(f"第{chapter_num}章"):
                return stem.strip()

    return f"第{chapter_num}章"


def prepend_title(content, title):
    """在章节内容前加上标题行。"""
    lines = content.strip().split('\n')
    # 去掉 LLM 自己生成的标题（如 # 第一章）
    if lines and lines[0].startswith('#'):
        lines = lines[1:]
    if lines and lines[0].strip() == '':
        lines = lines[1:]
    return title + '\n\n' + '\n'.join(lines).strip()


# ============================================================
# Phase 0: Prep（提取元数据+章节目录）
# ============================================================

def phase_prep(config):
    """从原始 TXT 提取头部元数据和章节目录，供 open-book 使用。兼容 projects/ 下各种目录结构。"""
    import glob as g

    base_dir = config.get("base_dir", os.getcwd())
    author = config.get("author", "")
    source_book = config.get("source_book", "")

    cache_dir = Path(base_dir) / "projects" / author / source_book / "_cache"
    os.makedirs(cache_dir, exist_ok=True)

    # 1. 提取原始 TXT 头部（书名/作者/简介/标签/等级体系）
    header_file = cache_dir / "_header.txt"
    if not header_file.exists():
        # 多路径搜索原始 TXT
        raw_paths = [
            Path(base_dir) / "projects" / f"{source_book}.txt",
            Path(base_dir) / "projects" / author / f"{source_book}.txt",
            Path(base_dir) / "projects" / author / source_book / f"{source_book}.txt",
            Path(base_dir) / "novel-download-authors" / author / f"{source_book}.txt",
            Path(base_dir) / f"{source_book}.txt",
        ]
        raw_txt = None
        for p in raw_paths:
            if p.exists():
                raw_txt = p
                break

        if raw_txt:
            with open(raw_txt, encoding='utf-8') as f:
                head_lines = []
                for i, line in enumerate(f):
                    if i >= 80:
                        break
                    stripped = line.strip()
                    # 多种章节标题模式：第1章 / 第一章 / 第001章 / Chapter 1
                    if stripped and (
                        (stripped.startswith('第') and '章' in stripped[:15]) or
                        stripped.lower().startswith('chapter')
                    ):
                        break
                    head_lines.append(line)
            header_file.write_text(''.join(head_lines), encoding='utf-8')
            print(f"[OK] _header.txt ({len(head_lines)}行) -> {raw_txt}")
        else:
            print(f"[WARN] 未找到原始 TXT，_header.txt 跳过")

    # 2. 生成章节目录（从已拆分的章节）
    toc_file = cache_dir / "_toc.txt"
    if not toc_file.exists():
        # 多路径搜索拆分章节
        chapters_dirs = [
            cache_dir / "chapters",
            Path(base_dir) / "projects" / author / source_book / "源文",
            Path(base_dir) / "novel-download-authors" / author / source_book / "源文",
        ]
        chapter_files = []
        for d in chapters_dirs:
            if d.exists():
                import re as re_toc
                cf = sorted(
                    d.glob("第*章*.txt"),
                    key=lambda f: int(re_toc.search(r'第(\d+)章', f.stem).group(1)) if re_toc.search(r'第(\d+)章', f.stem) else 0
                )
                if cf:
                    chapter_files = cf
                    break

        if chapter_files:
            toc_lines = [f"总章数: {len(chapter_files)}\n\n"]
            for cf in chapter_files:
                toc_lines.append(cf.stem)
            toc_file.write_text('\n'.join(toc_lines), encoding='utf-8')
            print(f"[OK] _toc.txt ({len(chapter_files)}章)")
        else:
            print(f"[WARN] 未找到拆分章节，_toc.txt 跳过")


# ============================================================
# Phase 1: 开书
# ============================================================

def phase_open_book(config):
    """生成 concept.md（设定 + 弧线，含固定角色名）。"""
    print("\n" + "=" * 50)
    print("Phase 1: 开书 (pro, reasoning=high)")
    print("=" * 50)

    pro = {**config, "model": "deepseek-v4-pro", "reasoning_effort": "high"}
    try:
        concept = run_one(pro, "open-book")
        path = save_file(config["rewrites_dir"], "concept.md", concept)
        print(f"[OK] concept.md → {path}")
        return True
    except Exception as e:
        print(f"[FAIL] concept.md: {e}")
        return False


# ============================================================
# Phase 1.5: 全局风格画像
# ============================================================

def phase_style_profile(config):
    """生成全局风格画像（跑一次，全章共用）。"""
    profile_path = Path(config["rewrites_dir"]) / "style-profile.md"
    if profile_path.exists():
        print(f"style-profile.md 已存在，跳过")
        return True

    print("\n" + "=" * 50)
    print("Phase 1.5: 全局风格画像 (pro)")
    print("=" * 50)

    pro = {**config, "model": "deepseek-v4-pro", "reasoning_effort": "high"}
    try:
        profile = run_one(pro, "style-profile")
        save_file(config["rewrites_dir"], "style-profile.md", profile)
        print(f"[OK] style-profile.md 生成成功")
        return True
    except Exception as e:
        print(f"[FAIL] style-profile: {e}")
        return False


# ============================================================
# Phase 2: Guide 生成
# ============================================================

def extract_source_metrics(config, ch):
    """用脚本提取源文风格指标"""
    import subprocess
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    base_dir = config.get("base_dir", os.getcwd())
    
    # 查找源文文件
    patterns = [
        f"projects/{author}/{source_book}/_cache/chapters/第{ch}章*.txt",
        f"projects/{author}/{source_book}/_cache/chapters/第{ch:03d}章*.txt",
        f"novel-download-authors/{author}/{source_book}/源文/第{ch}章*.txt",
    ]
    
    import glob
    source_file = None
    for pat in patterns:
        for f in sorted(glob.glob(os.path.join(base_dir, pat))):
            source_file = f
            break
        if source_file:
            break
    
    if not source_file:
        return None
    
    # 运行提取脚本
    script_path = Path(__file__).parent / "extract_style.py"
    try:
        result = subprocess.run(
            ["python", str(script_path), source_file],
            capture_output=True, timeout=30
        )
        if result.returncode == 0 and result.stdout:
            # 手动解码bytes为字符串
            output = result.stdout.decode('utf-8', errors='ignore')
            return output.strip()
    except Exception as e:
        print(f"  [WARN] 提取源文指标失败: {e}")
    
    return None


def phase_guides(config, start, end, workers=5, serial=False):
    """生成 plot_guide + style_guide。serial=True 时 plot-guide 串行以保持章间连贯。"""
    guides_dir = f"{config['rewrites_dir']}/guides"
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    # style-guide 始终并行（章间独立）
    print(f"\n{'=' * 50}")
    print(f"Phase 2: style_guide (flash, ch{start}-{end}, {'并行' if workers>1 else '串行'})")
    print("=" * 50)
    
    # 先用脚本提取源文指标，注入到replacements中
    for ch in range(start, end + 1):
        metrics = extract_source_metrics(config, ch)
        if metrics:
            print(f"  [OK] ch{ch} 源文指标提取完成")
    
    ok, fail = batch_run(flash, "style-guide", start, end, workers, guides_dir, "style_{ch}.md")
    print(f"style_guide: OK={len(ok)} FAIL={len(fail)}")

    # plot-guide
    print(f"\n{'=' * 50}")
    print(f"Phase 2: plot_guide (flash, ch{start}-{end}, {'串行(质量)' if serial else '并行(速度)'})")
    print("=" * 50)

    if serial:
        # 串行模式：每章带上章摘要，保持连贯
        prev_summary = ""
        ok, fail = {}, {}
        for ch in range(start, end + 1):
            try:
                overrides = {}
                if prev_summary:
                    overrides["上一章摘要"] = prev_summary
                result = run_one(flash, "plot-guide", ch, extra_replacements=overrides)
                path = save_file(guides_dir, f"plot_{ch}.md", result)
                ok[ch] = path
                # 提取摘要：优先取新书节拍
                import re as re_p
                beats = re_p.findall(r'新书[：:].*?(?=\n|$)', result)
                if not beats:
                    beats = re_p.findall(r'节拍\d+[：:].*?(?=\n|$)', result)
                prev_summary = '；'.join(beats[-3:]) if beats else result[-300:]
                print(f"  [OK] ch{ch} plot-guide")
            except Exception as e:
                fail[ch] = str(e)
                print(f"  [FAIL] ch{ch}: {e}")
    else:
        # 并行模式：独立生成，速度快
        ok, fail = batch_run(flash, "plot-guide", start, end, workers, guides_dir, "plot_{ch}.md")

    print(f"plot_guide: OK={len(ok)} FAIL={len(fail)}")


# ============================================================
# Phase 3: 写章
# ============================================================

def phase_write(config, start, end, workers=10):
    """并行写章 + 异常章自动重跑（字数触发）。"""
    import re as re2
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    print(f"\n{'=' * 50}")
    print(f"Phase 3: 写章 (flash, ch{start}-{end}, {workers}w)")
    print("=" * 50)

    t0 = time.time()

    # 第一轮
    ok, fail = batch_run(flash, "write-chapter", start, end, workers, chapters_dir, "ch_{ch:03d}.txt", skip_existing=True)

    # 重跑异常章（最多2轮）
    for retry_round in range(1, 3):
        retry_list = []
        for ch in range(start, end + 1):
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            if not ch_file.exists():
                continue
            text = ch_file.read_text(encoding='utf-8')
            
            # 检查：字数异常（按源文字数±30%）
            target = count_source_chars(config, ch)
            chars = len(re2.sub(r'\s', '', text.split('\n', 1)[1] if '\n' in text else text))
            if target > 0:
                deviation = abs(chars - target) / target
                if deviation > 0.3:  # 超过±30%
                    retry_list.append((ch, f"字数{chars}/{target}"))
            elif chars < 900 or chars > 3000:  # 无源文时用固定阈值
                retry_list.append((ch, f"字数{chars}"))

        if not retry_list:
            break

        print(f"  [RETRY R{retry_round}] {len(retry_list)}章异常: {[(c, w) for c,w in retry_list]}")
        for ch, _ in retry_list:
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            ch_file.unlink(missing_ok=True)

        ok2, fail2 = batch_run(flash, "write-chapter",
            min(c for c, _ in retry_list), max(c for c, _ in retry_list),
            workers, chapters_dir, "ch_{ch:03d}.txt", skip_existing=False)
        ok.update(ok2)
        fail.update(fail2)

    total = sum(
        len(Path(path).read_text(encoding='utf-8').replace('\n','').replace(' ','').replace('\r',''))
        for path in ok.values()
    )
    print(f"  完成: OK={len(ok)} FAIL={len(fail)} 总字数≈{total} | 耗时 {time.time()-t0:.0f}s")
    return ok, fail


# ============================================================
# 批量并行
# ============================================================

def batch_run(config, prompt_type, start, end, workers, output_dir, filename_fmt, skip_existing=False):
    """并行批量调用。"""
    results, errors = {}, {}
    todo = []
    for ch in range(start, end + 1):
        if skip_existing:
            filename = filename_fmt.format(ch=ch)
            filepath = Path(output_dir) / filename
            if filepath.exists():
                # 检查不是损坏文件（致歉内容等）
                text = filepath.read_text(encoding='utf-8')
                if '抱歉' not in text[:300] and '无法读取' not in text[:300] and len(text) > 500:
                    continue  # 跳过已有健康文件
        todo.append(ch)

    if not todo:
        print(f"  全部已存在，跳过")
        return results, errors

    print(f"  待处理: {len(todo)}章")
    done, total = 0, len(todo)
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_one, config, prompt_type, ch): ch for ch in todo}
        for future in as_completed(futures):
            ch = futures[future]
            try:
                content = future.result()
                filename = filename_fmt.format(ch=ch)
                path = save_file(output_dir, filename, content)
                results[ch] = path
            except Exception as e:
                errors[ch] = str(e)
            done += 1
            # 实时进度+ETA：每5%或最后一章打印
            if done % max(1, total // 20) == 0 or done == total:
                elapsed = time.time() - t_start
                speed = elapsed / done  # 秒/章
                eta = speed * (total - done)  # 剩余秒
                pct = done * 100 // total
                bar = '=' * (pct // 5) + '>' + ' ' * (20 - pct // 5)
                print(f"  [{done}/{total}] [{bar}] {pct}% | {elapsed:.0f}s | ETA {eta:.0f}s")
    return results, errors


# ============================================================
# Phase 3.1: Validate（后处理验证）
# ============================================================

def count_chapter_metrics(text):
    """统计章节的量化指标。"""
    import re
    body = text.strip()
    lines = body.split('\n')
    if lines and lines[0].startswith('第'):
        body = '\n'.join(lines[1:])

    clean = re.sub(r'\s', '', body)

    # 比喻检测：只匹配明确比喻结构 (像X一样/仿佛X/犹如X)
    metaphor_pattern = r'(?:就像|好像|像.{1,20}(?:一样|似的|般|一般)|仿佛.{1,20}(?:一样|似的|般|一般)?|犹如|恍如|宛如|好似)'

    return {
        "chars": len(clean),
        "dash": body.count('——'),
        "metaphor": len(re.findall(metaphor_pattern, body)),
        "ai_markers": len(re.findall(r'(?:首先|其次|然后|最后|与此同时|值得注意的是|此外|综上所述|总而言之)', body)),
        "direct_emotion": len(re.findall(r'(?:充满了|感到无比|心中涌起|不由得|不禁|忍不住)', body)),
    }


def get_source_text(config, ch):
    """读取源文章节原始文本。"""
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    base_dir = config.get("base_dir", os.getcwd())

    patterns = [
        f"projects/{author}/{source_book}/_cache/chapters/第{ch}章*.txt",
        f"novel-download-authors/{author}/{source_book}/源文/第{ch}章*.txt",
    ]
    import glob as g
    for pat in patterns:
        for f in sorted(g.glob(os.path.join(base_dir, pat))):
            return Path(f).read_text(encoding='utf-8')
    return None


def get_source_metrics(config, ch):
    """直接从源文章节计算锚点指标（不依赖 LLM 填写的 style_guide）。"""
    text = get_source_text(config, ch)
    if text:
        return count_chapter_metrics(text)
    return None


def validate_one(config, ch):
    """验证单章质量：源文指标 vs 仿写指标。返回 (pass: bool, report: str)。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"

    if not ch_file.exists():
        return False, f"ch{ch:03d}: 文件不存在"

    text = ch_file.read_text(encoding='utf-8')
    metrics = count_chapter_metrics(text)
    src = get_source_metrics(config, ch)
    src_text = get_source_text(config, ch)  # 用于台词抄袭检测

    issues = []
    warnings = []

    # 1. 字数检查（对标源文）
    target = count_source_chars(config, ch)
    if target > 0:
        deviation = (metrics["chars"] - target) / target
        if deviation > 0.15:
            issues.append(f"字数超标 {metrics['chars']}/{target} (+{deviation:.0%})")
        elif deviation < -0.15:
            issues.append(f"字数不足 {metrics['chars']}/{target} ({deviation:.0%})")
        elif abs(deviation) > 0.10:
            warnings.append(f"字数偏差 {metrics['chars']}/{target} ({deviation:+.0%})")

    # 2. 比喻句检查（不超过源文+3）
    if src:
        limit = src["metaphor"] + 3
        if metrics["metaphor"] > limit:
            issues.append(f"比喻过多 {metrics['metaphor']} (源文{src['metaphor']}, 上限{limit})")

    # 4. AI 路标词（源文水平+2以内）
    if src:
        limit = max(src["ai_markers"] + 1, 1)  # 收紧AI痕迹
        if metrics["ai_markers"] > limit:
            issues.append(f"AI路标词 {metrics['ai_markers']}处 (源文{src['ai_markers']}, 上限{limit})")

    # 5. 直抒情（源文水平+2以内）
    if src:
        limit = max(src["direct_emotion"] + 2, 3)
        if metrics["direct_emotion"] > limit:
            issues.append(f"直抒情 {metrics['direct_emotion']}处 (源文{src['direct_emotion']}, 上限{limit})")

    # 6. 台词抄袭检测（连续8字以上与源文重合）
    if src_text:
        # 分词：按标点切句
        def split_sentences(text):
            import re as re_s
            return [s.strip() for s in re_s.split(r'[。！？…\n]+', text) if len(s.strip()) >= 8]

        src_sents = split_sentences(src_text)
        imt_sents = split_sentences(text)
        plagiarisms = []
        for s in imt_sents:
            for ss in src_sents:
                if len(s) < 8 or len(ss) < 8:
                    continue
                # 滑动窗口找最长公共子串
                max_overlap = 0
                for i in range(len(s) - 7):
                    for j in range(i + 8, len(s) + 1):
                        if s[i:j] in ss:
                            max_overlap = max(max_overlap, j - i)
                if max_overlap >= 8:
                    plagiarisms.append((s[:40], ss[:40], max_overlap))
                    break  # 一句只记一次

        if plagiarisms:
            issues.append(f"台词雷同 {len(plagiarisms)}处（连续≥8字匹配）")
            for p in plagiarisms[:3]:  # 最多显示3处
                issues.append(f"  '{p[0]}...' ≈ '{p[1]}...' ({p[2]}字重合)")

    # 汇总
    all_ok = len(issues) == 0
    status = "[PASS]" if all_ok else "[FAIL]"
    report_parts = [f"ch{ch:03d} {status} | {metrics['chars']}字 | metaphor={metrics['metaphor']} | AI={metrics['ai_markers']} | direct_emo={metrics['direct_emotion']}"]
    if src:
        report_parts.append(f"  源文: {src['chars']}字 | metaphor={src['metaphor']} | AI={src['ai_markers']} | direct_emo={src['direct_emotion']}")
    for i in issues:
        report_parts.append(f"  *ISSUE* {i}")
    for w in warnings:
        report_parts.append(f"  *WARN* {w}")

    return all_ok, '\n'.join(report_parts)


def phase_validate(config, start, end):
    """验证章节质量，报告不达标指标。"""
    print(f"\n{'=' * 50}")
    print(f"Phase 3.1: 质量验证 (ch{start}-{end})")
    print("=" * 50)

    ok_count, fail_count = 0, 0
    for ch in range(start, end + 1):
        passed, report = validate_one(config, ch)
        print(report)
        if passed:
            ok_count += 1
        else:
            fail_count += 1

    if fail_count > 0:
        print(f"\n[WARN] {fail_count}章不达标，建议手动修改或重写。")
    else:
        print(f"\n[OK] 全部通过")

    return ok_count, fail_count


# ============================================================
# Phase 3.2: Post-Fix（机械后处理——不调LLM）
# ============================================================

def phase_postfix(config, start, end):
    """机械修复：段尾补省略号、去#号、砍超标字数。不调LLM。"""
    import re
    chapters_dir = f"{config['rewrites_dir']}/chapters"

    print(f"\n{'=' * 50}")
    print(f"Phase 3.2: 后处理 (ch{start}-{end})")
    print("=" * 50)

    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue

        text = ch_file.read_text(encoding='utf-8')
        lines = text.strip().split('\n')
        fixed = 0

        # 1. 去标题 # 号；过滤源文标题；删重复标题行
        if lines and lines[0].startswith('# '):
            lines[0] = lines[0][2:]
            fixed += 1
        src_title = get_source_title(config, ch)
        if src_title and lines and lines[0].strip() == src_title.strip():
            lines[0] = f"第{ch}章"  # 替换为通用标题
            fixed += 1
        # 删除紧跟标题后的重复标题行（如 line 0 和 line 2 都是"第N章"）
        if len(lines) >= 3 and lines[2].startswith('第') and '章' in lines[2][:10]:
            del lines[2]  # 删掉重复标题
            if len(lines) > 2 and lines[2].strip() == '':
                del lines[2]  # 顺便删空行
            fixed += 1

        if fixed > 0:
            ch_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            print(f"  ch{ch:03d}: {fixed}处修复")
        else:
            print(f"  ch{ch:03d}: 无需修复")

    return True


# ============================================================
# Phase 3.5: Post-Trim
# ============================================================

def phase_trim(config, start, end):
    """超字数章节自动精简（>20% 偏差触发）。"""
    import re
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    trimmed = 0
    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue

        text = ch_file.read_text(encoding='utf-8')
        lines = text.strip().split('\n')
        body = '\n'.join(lines[1:]) if lines and lines[0].startswith('第') else text
        chars = len(re.sub(r'\s', '', body))
        target = count_source_chars(config, ch)

        if target == 0:
            continue

        over = (chars - target) / target
        if over <= 0.2:
            continue  # 在 ±20% 内，跳过

        print(f"[TRIM] ch{ch:03d}: {chars}->{target} ({over:+.0%})")
        try:
            result = run_one(flash, "trim-chapter", ch)
            # 保留原标题
            title = lines[0] if lines and lines[0].startswith('第') else f"第{ch}章"
            ch_file.write_text(title + '\n\n' + result.strip(), encoding='utf-8')
            trimmed += 1
        except Exception as e:
            print(f"  [FAIL] trim ch{ch}: {e}")

    if trimmed:
        print(f"[OK] 精简了 {trimmed} 章")
    else:
        print(f"所有章节在 ±20% 内，无需精简")
    return trimmed


# ============================================================
# Phase 3.6: 跨章衔接修复
# ============================================================

def phase_continuity(config, start, end, workers=30):
    """修复相邻章节的衔接问题（并行）。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    print(f"\n{'=' * 50}")
    print(f"Phase 3.6: 跨章衔接修复 (ch{start}-{end})")
    print("=" * 50)

    fixed = 0
    # 只处理相邻对，从 start+1 开始（修下一章的开头）
    pairs = [(ch - 1, ch) for ch in range(start + 1, end + 1)]

    def fix_pair(prev_ch, curr_ch):
        prev_file = Path(chapters_dir) / f"ch_{prev_ch:03d}.txt"
        curr_file = Path(chapters_dir) / f"ch_{curr_ch:03d}.txt"
        if not prev_file.exists() or not curr_file.exists():
            return None

        try:
            import re as re_c
            result = run_one(flash, "continuity-fix", prev_ch)
            # 安全校验：输出不得短于源文50%
            target = count_source_chars(config, curr_ch)
            result_chars = len(re_c.sub(r'\s', '', result))
            if target > 0 and result_chars < target * 0.5:
                print(f"  [SKIP] ch{prev_ch}->ch{curr_ch}: 输出过短({result_chars}字), 保留原章")
                return None
            # 保留原标题
            orig_lines = curr_file.read_text(encoding='utf-8').strip().split('\n')
            title = orig_lines[0] if orig_lines and orig_lines[0].startswith('第') else f"第{curr_ch}章"
            curr_file.write_text(title + '\n\n' + result.strip(), encoding='utf-8')
            return curr_ch
        except Exception as e:
            print(f"  [FAIL] ch{prev_ch}->ch{curr_ch}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fix_pair, p, c): (p, c) for p, c in pairs}
        for future in as_completed(futures):
            r = future.result()
            if r:
                fixed += 1

    print(f"[OK] 修复了 {fixed} 处衔接")
    return fixed


# ============================================================
# Phase 4: 对比
# ============================================================

def phase_compare(config, start, end, batch_size=10):
    """生成仿写 vs 源文对比报告（分批处理）"""
    import subprocess

    rewrites_dir = config["rewrites_dir"]
    compare_script = ".agents/skills/story-compare/compare.py"

    print(f"\n{'=' * 50}")
    print(f"Phase 4: 对比 (ch{start}-{end}, 每{batch_size}章一批)")
    print("=" * 50)

    # 分批处理
    for batch_start in range(start, end + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end)
        print(f"\n  对比第{batch_start}-{batch_end}章...")
        
        cmd = ["python", compare_script, rewrites_dir, str(batch_start), str(batch_end)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=120)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            compare_dir = f"{rewrites_dir}/compare"
            print(f"  [OK] 对比_{batch_start}-{batch_end}_报告.md")
            print(f"  [OK] 对比_{batch_start}-{batch_end}_AI分析.md")
        except Exception as e:
            print(f"  [FAIL] 第{batch_start}-{batch_end}章对比失败: {e}")

    print(f"\n对比报告 → {rewrites_dir}/compare/")


def open_reader(config):
    """自动启动阅读器"""
    import webbrowser
    import subprocess
    
    rewrites_dir = config.get("rewrites_dir", "")
    if not rewrites_dir:
        return
    
    # 查找 compare_server.py
    server_paths = [
        "tools/compare_server.py",
        ".agents/skills/story-engine/tools/compare_server.py",
    ]
    
    server_script = None
    for path in server_paths:
        if Path(path).exists():
            server_script = path
            break
    
    if not server_script:
        print(f"[WARN] 未找到 compare_server.py，跳过自动打开")
        return
    
    # 启动服务器
    print(f"\n启动阅读器服务器...")
    try:
        # 后台启动服务器
        proc = subprocess.Popen(
            ["python", server_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        # 等待服务器启动
        import time
        time.sleep(2)
        
        # 打开浏览器
        url = "http://localhost:8900"
        print(f"阅读器地址: {url}")
        webbrowser.open(url)
        
        # 不阻塞主进程
        print(f"服务器已在后台运行 (PID: {proc.pid})")
        print(f"按 Ctrl+C 不会停止服务器，需要手动关闭")
        
    except Exception as e:
        print(f"[WARN] 启动阅读器失败: {e}")


# ============================================================
# 主入口
# ============================================================

def get_chapters_list(config, include_fanwai=False):
    """获取章节目录中的章节列表"""
    import glob
    import re
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    base_dir = config.get("base_dir", os.getcwd())
    
    # 查找章节目录
    patterns = [
        f"projects/{author}/{source_book}/_cache/chapters/",
        f"novel-download-authors/{author}/{source_book}/源文/",
    ]
    
    chapters_dir = None
    for pat in patterns:
        full_path = os.path.join(base_dir, pat)
        if os.path.isdir(full_path):
            chapters_dir = full_path
            break
    
    if not chapters_dir:
        return []
    
    # 获取章节列表
    chapters = []
    for f in os.listdir(chapters_dir):
        if not f.endswith('.txt'):
            continue
        if not include_fanwai and '番外' in f:
            continue
        m = re.search(r'(\d+)', f)
        if m:
            chapters.append(int(m.group(1)))
    
    chapters.sort()
    return chapters


def main():
    parser = argparse.ArgumentParser(description="统一改写流水线")
    parser.add_argument("--config", required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=10)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--serial", action="store_true",
                        help="plot-guide 串行生成，保持章间连贯（质量模式）")
    parser.add_argument("--phase", default="all",
                        help="all | open-book | style-profile | guides | write | validate | trim | compare（外加: continuity）")
    parser.add_argument("--include-fanwai", action="store_true",
                        help="包含番外章节（默认不包含）")

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.setdefault("prompts_dir", ".agents/skills/story-engine/prompts")
    config.setdefault("base_dir", os.getcwd())

    # 如果没有指定 --end，则自动获取最大章节号（默认不包含番外）
    if args.end == 10:  # 默认值
        chapters = get_chapters_list(config, include_fanwai=args.include_fanwai)
        if chapters:
            args.end = max(chapters)
            print(f"自动检测到最大章节: 第{args.end}章")

    if args.workers is None:
        args.workers = args.end - args.start + 1
        print(f"workers 自动设为章节数: {args.workers}")

    print(f"改写流水线 | {config['book_name']} | ch{args.start}-{args.end} | workers={args.workers}")
    print(f"项目目录: {config.get('rewrites_dir')}")

    t0 = time.time()
    phases = set(args.phase.split(","))

    if "all" in phases or "prep" in phases or "open-book" in phases:
        phase_prep(config)

    if "all" in phases or "open-book" in phases:
        concept_path = Path(config["rewrites_dir"]) / "concept.md"
        if concept_path.exists():
            print(f"concept.md 已存在，跳过开书")
        else:
            phase_open_book(config)

    if "all" in phases or "style-profile" in phases:
        phase_style_profile(config)

    if "all" in phases or "guides" in phases:
        phase_guides(config, args.start, args.end, args.workers, serial=args.serial)

    if "all" in phases or "write" in phases:
        # 分批写章+对比（每10章一批）
        batch_size = 10
        for batch_start in range(args.start, args.end + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, args.end)
            print(f"\n{'#' * 50}")
            print(f" 批次: 第{batch_start}-{batch_end}章")
            print(f"{'#' * 50}")
            
            phase_write(config, batch_start, batch_end, args.workers)
            phase_postfix(config, batch_start, batch_end)
            phase_compare(config, batch_start, batch_end)
        
        # 全部完成后启动阅读器
        open_reader(config)

    if "all" in phases or "validate" in phases:
        phase_validate(config, args.start, args.end)

    if "all" in phases or "trim" in phases:
        phase_trim(config, args.start, args.end)

    if "continuity" in phases:
        phase_continuity(config, args.start, args.end, args.workers)

    if "all" in phases or "compare" in phases:
        phase_compare(config, args.start, args.end)

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
            os.makedirs(export_dir, exist_ok=True)
            if merge_chapters(chapters_dir, export_file):
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
            ("style-profile.md", "全局风格画像"),
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
    
    print(f"\n如需修复，可运行：")
    print(f"python .agents/skills/story-engine/tools/rewrite_chapters.py --config {args.config} --phase continuity --start {args.start} --end {args.end}")


if __name__ == '__main__':
    main()
