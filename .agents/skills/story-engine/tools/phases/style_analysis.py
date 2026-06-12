"""Phase 1.5: 风格分析（脚本，自动提取源文指标）"""

import subprocess
from pathlib import Path


def phase_style_analysis(config, state_mgr=None):
    """运行 style_analyzer.py 提取源文风格指标。"""
    print("\n" + "=" * 50)
    print("Phase 1.5: 风格分析 (脚本)")
    print("=" * 50)

    if state_mgr:
        if state_mgr.is_phase_done("style-analysis"):
            print("风格分析已完成，跳过")
            return True
        state_mgr.phase_start("style-analysis")

    # 源文目录
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    src_dir = Path("projects") / author / source_book / "_cache" / "chapters"
    if not src_dir.exists():
        print(f"  [WARN] 源文目录不存在: {src_dir}，跳过风格分析")
        return False

    # 输出目录
    rewrites_dir = Path(config["rewrites_dir"])
    out_dir = rewrites_dir.parent / "style_analysis"

    # 脚本路径
    script = Path(__file__).parent.parent.parent.parent / "tools" / "style_analyzer.py"
    if not script.exists():
        # 尝试项目根目录
        script = Path("tools") / "style_analyzer.py"
    if not script.exists():
        print(f"  [WARN] style_analyzer.py 不存在，跳过风格分析")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(script), str(src_dir), str(out_dir)],
            capture_output=True, text=True, timeout=120, encoding='utf-8'
        )
        if result.returncode == 0:
            # 只打印关键行
            for line in result.stdout.strip().split('\n'):
                if '已分析' in line or '均值' in line or 'JSON' in line:
                    print(f"  {line.strip()}")
            if state_mgr:
                state_mgr.phase_done("style-analysis")
            return True
        else:
            print(f"  [FAIL] style_analyzer.py 出错: {result.stderr[:200]}")
            if state_mgr:
                state_mgr.phase_failed("style-analysis", error=result.stderr[:200])
            return False
    except subprocess.TimeoutExpired:
        print("  [FAIL] style_analyzer.py 超时")
        if state_mgr:
            state_mgr.phase_failed("style-analysis", error="超时")
        return False
    except Exception as e:
        print(f"  [FAIL] {e}")
        if state_mgr:
            state_mgr.phase_failed("style-analysis", error=str(e))
        return False
