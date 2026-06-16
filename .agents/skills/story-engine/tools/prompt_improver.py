"""Smart editor agent: reads source+rewrite+all prompts, outputs feedback + improved prompts.

No numeric scores. No rule-based mapping. One LLM call does everything.
"""

import re
from pathlib import Path


def smart_edit_loop(config, start, end, api_key, api_url, loop_num):
    """One smart agent: analyze gaps -> editorial feedback -> modify any prompts.

    Returns dict with {feedback, changes, prompts_modified}
    """
    from utils import get_source_text
    from lib.api_client import call_api

    chapters_dir = Path(config["rewrites_dir"]) / "chapters"
    prompts_dir = Path(".agents/skills/story-engine/prompts")

    # Load source vs rewrite (full text, up to 3 chapters)
    comparison_parts = []
    for ch in range(start, min(end, start + 3)):
        src = get_source_text(config, ch)
        rw_file = chapters_dir / f"ch_{ch:03d}.txt"
        if src and rw_file.exists():
            rw = rw_file.read_text(encoding="utf-8")
            comparison_parts.append(
                f"## 第{ch}章 源文\n{src[:3000]}\n\n## 第{ch}章 仿写\n{rw[:3000]}"
            )
    comparison = "\n\n---\n\n".join(comparison_parts)

    # Load ALL current prompts
    all_prompts = {}
    for f in sorted(prompts_dir.glob("*.md")):
        if f.stem.startswith("system-") or f.stem in ("write-chapter", "plot-guide", "style-analyze",
                                                       "unified-review", "unified-fix", "open-book"):
            all_prompts[f.name] = f.read_text(encoding="utf-8")

    prompt_section = "\n\n".join(
        f"### {name}\n```\n{content[:2000]}\n```"
        for name, content in all_prompts.items()
    )

    # Concepts for context
    concepts = ""
    for name in ["concept.md", "characters.md", "plot.md"]:
        p = Path(config["rewrites_dir"]) / name
        if p.exists():
            concepts += f"\n### {name}\n{p.read_text(encoding='utf-8')[:1000]}\n"

    # The prompt for the smart editor
    editor_prompt = f"""You are a master web novel editor. Review the source vs rewrite comparison and ALL prompts. Give editorial feedback, then modify prompts to close gaps.

## Source vs Rewrite (full text comparison)
{comparison}

## Story Concepts
{concepts}

## Current Prompts
{prompt_section}

## Task

### Part 1: Editorial Feedback
Analyze the gaps between source and rewrite in these dimensions:
- Hook/Opening: Does the rewrite open the same way as the source?
- Paragraph rhythm: Same paragraph length and count?
- Dialogue handling: Same style of dialogue tags and density?
- Emotional register: Same intensity and expression style?
- Character voice: Do characters behave according to their cards?

Be specific. Quote examples from both texts. Do NOT give numeric scores.

### Part 2: Prompt Modifications
Based on your analysis, modify up to 3 prompts. For each:
- Which prompt file (exact filename)?
- What specific change and why?
- Output the COMPLETE modified prompt (with YAML header).

Output format:
```
## Editorial Feedback
(your analysis here)

## Prompt Changes

### FILE: write-chapter.md
(complete modified file content)

### FILE: system-generic.md
(complete modified file content)
```
"""

    try:
        content = call_api(
            api_key, "deepseek-v4-flash", editor_prompt,
            temperature=0.3, max_tokens=8192,
            api_url=api_url,
            system_prompt="You are a master web novel editor and prompt engineer. Output editorial feedback and complete modified prompts.",
        )

        # Extract feedback
        fb_match = re.search(r'## Editorial Feedback\n(.*?)(?=## Prompt Changes|\Z)', content, re.DOTALL)
        feedback = fb_match.group(1).strip() if fb_match else content[:500]

        # Extract and apply prompt changes
        changes = []
        for m in re.finditer(r'### FILE:\s*(\S+)\s*\n(.*?)(?=### FILE:|\Z)', content, re.DOTALL):
            fname = m.group(1).strip()
            new_content = m.group(2).strip()
            # Verify it has YAML header
            if new_content.startswith("---"):
                path = prompts_dir / fname
                if path.exists():
                    # Bump version
                    old = path.read_text(encoding="utf-8")
                    ver_m = re.search(r'version:\s*(\d+)', new_content)
                    if not ver_m:
                        old_ver = re.search(r'version:\s*(\d+)', old)
                        if old_ver:
                            new_content = new_content.replace(
                                f"version: {old_ver.group(1)}",
                                f"version: {int(old_ver.group(1)) + 1}"
                            )
                    path.write_text(new_content, encoding="utf-8")
                    changes.append(fname)
                    print(f"  [OK] {fname} updated")

        return {"feedback": feedback, "changes": changes}

    except Exception as e:
        return {"feedback": f"Error: {e}", "changes": []}
