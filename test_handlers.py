#!/usr/bin/env python3
"""测试 handlers.py 中的新增处理器"""
import sys
from pathlib import Path

# 添加 tools 目录到路径
sys.path.insert(0, str(Path(__file__).parent / ".agents/skills/fangcun-write/tools"))

from variable_resolver import VariableResolver

# 测试项目路径
novel_dir = Path(r"C:\Users\Administrator\Documents\trae_projects\fangcun-write\projects\仿写新书")

# 创建解析器
resolver = VariableResolver(novel_dir)

# 测试 1: 关联章节（默认行为：上一章）
print("=" * 60)
print("测试 1: 关联章节（默认取上一章）")
resolver.set_context(N=5)
result = resolver.resolve("关联章节")
print(f"N=5 时，关联章节 = 第4章章尾")
print(f"结果前200字符:\n{result[:200]}")
print()

# 测试 2: 关联章节（手动指定）
print("=" * 60)
print("测试 2: 关联章节（手动指定 关联章节号=3）")
resolver.set_context(N=5, 关联章节号=3)
result = resolver.resolve("关联章节")
print(f"结果前200字符:\n{result[:200]}")
print()

# 测试 3: 后续章节
print("=" * 60)
print("测试 3: 后续章节（手动指定 后续章节号=6）")
resolver.set_context(N=5, 后续章节号=6)
result = resolver.resolve("后续章节")
print(f"结果前200字符:\n{result[:200]}")
print()

# 测试 4: 关联章纲
print("=" * 60)
print("测试 4: 关联章纲（默认取上一章）")
resolver.set_context(N=5)
result = resolver.resolve("关联章纲")
print(f"结果前200字符:\n{result[:200]}")
print()

print("=" * 60)
print("所有测试完成！")
