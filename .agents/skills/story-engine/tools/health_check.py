"""健康检查和诊断工具：检查项目状态，发现潜在问题。"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加路径
current_dir = str(Path(__file__).parent)
sys.path.insert(0, current_dir)

from state_manager import StateManager
from utils import validate_config, get_chapters_list, get_cache_stats
from logger import get_logger


class HealthChecker:
    """项目健康检查器。"""
    
    def __init__(self, config):
        self.config = config
        self.rewrites_dir = config.get("rewrites_dir", "")
        self.logger = get_logger()
        self.issues = []
        self.warnings = []
        self.info = []
    
    def add_issue(self, level, message, details=None):
        """添加问题。"""
        item = {"level": level, "message": message, "details": details}
        if level == "error":
            self.issues.append(item)
        elif level == "warning":
            self.warnings.append(item)
        else:
            self.info.append(item)
    
    def check_config(self):
        """检查配置完整性。"""
        self.logger.info("检查配置...")
        
        errors = validate_config(self.config)
        if errors:
            for e in errors:
                self.add_issue("error", f"配置错误: {e}")
        else:
            self.add_issue("info", "配置验证通过")
        
        # 检查目录是否存在
        rewrites_dir = Path(self.rewrites_dir)
        if not rewrites_dir.exists():
            self.add_issue("warning", f"仿写目录不存在: {rewrites_dir}")
        else:
            self.add_issue("info", f"仿写目录存在: {rewrites_dir}")
    
    def check_state(self):
        """检查状态文件。"""
        self.logger.info("检查状态文件...")
        
        if not self.rewrites_dir:
            self.add_issue("warning", "未配置 rewrites_dir，跳过状态检查")
            return
        
        state_mgr = StateManager(self.rewrites_dir)
        state_mgr.load()
        
        # 检查章节状态
        completed = state_mgr.get_completed_chapters()
        failed = state_mgr.get_failed_chapters()
        
        self.add_issue("info", f"已完成章节: {len(completed)}")
        self.add_issue("info", f"失败章节: {len(failed)}")
        
        if failed:
            self.add_issue("warning", f"有 {len(failed)} 章失败: {failed[:10]}...")
        
        # 检查阶段状态
        phases = state_mgr.state.get("phases", {})
        for phase, info in phases.items():
            status = info.get("status", "unknown")
            self.add_issue("info", f"阶段 {phase}: {status}")
    
    def check_files(self):
        """检查文件完整性。"""
        self.logger.info("检查文件...")
        
        if not self.rewrites_dir:
            return
        
        rewrites_path = Path(self.rewrites_dir)
        
        # 检查核心文件
        core_files = [
            ("concept.md", "设定文件"),
            ("guides/", "指南目录"),
            ("chapters/", "章节目录"),
        ]
        
        for file_path, desc in core_files:
            full_path = rewrites_path / file_path
            if full_path.exists():
                if full_path.is_dir():
                    count = len(list(full_path.glob("*")))
                    self.add_issue("info", f"{desc}存在: {count} 个文件")
                else:
                    self.add_issue("info", f"{desc}存在")
            else:
                self.add_issue("warning", f"{desc}不存在: {full_path}")
        
        # 检查章节文件
        chapters_dir = rewrites_path / "chapters"
        if chapters_dir.exists():
            chapter_files = sorted(chapters_dir.glob("ch_*.txt"))
            self.add_issue("info", f"章节数量: {len(chapter_files)}")
            
            # 检查章节大小
            empty_chapters = []
            small_chapters = []
            for ch_file in chapter_files:
                size = ch_file.stat().st_size
                if size == 0:
                    empty_chapters.append(ch_file.name)
                elif size < 1000:  # 小于1KB
                    small_chapters.append(ch_file.name)
            
            if empty_chapters:
                self.add_issue("warning", f"空章节: {empty_chapters[:5]}...")
            if small_chapters:
                self.add_issue("warning", f"过小章节: {small_chapters[:5]}...")
    
    def check_cache(self):
        """检查缓存状态。"""
        self.logger.info("检查缓存...")
        
        try:
            stats = get_cache_stats(self.config)
            self.add_issue("info", f"内存缓存: {stats['memory']} 章")
        except Exception as e:
            self.add_issue("warning", f"缓存检查失败: {e}")
    
    def check_source(self):
        """检查源文可访问性。"""
        self.logger.info("检查源文...")
        
        from utils import get_source_text, get_total_chapters
        
        try:
            total = get_total_chapters(self.config)
            self.add_issue("info", f"源文总章数: {total}")
            
            # 测试读取第一章
            if total > 0:
                text = get_source_text(self.config, 1)
                if text:
                    self.add_issue("info", f"源文第一章可读: {len(text)} 字符")
                else:
                    self.add_issue("error", "源文第一章读取失败")
        except Exception as e:
            self.add_issue("error", f"源文检查失败: {e}")
    
    def check_api(self):
        """检查 API 连接。"""
        self.logger.info("检查 API 连接...")
        
        from lib.api_client import test_api_connection
        
        result = test_api_connection(self.config, timeout=10)
        
        if result["success"]:
            self.add_issue("info", f"API 连接成功: {result['url']}")
            self.add_issue("info", f"模型: {result['model']}")
            self.add_issue("info", f"延迟: {result['latency_ms']}ms")
        else:
            self.add_issue("error", f"API 连接失败: {result['error']}")
            self.add_issue("info", f"URL: {result['url']}")
            self.add_issue("info", f"模型: {result['model']}")
    
    def run_all_checks(self):
        """运行所有检查。"""
        self.logger.info("=" * 50)
        self.logger.info("开始健康检查")
        self.logger.info("=" * 50)
        
        self.check_config()
        self.check_state()
        self.check_files()
        self.check_cache()
        self.check_source()
        self.check_api()
        
        return self.generate_report()
    
    def generate_report(self):
        """生成检查报告。"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "book_name": self.config.get("book_name", ""),
                "author": self.config.get("author", ""),
                "source_book": self.config.get("source_book", ""),
            },
            "summary": {
                "errors": len(self.issues),
                "warnings": len(self.warnings),
                "info": len(self.info),
            },
            "issues": self.issues,
            "warnings": self.warnings,
            "info": self.info,
        }
        
        # 打印摘要
        self.logger.info("\n" + "=" * 50)
        self.logger.info("检查结果摘要")
        self.logger.info("=" * 50)
        
        if self.issues:
            self.logger.error(f"错误: {len(self.issues)}")
            for issue in self.issues:
                self.logger.error(f"  - {issue['message']}")
        
        if self.warnings:
            self.logger.warning(f"警告: {len(self.warnings)}")
            for warning in self.warnings:
                self.logger.warning(f"  - {warning['message']}")
        
        self.logger.info(f"信息: {len(self.info)}")
        
        if not self.issues and not self.warnings:
            self.logger.success("所有检查通过！")
        
        return report


def run_health_check(config, output_file=None):
    """运行健康检查并保存报告。"""
    checker = HealthChecker(config)
    report = checker.run_all_checks()
    
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"报告已保存: {output_path}")
    
    return report


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="项目健康检查")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--output", help="报告输出文件")
    
    args = parser.parse_args()
    
    # 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)
    
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.setdefault("base_dir", os.getcwd())
    
    # 运行检查
    run_health_check(config, args.output)
