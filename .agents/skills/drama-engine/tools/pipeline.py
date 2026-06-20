"""
剧本引擎 — 小说转短剧剧本（Toonflow 原生流程 + 全量优化）

优化项：
  - 按阶段配置模型（model_overrides）
  - 事件提取滑窗上下文（带前2章摘要）
  - 事件提取默认用非推理模型
  - 增量骨架（只生成有事件支撑的集数）
  - 剧本只传当前集相关骨架片段
  - 输出校验层

用法:
  python pipeline.py --config configs/drama_xxx.json                     # 全流程
  python pipeline.py --config configs/drama_xxx.json --phase event       # 仅事件提取
  python pipeline.py --config configs/drama_xxx.json --phase skeleton    # 仅骨架
  python pipeline.py --config configs/drama_xxx.json --phase adaptation  # 仅改编策略
  python pipeline.py --config configs/drama_xxx.json --phase script --start 1 --end 10
  python pipeline.py --config configs/drama_xxx.json --phase review      # 质量审核
  python pipeline.py --config configs/drama_xxx.json --phase export      # 合并导出
"""

import os
import sys
import re
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加 shared-engine 和 source-engine tools 到 path 以复用共享模块
_shared_engine_tools = str(Path(__file__).parent.parent.parent / "shared-engine" / "tools")
_source_engine_tools = str(Path(__file__).parent.parent.parent / "source-engine" / "tools")
sys.path.insert(0, _shared_engine_tools)  # shared-engine 优先
sys.path.insert(0, _source_engine_tools)  # source-engine 兼容
from lib.api_client import call_api, get_api_key, get_api_url
from source_analysis import (
    load_events, save_events, get_events_text, get_source_chapters, get_source_text,
    load_skeleton, save_skeleton, load_adaptation, save_adaptation,
    extract_events, build_skeleton, build_adaptation,
    get_cache_dir,
)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

def load_prompt(name: str) -> str:
    p = _PROMPTS_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {p}")
    return p.read_text(encoding="utf-8")

from state_manager import StateManager

from agent_tools import (
    get_events, get_events_json, save_events,
    get_skeleton, save_skeleton,
    get_adaptation, save_adaptation,
    get_novel_text, get_novel_chapters,
    get_script_content, save_script, get_all_scripts,
    extract_xml_tag, extract_script_items,
    extract_episode_from_skeleton,
    validate_script, validate_event,
)


# ─── 模型解析 ───────────────────────────────────────────────────────────────

def get_phase_model(config: dict, phase: str) -> str:
    """按阶段解析模型。优先级：model_overrides.{phase} > model。

    优化：事件提取默认用非推理模型（避免 MiMo 推理 token 浪费）。
    """
    overrides = config.get("model_overrides", {})
    if phase in overrides:
        return overrides[phase]
    # 事件提取如果没有显式配置，默认用 deepseek-chat（非推理模型）
    if phase == "event" and "model_overrides" not in config:
        return "deepseek-chat"
    return config.get("model", "deepseek-chat")


def get_phase_api(config: dict, phase: str) -> tuple[str, str, str]:
    """返回 (api_key, api_url, model)。"""
    api_key = get_api_key(config)
    api_url = get_api_url(config)
    model = get_phase_model(config, phase)
    return api_key, api_url, model


# ─── 项目配置信息 ───────────────────────────────────────────────────────────

def build_project_info(config: dict) -> str:
    p = config.get("project", {})
    duration = p.get("episode_duration", 2)
    words_per_ep = int(duration * 150)
    ch_range = p.get("chapter_range", [1, 999])
    return f"""【项目配置】
- 集数：{p.get('episodes', '?')}集
- 单集时长：{duration}分钟（约{words_per_ep}字台词）
- 原著范围：第{ch_range[0]}-{ch_range[1]}章
- 平台规格：{p.get('platform', '竖屏9:16')}
- 风格定位：{p.get('style', '未指定')}
- 付费策略：{p.get('paywall', '未指定')}"""


# ─── 事件提取（优化：滑窗上下文 + 非推理模型 + 增量保存 + 校验）──────────

def phase_event(config: dict, workers: int = 5):
    api_key, api_url, model = get_phase_api(config, "event")
    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return False
    prompt_text = load_prompt("event_extraction.md")
    cache_dir = get_cache_dir(config)
    print(f"\n{'='*50}")
    print(f"事件提取 | {config.get('novel_name', '')}")
    print(f"输出: {cache_dir}/events.json")
    print(f"{'='*50}")
    events = extract_events(config, api_key, api_url, model, prompt_text, workers)
    return len(events) > 0


def phase_skeleton(config: dict, dry_run: bool = False):
    api_key, api_url, model = get_phase_api(config, "skeleton")
    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return False
    system_prompt = load_prompt("skeleton.md")
    system_prompt += "\n\n你必须使用如下XML格式写入工作区：\n<storySkeleton>故事骨架内容</storySkeleton>"
    if dry_run:
        print(f"[DRY-RUN] 模型 {model}")
        return True
    cache_dir = get_cache_dir(config)
    print(f"\n{'='*50}")
    print(f"故事骨架 | {config.get('novel_name', '')}")
    print(f"输出: {cache_dir}/story_skeleton.md")
    print(f"{'='*50}")
    result = build_skeleton(config, api_key, api_url, model, system_prompt, config.get("novel_name", ""))
    return result is not None


def phase_adaptation(config: dict, dry_run: bool = False):
    api_key, api_url, model = get_phase_api(config, "adaptation")
    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return False
    system_prompt = load_prompt("adaptation.md")
    system_prompt += "\n\n你必须使用如下XML格式写入工作区：\n<adaptationStrategy>改编策略内容</adaptationStrategy>"
    if dry_run:
        print(f"[DRY-RUN] 模型 {model}")
        return True
    cache_dir = get_cache_dir(config)
    print(f"\n{'='*50}")
    print(f"改编策略 | {config.get('novel_name', '')}")
    print(f"输出: {cache_dir}/adaptation_strategy.md")
    print(f"{'='*50}")
    result = build_adaptation(config, api_key, api_url, model, system_prompt, config.get("novel_name", ""))
    return result is not None


# ─── 剧本编写（优化：只传当前集骨架片段 + 输出校验）─────────────────────────

def phase_script(config: dict, start: int = 1, end: int = 3, dry_run: bool = False, state: StateManager = None):
    output_dir = config["output_dir"]
    source_dir = config["source_dir"]
    api_key, api_url, model = get_phase_api(config, "script")

    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return False

    skeleton = get_skeleton(output_dir)
    adaptation = get_adaptation(output_dir)
    events_text = get_events(output_dir)

    if not skeleton:
        print("[FAIL] 故事骨架不存在，请先 --phase skeleton")
        return False
    if not adaptation:
        print("[FAIL] 改编策略不存在，请先 --phase adaptation")
        return False

    project = config.get("project", {})
    project_info = build_project_info(config)
    duration = project.get("episode_duration", 2)
    target_words = int(duration * 150)

    system_prompt = load_prompt("script.md")
    # 加载写作方法论作为参考上下文
    try:
        writing_methods = load_prompt("writing-methods.md")
        system_prompt += f"\n\n## 写作方法论参考（仅供创意参考，不写进剧本）\n\n{writing_methods}"
    except FileNotFoundError:
        pass
    format_prompt = '\n你必须使用如下XML格式写入工作区：\n<scriptItem name="剧本名称">剧本内容</scriptItem>'

    existing_scripts = get_all_scripts(output_dir)
    script_list_str = ""
    if existing_scripts:
        script_list_str = "## 已有剧本\n" + ", ".join(
            [f"第{s['id']}集:{s['name']}" for s in existing_scripts]
        )

    print(f"\n{'='*50}")
    print(f"剧本编写 | {config.get('novel_name', '')} | 第{start}-{end}集")
    print(f"模型: {model} | 目标: {target_words}字/集")
    print(f"{'='*50}")

    t0 = time.time()
    done = 0
    total = end - start + 1
    validation_warnings = []

    for ep_num in range(start, end + 1):
        # 读取上一集剧本
        prev_script = ""
        if ep_num > 1:
            prev_script = get_script_content(output_dir, [ep_num - 1])

        # 优化：只提取当前集相关的骨架片段
        ep_skeleton = extract_episode_from_skeleton(skeleton, ep_num)

        # 读取对应章节原文
        novel_text_sample = ""
        events_json = get_events_json(output_dir)
        if events_json:
            chapter_range = project.get("chapter_range", [1, 999])
            chapters_per_ep = max(1, (chapter_range[1] - chapter_range[0] + 1) // project.get("episodes", 20))
            ch_start = chapter_range[0] + (ep_num - 1) * chapters_per_ep
            ch_end = min(ch_start + chapters_per_ep - 1, chapter_range[1])
            for ch in range(ch_start, min(ch_start + 3, ch_end + 1)):
                text = get_novel_text(source_dir, ch)
                if text:
                    novel_text_sample += f"\n\n--- 第{ch}章 ---\n{text[:2000]}"

        user_prompt = f"""{project_info}

## 作品名称
{config.get('novel_name', '未命名')}

{script_list_str}

## 本集骨架信息
{ep_skeleton}

## 改编策略
{adaptation}

## 事件表
{events_text[:2000]}

{"## 上一集剧本（用于衔接）" if prev_script else ""}
{prev_script[:2000] if prev_script else ""}

{"## 对应章节原文（参考）" if novel_text_sample else ""}
{novel_text_sample[:3000] if novel_text_sample else ""}

请编写第{ep_num}集的完整剧本。目标字数：约{target_words}字台词。{format_prompt}"""

        if dry_run:
            print(f"  [DRY-RUN] 第{ep_num}集 prompt 长度: {len(user_prompt)}字")
            continue

        try:
            result = call_api(
                api_key, model, user_prompt,
                system_prompt=system_prompt + format_prompt,
                api_url=api_url,
                temperature=0.7,
                max_tokens=4096,
            )
        except Exception as e:
            done += 1
            print(f"  [{done}/{total}] ✗ 第{ep_num}集 ({e})")
            if state:
                state.episode_failed(ep_num, error=str(e))
                state.save()
            continue

        # 提取 <scriptItem> 标签
        items = extract_script_items(result)
        if items:
            script_content = items[0]["content"]
        else:
            script_content = result.strip()

        # 输出校验
        v_issues = validate_script(script_content, target_words)
        if v_issues:
            validation_warnings.append((ep_num, v_issues))
            issue_summary = " | ".join(v_issues[:2])
            print(f"  [{done+1}/{total}] ⚠ 第{ep_num}集 ({len(script_content)}字) {issue_summary}")
        else:
            done += 1
            print(f"  [{done}/{total}] ✓ 第{ep_num}集 ({len(script_content)}字)")

        save_script(output_dir, ep_num, script_content)
        done += 1
        if state:
            state.episode_completed(ep_num, chars=len(script_content))
            state.save()

    elapsed = time.time() - t0
    print(f"\n{'='*50}")
    print(f"完成 | 第{start}-{end}集 | {elapsed:.0f}s")
    if validation_warnings:
        print(f"校验警告: {len(validation_warnings)}集有问题")
        for ep, issues in validation_warnings:
            for issue in issues:
                print(f"  集{ep}: {issue}")
    print(f"输出: {output_dir}/scripts/")
    print(f"{'='*50}")
    return True


# ─── 质量审核 ───────────────────────────────────────────────────────────────

def phase_review(config: dict, target: str = "all"):
    output_dir = config["output_dir"]
    api_key, api_url, model = get_phase_api(config, "review")

    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return False

    project_info = build_project_info(config)
    system_prompt = load_prompt("supervision.md")
    reviews_dir = Path(output_dir) / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)

    results = []

    if target in ("skeleton", "all"):
        skeleton = get_skeleton(output_dir)
        if skeleton:
            print(f"\n{'='*50}")
            print(f"审核：故事骨架")
            print(f"{'='*50}")

            events_text = get_events(output_dir)
            user_prompt = f"""{project_info}

请审核【故事骨架】的产出物。
审核维度：结构完整性、分集与时长、章节全覆盖、付费点分布、股价级反转登记、矛盾强度、三大密度结构、心理级爽点/金手指、投放素材、前10%黄金结构、情绪布局、信息差标注、集末钩子、节奏框架

## 故事骨架
{skeleton}

## 事件表
{events_text}"""

            try:
                result = call_api(
                    api_key, model, user_prompt,
                    system_prompt=system_prompt,
                    api_url=api_url,
                    temperature=0.3,
                    max_tokens=4096,
                )
                review_file = reviews_dir / "skeleton_review.md"
                review_file.write_text(result, encoding="utf-8")
                results.append(("故事骨架", result))
                print(f"  ✓ 审核完成 → {review_file}")
            except Exception as e:
                print(f"  ✗ 审核失败: {e}")

    if target in ("adaptation", "all"):
        adaptation = get_adaptation(output_dir)
        skeleton = get_skeleton(output_dir)
        if adaptation:
            print(f"\n{'='*50}")
            print(f"审核：改编策略")
            print(f"{'='*50}")

            user_prompt = f"""{project_info}

请审核【改编策略】的产出物。
审核维度：用户意图一致、与骨架一致、原创性/反洗稿、股价级反转来源一致、8大要点覆盖、三大密度策略、心理级爽点锁定、AI形态适配、原则质量、情绪基调一致、人物弧光保留、删减合理性、世界观呈现、语言适配

## 故事骨架
{skeleton}

## 改编策略
{adaptation}"""

            try:
                result = call_api(
                    api_key, model, user_prompt,
                    system_prompt=system_prompt,
                    api_url=api_url,
                    temperature=0.3,
                    max_tokens=4096,
                )
                review_file = reviews_dir / "adaptation_review.md"
                review_file.write_text(result, encoding="utf-8")
                results.append(("改编策略", result))
                print(f"  ✓ 审核完成 → {review_file}")
            except Exception as e:
                print(f"  ✗ 审核失败: {e}")

    if results:
        print(f"\n{'='*50}")
        print(f"审核完成 | {len(results)}项")
        print(f"{'='*50}")
    return True


# ─── 合并导出 ───────────────────────────────────────────────────────────────

def phase_export(config: dict):
    output_dir = config["output_dir"]
    drama_name = config.get("drama_name", "剧本")
    scripts = get_all_scripts(output_dir)

    if not scripts:
        print("没有可导出的剧本")
        return

    parts = [s["content"] for s in scripts]
    export_file = Path(output_dir) / f"{drama_name}.txt"
    export_file.write_text("\n\n---\n\n".join(parts), encoding="utf-8")
    print(f"导出完成: {export_file} ({len(scripts)}集)")


# ─── 主入口 ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="剧本引擎 — 小说转短剧剧本")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--phase", default="all",
                        choices=["all", "resume", "event", "skeleton", "adaptation", "script", "review", "export", "status"],
                        help="执行阶段（resume=断点续传，status=查看进度）")
    parser.add_argument("--start", type=int, default=1, help="剧本起始集")
    parser.add_argument("--end", type=int, default=3, help="剧本结束集")
    parser.add_argument("--workers", type=int, default=5, help="事件提取并行数")
    parser.add_argument("--review-target", default="all", choices=["skeleton", "adaptation", "all"],
                        help="审核目标")
    parser.add_argument("--dry-run", action="store_true", help="只分析不执行")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    output_dir = config["output_dir"]
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 加载状态
    state = StateManager(output_dir)
    state.load()

    print(f"\n{'#'*50}")
    print(f"剧本引擎 | {config.get('novel_name', '')} → {config.get('drama_name', '')}")
    print(f"阶段: {args.phase}")
    print(f"{'#'*50}")

    # --status: 查看进度
    if args.phase == "status":
        state.print_status()
        return

    # --resume: 断点续传
    if args.phase == "resume":
        resume_phase = state.get_resume_phase()
        if resume_phase is None:
            print("全部完成，无需续传")
            state.print_status()
            return
        print(f"断点续传: 从 {resume_phase} 阶段继续")
        args.phase = resume_phase
        # resume 时 script 默认续写到 config 中的集数
        if resume_phase == "script":
            project = config.get("project", {})
            args.end = project.get("episodes", args.end)

    # 执行
    if args.phase == "all":
        _run_all(config, state, args)
    elif args.phase == "event":
        _run_phase(state, "event", lambda: phase_event(config, args.workers))
    elif args.phase == "skeleton":
        _run_phase(state, "skeleton", lambda: phase_skeleton(config, args.dry_run))
    elif args.phase == "adaptation":
        _run_phase(state, "adaptation", lambda: phase_adaptation(config, args.dry_run))
    elif args.phase == "script":
        _run_phase(state, "script", lambda: phase_script(config, args.start, args.end, args.dry_run, state))
    elif args.phase == "review":
        _run_phase(state, "review", lambda: phase_review(config, args.review_target))
    elif args.phase == "export":
        phase_export(config)


def _run_phase(state, phase_name, fn):
    """包装单个 phase 的执行：自动记录 start/done/failed。"""
    if state.is_phase_done(phase_name):
        print(f"  {phase_name} 已完成，跳过（用 --phase {phase_name} 强制重跑）")
        return True
    state.phase_start(phase_name)
    try:
        result = fn()
        if result:
            state.phase_done(phase_name)
        else:
            state.phase_failed(phase_name, "返回失败")
        return result
    except Exception as e:
        state.phase_failed(phase_name, str(e))
        raise


def _run_all(config, state, args):
    """全流程执行：骨架→审核→改编→审核→剧本→导出。审核前置，避免基于错误骨架写剧本。"""
    phases = [
        ("event",           lambda: phase_event(config, args.workers)),
        ("skeleton",        lambda: phase_skeleton(config, args.dry_run)),
        ("skeleton_review", lambda: phase_review(config, "skeleton")),
        ("adaptation",      lambda: phase_adaptation(config, args.dry_run)),
        ("adaptation_review", lambda: phase_review(config, "adaptation")),
        ("script",          lambda: phase_script(config, args.start, args.end, args.dry_run, state)),
    ]
    for name, fn in phases:
        if not _run_phase(state, name, fn):
            return
    phase_export(config)
    state.print_status()


if __name__ == "__main__":
    main()
