#!/usr/bin/env python3
"""测试部署配置"""

import os
import sys
from pathlib import Path

def test_skill_structure(skill_path: str) -> bool:
    """测试skill目录结构"""
    skill_dir = Path(skill_path)
    
    print(f"\n=== Testing {skill_dir.name} ===")
    
    # 检查SKILL.md
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        print(f"✅ SKILL.md exists ({skill_md.stat().st_size} bytes)")
    else:
        print(f"❌ SKILL.md missing")
        return False
    
    # 检查是否有工具目录
    tools_dir = skill_dir / "tools"
    if tools_dir.exists():
        tools = list(tools_dir.glob("*.py"))
        print(f"✅ tools/ exists ({len(tools)} Python files)")
    else:
        print(f"⚠️  tools/ missing (optional)")
    
    # 检查是否有references目录
    refs_dir = skill_dir / "references"
    if refs_dir.exists():
        refs = list(refs_dir.glob("*.md"))
        print(f"✅ references/ exists ({len(refs)} files)")
    else:
        print(f"⚠️  references/ missing (optional)")
    
    return True


def test_github_actions() -> bool:
    """测试GitHub Actions配置"""
    print("\n=== Testing GitHub Actions ===")
    
    workflow_file = Path(".github/workflows/deploy-skills.yml")
    if workflow_file.exists():
        print(f"✅ deploy-skills.yml exists")
        return True
    else:
        print(f"❌ deploy-skills.yml missing")
        return False


def test_deploy_scripts() -> bool:
    """测试部署脚本"""
    print("\n=== Testing Deploy Scripts ===")
    
    scripts = [
        "scripts/deploy/deploy_coze.py",
        "scripts/deploy/test_deploy.py"
    ]
    
    all_ok = True
    for script in scripts:
        if Path(script).exists():
            print(f"✅ {script}")
        else:
            print(f"❌ {script} missing")
            all_ok = False
    
    return all_ok


def main():
    print("=== Deployment Configuration Test ===")
    
    # 测试skill目录
    skills_dir = Path(".agents/skills")
    skills = list(skills_dir.glob("fangcun-*")) + list(skills_dir.glob("story-*"))
    
    print(f"\nFound {len(skills)} skills:")
    for skill in skills:
        if skill.is_dir():
            test_skill_structure(str(skill))
    
    # 测试GitHub Actions
    test_github_actions()
    
    # 测试部署脚本
    test_deploy_scripts()
    
    print("\n=== Summary ===")
    print("To deploy:")
    print("  1. Configure GitHub Secrets (see scripts/deploy/README.md)")
    print("  2. Create a tag: git tag v1.0.0 && git push origin v1.0.0")
    print("  3. Or manually trigger in GitHub Actions")


if __name__ == "__main__":
    main()
