"""Phase 4: 对比（生成仿写 vs 源文对比报告）"""

import os
import sys
import subprocess
from pathlib import Path

# 添加路径
current_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, current_dir)


def phase_compare(config, start, end, batch_size=10):
    """生成仿写 vs 源文对比报告（分批处理）"""
    rewrites_dir = config["rewrites_dir"]
    compare_dir = f"{rewrites_dir}/compare"
    compare_script = ".agents/skills/story-compare/compare.py"

    print(f"\n{'=' * 50}")
    print(f"Phase 4: 对比 (ch{start}-{end}, 每{batch_size}章一批)")
    print("=" * 50)
    
    # 清理旧的对比报告
    for old_file in Path(compare_dir).glob("对比_*.md"):
        old_file.unlink()
    for old_file in Path(compare_dir).glob("源文_*.txt"):
        old_file.unlink()
    for old_file in Path(compare_dir).glob("新书_*.txt"):
        old_file.unlink()
    print("已清理旧对比报告")

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
            
            print(f"  [OK] 对比_{batch_start}-{batch_end}_报告.md")
            print(f"  [OK] 对比_{batch_start}-{batch_end}_AI分析.md")
        except Exception as e:
            print(f"  [FAIL] 第{batch_start}-{batch_end}章对比失败: {e}")

    print(f"\n对比报告 → {rewrites_dir}/compare/")
