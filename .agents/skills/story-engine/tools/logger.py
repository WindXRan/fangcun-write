"""日志模块：统一管理日志输出。"""

import sys
import logging
from pathlib import Path


class Logger:
    """统一日志管理器。"""
    
    def __init__(self, name="story-engine", log_file=None, level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            # 控制台handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_format = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)
            
            # 文件handler（可选）
            if log_file:
                self._setup_file_handler(log_file, level)
    
    def _setup_file_handler(self, log_file, level):
        """设置文件handler。"""
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_format = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
    
    def info(self, message):
        """普通信息。"""
        self.logger.info(message)
    
    def warning(self, message):
        """警告信息。"""
        self.logger.warning(message)
    
    def error(self, message):
        """错误信息。"""
        self.logger.error(message)
    
    def debug(self, message):
        """调试信息。"""
        self.logger.debug(message)
    
    def success(self, message):
        """成功信息（自定义级别）。"""
        self.logger.info(f"[OK] {message}")
    
    def fail(self, message):
        """失败信息（自定义级别）。"""
        self.logger.error(f"[FAIL] {message}")
    
    def progress(self, current, total, start_time, prefix=""):
        """进度信息。"""
        import time
        elapsed = time.time() - start_time
        speed = elapsed / current if current > 0 else 0
        eta = speed * (total - current)
        pct = current * 100 // total if total > 0 else 0
        bar = '=' * (pct // 5) + '>' + ' ' * (20 - pct // 5)
        self.logger.info(f"{prefix}[{current}/{total}] [{bar}] {pct}% | {elapsed:.0f}s | ETA {eta:.0f}s")
    
    def set_level(self, level):
        """设置日志级别。"""
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)


# 全局日志实例
_logger = None


def get_logger(name="story-engine", log_file=None, level=logging.INFO):
    """获取全局日志实例。"""
    global _logger
    if _logger is None:
        _logger = Logger(name, log_file, level)
    return _logger


def setup_logger(config):
    """根据配置设置日志。"""
    global _logger
    
    log_file = config.get("log_file")
    log_level = config.get("log_level", "INFO")
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    level = level_map.get(log_level.upper(), logging.INFO)
    
    _logger = Logger("story-engine", log_file, level)
    return _logger


# 便捷函数
def log_info(message):
    """记录普通信息。"""
    get_logger().info(message)


def log_warning(message):
    """记录警告信息。"""
    get_logger().warning(message)


def log_error(message):
    """记录错误信息。"""
    get_logger().error(message)


def log_success(message):
    """记录成功信息。"""
    get_logger().success(message)


def log_fail(message):
    """记录失败信息。"""
    get_logger().fail(message)


def log_progress(current, total, start_time, prefix=""):
    """记录进度信息。"""
    get_logger().progress(current, total, start_time, prefix)
