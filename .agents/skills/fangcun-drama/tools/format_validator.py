"""
剧本格式校验器 — 自动检测格式违规。

用法:
    python format_validator.py <file_or_dir> [--fix] [--json]

检查项:
    1. △行代称（他/她开头）
    2. 对话行括号（动作/神态描述混入对话行）
    3. 破折号（——在剧本正文中）
    4. △行冒号引入主观感知（应拆成OS）
    5. 场景数（每集≤4）
    6. OS长度（每段≤15字）
"""

import re
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict


@dataclass
class Issue:
    file: str
    line: int
    category: str
    severity: str  # error / warning
    message: str
    content: str


@dataclass
class Report:
    file: str
    issues: list = field(default_factory=list)
    scene_count: int = 0

    @property
    def error_count(self):
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self):
        return sum(1 for i in self.issues if i.severity == "warning")


def is_in_summary(line_idx: int, lines: list) -> bool:
    """检查当前行是否在剧情梗概区域内。"""
    in_summary = False
    for i in range(line_idx):
        if lines[i].strip().startswith("###"):
            in_summary = True
        elif lines[i].strip() == "---" and in_summary:
            in_summary = False
    return in_summary


def validate_file(filepath: Path) -> Report:
    """校验单个剧本文件。"""
    report = Report(file=str(filepath))
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")

    # 统计场景数
    scene_pattern = re.compile(r"^\d+-\d+\s")
    report.scene_count = sum(1 for line in lines if scene_pattern.match(line.strip()))

    if report.scene_count > 4:
        report.issues.append(Issue(
            file=str(filepath),
            line=0,
            category="scene_count",
            severity="error",
            message=f"场景数 {report.scene_count} 超过4个，建议合并",
            content=f"共 {report.scene_count} 个场景"
        ))

    in_summary = False
    in_script = False

    for idx, line in enumerate(lines):
        stripped = line.strip()
        line_num = idx + 1

        # 跟踪剧情梗概区域
        if stripped.startswith("###"):
            in_summary = True
            continue
        if stripped == "---" and in_summary:
            in_summary = False
            continue

        # 跟踪剧本正文区域（第一个场景头之后）
        if scene_pattern.match(stripped):
            in_script = True

        if not in_script or in_summary:
            continue

        # === 检查1: △行代称 ===
        if stripped.startswith("△"):
            # 检查△后面是否紧跟代称
            after_delta = stripped[1:].lstrip()
            if re.match(r"^[他她它他们她们它们她们我们你们]", after_delta):
                report.issues.append(Issue(
                    file=str(filepath),
                    line=line_num,
                    category="pronoun",
                    severity="error",
                    message="△行禁用代称，必须用角色全名",
                    content=stripped
                ))

        # === 检查2: 对话行括号 ===
        if not stripped.startswith("△") and not stripped.startswith("#") and not stripped.startswith("【"):
            # 匹配 "人物名（动作/神态）：" 模式
            if re.match(r"^[^△#].*[：:]", stripped) and "（" in stripped and "）" in stripped:
                # 排除OS行和场景头
                if "OS：" not in stripped and "OS:" not in stripped:
                    # 排除人物行（场景头下面的 人物：xxx）
                    if not stripped.startswith("人物：") and not stripped.startswith("人物:"):
                        # 排除（画外）标记
                        cleaned = re.sub(r"（画外）", "", stripped)
                        cleaned = re.sub(r"（画外音）", "", cleaned)
                        if "（" in cleaned and "）" in cleaned:
                            report.issues.append(Issue(
                                file=str(filepath),
                                line=line_num,
                                category="parenthetical",
                                severity="error",
                                message="对话行禁止括号动作/神态，应拆到△行",
                                content=stripped
                            ))

        # === 检查3: 破折号 ===
        if not in_summary and "——" in stripped:
            # 排除剧情梗概行
            if not stripped.startswith("###"):
                report.issues.append(Issue(
                    file=str(filepath),
                    line=line_num,
                    category="dash",
                    severity="warning",
                    message="剧本正文禁用破折号（——），用句号/逗号/冒号替换",
                    content=stripped
                ))

        # === 检查4: △行冒号引入主观感知 ===
        if stripped.startswith("△") and "：" in stripped:
            # 找到△后的冒号位置
            delta_content = stripped[1:]
            colon_match = re.search(r"[：:]", delta_content)
            if colon_match:
                before_colon = delta_content[:colon_match.start()].strip()
                after_colon = delta_content[colon_match.end():].strip()

                # 排除外部声音模式（"远处传来声音：xxx"、"外面传来xxx"）
                external_sound = re.search(
                    r"传来|画外|外面|远处|隔壁|收音机|播音员|广播",
                    before_colon
                )
                if not external_sound:
                    # 排除OS行（△王全发一愣。王全发OS：xxx）
                    if "OS：" not in stripped and "OS:" not in stripped:
                        report.issues.append(Issue(
                            file=str(filepath),
                            line=line_num,
                            category="colon_in_delta",
                            severity="error",
                            message="△行冒号后是主观感知，应拆成△动作+OS",
                            content=stripped
                        ))

        # === 检查5: OS长度 ===
        if "OS：" in stripped or "OS:" in stripped:
            # 提取OS内容
            os_match = re.search(r"OS[：:](.+)", stripped)
            if os_match:
                os_content = os_match.group(1).strip()
                # 去掉标点算字数
                cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", os_content))
                if cjk_chars > 15:
                    report.issues.append(Issue(
                        file=str(filepath),
                        line=line_num,
                        category="os_too_long",
                        severity="warning",
                        message=f"OS内容过长（{cjk_chars}字），建议≤10字，情绪变化应加新动作+新OS",
                        content=stripped
                    ))

    return report


def validate_directory(dirpath: Path) -> list:
    """校验目录下所有剧本文件。"""
    reports = []
    for f in sorted(dirpath.glob("ep_*.txt")):
        reports.append(validate_file(f))
    return reports


def print_report(report: Report, use_json: bool = False):
    """打印校验报告。"""
    if use_json:
        data = {
            "file": report.file,
            "scene_count": report.scene_count,
            "errors": report.error_count,
            "warnings": report.warning_count,
            "issues": [asdict(i) for i in report.issues]
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not report.issues:
        print(f"  ✅ {Path(report.file).name} — 无违规")
        return

    print(f"\n  📄 {Path(report.file).name} ({report.scene_count} 场景)")
    for issue in report.issues:
        icon = "🔴" if issue.severity == "error" else "🟡"
        line_str = f"L{issue.line}" if issue.line else ""
        print(f"    {icon} [{issue.category}] {line_str}: {issue.message}")
        if issue.content:
            # 截断显示
            display = issue.content[:80] + ("..." if len(issue.content) > 80 else "")
            print(f"       {display}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="剧本格式校验器")
    parser.add_argument("path", help="文件或目录路径")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--quiet", action="store_true", help="只输出汇总")
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"路径不存在: {target}")
        sys.exit(1)

    if target.is_file():
        reports = [validate_file(target)]
    else:
        reports = validate_directory(target)

    total_errors = sum(r.error_count for r in reports)
    total_warnings = sum(r.warning_count for r in reports)

    if args.json:
        all_data = {
            "total_files": len(reports),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "files": []
        }
        for r in reports:
            all_data["files"].append({
                "file": Path(r.file).name,
                "scene_count": r.scene_count,
                "errors": r.error_count,
                "warnings": r.warning_count,
                "issues": [asdict(i) for i in r.issues]
            })
        print(json.dumps(all_data, ensure_ascii=False, indent=2))
        return

    print("=== 剧本格式校验 ===")
    for r in reports:
        if args.quiet:
            if r.issues:
                print(f"  {Path(r.file).name}: {r.error_count} errors, {r.warning_count} warnings")
        else:
            print_report(r)

    print(f"\n{'='*40}")
    if total_errors == 0 and total_warnings == 0:
        print(f"✅ 全部 {len(reports)} 个文件通过校验")
    else:
        print(f"❌ {len(reports)} 个文件: {total_errors} 个错误, {total_warnings} 个警告")

    sys.exit(1 if total_errors > 0 else 0)


if __name__ == "__main__":
    main()
