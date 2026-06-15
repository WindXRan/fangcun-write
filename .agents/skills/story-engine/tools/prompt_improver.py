"""LLM-driven prompt improvement. Replaces mechanical rule-strengthening."""

import re
import requests
from pathlib import Path


def llm_improve_prompts(p0_issues, api_key, api_url):
    """Analyze P0 issues with LLM, rewrite affected prompts, bump version.
    Returns list of {prompt, summary} changes.
    """
    if not p0_issues:
        return []

    target_prompts = _identify_prompts(p0_issues)
    if not target_prompts:
        return []

    changes = []
    for prompt_name in target_prompts:
        path = Path(".agents/skills/story-engine/prompts") / prompt_name
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")

        issue_text = "\n".join(
            f"- [P0] [{iss.get('type','?')}] ch{iss.get('ch','?')}: {iss.get('desc','')[:200]}"
            for iss in p0_issues
        )[:2000]

        prompt = f"""Here are P0 issues from a novel rewrite run, and a prompt file. Fix the prompt to solve these issues.

## P0 Issues
{issue_text}

## Current prompt ({prompt_name})
```
{original}
```

## Requirements
Modify the prompt to fix these issues. You may: add examples, rewrite vague rules, adjust order, add counter-examples. Do NOT: remove rules, change YAML header, change variable names. Output the complete modified prompt file."""

        try:
            resp = requests.post(
                api_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-v4-flash",
                    "messages": [
                        {"role": "system", "content": "You are a prompt engineer. Output the complete modified prompt file."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3, "max_tokens": 4096,
                }, timeout=120,
            )
            if resp.status_code == 200:
                new_content = resp.json()["choices"][0]["message"]["content"]
                m = re.search(r'---\s*\n.*?\n---.*', new_content, re.DOTALL)
                if m:
                    new_content = m.group(0)

                cl_m = re.search(r'changelog:\s*(.+)', new_content)
                summary = cl_m.group(1)[:100] if cl_m else "LLM improved prompt"

                _bump_version(path, summary)
                path.write_text(new_content, encoding="utf-8")
                changes.append({"prompt": prompt_name, "summary": summary})
                print(f"  [OK] {prompt_name}: {summary}")
        except Exception as e:
            print(f"  [FAIL] {prompt_name}: {e}")

    return changes


def _identify_prompts(p0_issues):
    """Map P0 issue types to prompt files that need fixing."""
    prompts = set()
    for iss in p0_issues:
        typ = iss.get("type", "")
        if typ in ("character", "continuity"):
            prompts.add("write-chapter.md")
        elif typ in ("plagiarism", "ai_marker", "ai_trace"):
            prompts.add("system-generic.md")
        elif typ in ("emotion", "emotion_tell", "emotion_stage"):
            prompts.add("write-chapter.md")
        elif typ in ("word_count",):
            prompts.add("write-chapter.md")
        elif typ in ("rhythm",):
            prompts.add("plot-guide.md")
        else:
            prompts.add("write-chapter.md")
    return list(prompts)[:2]


def _bump_version(path, changelog):
    """Increment version number in prompt frontmatter."""
    content = path.read_text(encoding="utf-8")
    m = re.search(r'version:\s*(\d+)', content)
    if m:
        old_ver = int(m.group(1))
        content = content.replace(f"version: {old_ver}", f"version: {old_ver + 1}")
    content = re.sub(r'changelog:\s*.*', f'changelog: {changelog}', content)
    path.write_text(content, encoding="utf-8")
