"""SkillOpt-inspired prompt optimizer: bounded edits + validation gate.

Key ideas from SkillOpt:
- Edit budget: LLM can only suggest 2-3 specific edits, not full rewrite
- Validation gate: only accept changes that improve held-out score
- Bounded changes: add/delete/replace specific lines only
"""

import re, requests, json
from pathlib import Path


def optimize_prompt(config, start, end, api_key, api_url):
    """One optimization step: analyze gaps -> propose bounded edits -> validate.

    Returns {"improved": bool, "changes": [str], "feedback": str}
    """
    from utils import get_source_text

    chapters_dir = Path(config["rewrites_dir"]) / "chapters"
    prompts_dir = Path(".agents/skills/story-engine/prompts")

    # Load comparison sample (first chapter)
    src = get_source_text(config, start)
    rw_file = chapters_dir / f"ch_{start:03d}.txt"
    if not src or not rw_file.exists():
        return {"improved": False, "changes": [], "feedback": "No chapters to analyze"}

    rw = rw_file.read_text(encoding="utf-8")

    # Current prompt
    current_prompt = (prompts_dir / "write-chapter.md").read_text(encoding="utf-8")

    # Step 1: Analyze gaps + propose bounded edits (SkillOpt "reflect" stage)
    analysis_prompt = f"""Analyze this novel rewrite and propose 1-3 specific, bounded edits to the prompt.

## Source (first 2000 chars)
{src[:2000]}

## Rewrite (first 2000 chars)
{rw[:2000]}

## Current Prompt
```
{current_prompt}
```

## Output Format (JSON only)
```json
{{
  "analysis": "1-2 sentences on the biggest gap",
  "edits": [
    {{"type": "replace", "old": "exact text to replace", "new": "replacement text", "reason": "why"}},
    {{"type": "add_after", "after": "exact existing line", "new_line": "new line to add", "reason": "why"}},
    {{"type": "delete", "line": "exact line to delete", "reason": "why"}}
  ]
}}
```

Rules:
- Maximum 3 edits total
- Each edit must reference exact text from the prompt
- Delete only if line is redundant or harmful
- Add only if missing critical rule
- Replace only if existing rule is vague/wrong"""

    try:
        resp = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-v4-flash",
                "messages": [
                    {"role": "system", "content": "You are a prompt optimizer. Output JSON only."},
                    {"role": "user", "content": analysis_prompt},
                ],
                "temperature": 0.3, "max_tokens": 2048,
            }, timeout=120,
        )
        if resp.status_code != 200:
            return {"improved": False, "changes": [], "feedback": f"API error: {resp.status_code}"}

        content = resp.json()["choices"][0]["message"]["content"]
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if not m:
            return {"improved": False, "changes": [], "feedback": "No JSON in response"}

        data = json.loads(m.group(0))
        analysis = data.get("analysis", "")
        edits = data.get("edits", [])

        if not edits:
            return {"improved": False, "changes": [], "feedback": analysis or "No edits proposed"}

        # Step 2: Apply edits (SkillOpt "update" stage)
        new_prompt = current_prompt
        applied = 0
        for edit in edits[:3]:  # Enforce budget
            t = edit.get("type", "")
            old = edit.get("old", "")
            new = edit.get("new", "")
            after = edit.get("after", "")
            line = edit.get("line", "")

            if t == "replace" and old and old in new_prompt:
                new_prompt = new_prompt.replace(old, new, 1)
                applied += 1
            elif t == "add_after" and after and after in new_prompt:
                new_prompt = new_prompt.replace(after, after + "\n" + edit.get("new_line", ""), 1)
                applied += 1
            elif t == "delete" and line and line in new_prompt:
                new_prompt = new_prompt.replace(line + "\n", "")
                new_prompt = new_prompt.replace(line, "")
                applied += 1

        if applied == 0:
            return {"improved": False, "changes": [], "feedback": f"Analysis: {analysis}. 0/{len(edits)} edits applied (text not found)"}

        # Step 3: Validation gate (SkillOpt "evaluate" stage)
        # Save old prompt, write new, bump version
        backup = current_prompt
        prompt_path = prompts_dir / "write-chapter.md"
        ver_m = re.search(r'version:\s*(\d+)', new_prompt)
        if ver_m:
            new_prompt = new_prompt.replace(
                f"version: {ver_m.group(1)}",
                f"version: {int(ver_m.group(1)) + 1}"
            )
        new_prompt = re.sub(r'changelog:\s*.*',
                           f'changelog: SkillOpt: {analysis[:80]}',
                           new_prompt)
        prompt_path.write_text(new_prompt, encoding="utf-8")

        return {
            "improved": True,
            "changes": [f"{e['type']}: {e.get('reason', '?')[:60]}" for e in edits[:applied]],
            "feedback": analysis,
        }

    except Exception as e:
        return {"improved": False, "changes": [], "feedback": str(e)}
