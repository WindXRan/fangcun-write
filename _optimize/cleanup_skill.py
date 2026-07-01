p = '.agents/skills/fangcun-write/SKILL.md'
content = open(p, encoding='utf-8').read()

changes = {
    "| ~~`adaptation`~~ | ~~改编策略~~ | ~~已删除~~ |\n": "",
    "| `cover-prompt` | 封面提示词（只输出不调API） | 封面 |\n": "",
    "| `character-designer` | 角色设计 | 设计角色 |\n": "",
    "| `golden-opening` | 黄金开篇 | 开篇设计 |\n": "",
    "| `book-draw` | 顶层设计 | 顶层设计 |\n": "",
    r"| `plot-guide/nanpin` | `builtin/plot-guide/nanpin.xml` | **男频**，密集事件流+4段式 | 男频、升级、打脸、信息差、冲突密度 |": "",
    "   - 角色问题 → 检查角色卡质量或修改 `character-designer` 预设": "   - 角色问题 → 检查角色卡质量或修改 `character-generate` 预设",
    "| `@角色卡` / `@作品信息/设定/角色` | 角色设定文件 | `character-designer` |": "| `@角色卡` / `@作品信息/设定/角色` | 角色设定文件 | `character-generate` |",
    "run_preset(\"character-designer\") 或 run_preset(\"character-generate\")": "run_preset(\"character-generate\")",
}

for old, new in changes.items():
    if old in content:
        content = content.replace(old, new)
        print(f"Replaced: {old[:40]}...")
    else:
        print(f"NOT FOUND: {old[:40]}...")

open(p, 'w', encoding='utf-8').write(content)
print("\nDone")
