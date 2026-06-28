"""
pipeline 执行器 — 按 XML 定义编排多工具流程。

用户可自创 pipeline 文件，放在 pipelines/ 或内置在 builtin/ 下。

pipeline XML 格式：
<pipeline name="拆书逆推">
  <desc>导入章节 → 逆推套路 → 逆推总纲 → 逆推卷纲</desc>
  <step tool="book-import-raw" id="import">
    <param name="source" from="input.source" />
    <param name="book_name" from="input.book_name" />
    <param name="author" from="input.author" />
  </step>
  <step tool="pattern-analysis" id="pattern">
    <param name="ch" value="1" />
    <param name="源文对照" from="results.import.chapter_1" />
  </step>
  <step tool="book-import" id="outline">
    <param name="book_name" from="input.book_name" />
    <param name="total_chapters" from="results.import.total" />
  </step>
  <step tool="volume-outline" id="volumes">
    <param name="total_chapters" from="results.import.total" />
  </step>
</pipeline>
"""
import os, sys, json, xml.etree.ElementTree as ET
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BUILTIN = _HERE / "builtin"
_PIPELINES = _HERE / "pipelines"


def _resolve_value(spec: str, ctx: dict):
    """解析参数值。支持 from="input.xxx" / from="results.step_id.xxx" / value="xxx" """
    if spec.startswith("input."):
        key = spec[6:]
        return ctx.get("input", {}).get(key, "")
    if spec.startswith("results."):
        parts = spec[8:].split(".", 1)
        if len(parts) == 2:
            step_id, key = parts
            return ctx.get("results", {}).get(step_id, {}).get(key, "")
    return spec


def run_pipeline(pipeline_name: str, input_data: dict, project_dir: str) -> str:
    """运行 pipeline。"""
    from tool_executor import run_tool

    # 找 pipeline 定义
    pipeline_file = _BUILTIN / f"{pipeline_name}.xml"
    if not pipeline_file.exists():
        pipeline_file = _PIPELINES / f"{pipeline_name}.xml"
    if not pipeline_file.exists():
        return f"pipeline 不存在: {pipeline_name}"

    tree = ET.parse(pipeline_file)
    root = tree.getroot()
    if root.tag != "pipeline":
        return f"根元素必须是 <pipeline>，实际是 <{root.tag}>"

    name = root.get("name", pipeline_name)
    steps = root.findall("step")
    if not steps:
        return f"pipeline '{name}' 没有定义任何步骤"

    ctx = {
        "input": input_data,
        "results": {},
        "project_dir": project_dir,
    }

    logs = [f"▶ 运行 pipeline: {name}"]

    for step in steps:
        tool_name = step.get("tool", "")
        step_id = step.get("id", tool_name)
        if not tool_name:
            logs.append(f"  ✗ 步骤缺少 tool 属性")
            continue

        # 构建参数
        args = {}
        for param in step.findall("param"):
            p_name = param.get("name", "")
            if not p_name:
                continue
            # from 引用
            from_spec = param.get("from", "")
            if from_spec:
                args[p_name] = _resolve_value(from_spec, ctx)
            # 直接值
            value = param.get("value", "")
            if value:
                args[p_name] = value

        logs.append(f"  → {tool_name}（{step_id}）")

        result = run_tool(tool_name, args, project_dir)
        logs.append(f"    {result[:80]}")

        # 保存步骤结果
        ctx["results"][step_id] = {
            "output": result,
            "project_dir": project_dir,
        }

    logs.append(f"✓ pipeline 完成")
    return "\n".join(logs)


# ─── CLI ───

def main():
    import argparse
    parser = argparse.ArgumentParser(description="fangcun pipeline 执行器")
    parser.add_argument("pipeline", help="pipeline 名称")
    parser.add_argument("--book", default="", help="书名")
    parser.add_argument("--source", default="", help="源路径")
    parser.add_argument("--author", default="", help="作者")
    parser.add_argument("--project-dir", default=None, help="项目目录")
    args = parser.parse_args()

    input_data = {
        "book_name": args.book,
        "source": args.source,
        "author": args.author,
    }
    result = run_pipeline(args.pipeline, input_data, args.project_dir or ".")
    print(result)


if __name__ == "__main__":
    main()
