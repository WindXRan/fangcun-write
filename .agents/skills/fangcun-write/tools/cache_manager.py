"""集中式缓存管理器。

替代散落在各模块的 global 变量。提供 get_or_compute + clear 接口。
"""

import functools


class CacheManager:
    """线程安全（受限于 GIL）的内存缓存管理器。"""

    def __init__(self):
        self._caches = {}

    def get_or_compute(self, name: str, key, compute_fn, ttl=None):
        """获取或计算缓存值。

        Args:
            name: 缓存命名空间（如 "source_text", "style_fingerprint"）
            key: 缓存键（通常为 int 章号或 str prompt_type）
            compute_fn: 无参数可调用对象，值不存在时执行
            ttl: 存活秒数（None=永久）
        Returns:
            缓存的值
        """
        namespace = self._caches.setdefault(name, {})

        if ttl is not None:
            # 带 TTL 的缓存项存为 (value, expiry_time)
            import time
            entry = namespace.get(key)
            if entry is not None:
                val, expires = entry
                if time.monotonic() < expires:
                    return val

        if key in namespace:
            return namespace[key]

        result = compute_fn()
        if ttl is not None:
            import time
            namespace[key] = (result, time.monotonic() + ttl)
        else:
            namespace[key] = result
        return result

    def get(self, name: str, key=None):
        """直接读取缓存值。key=None 时返回整个命名空间。"""
        ns = self._caches.get(name, {})
        if key is None:
            return ns
        return ns.get(key)

    def set(self, name: str, key, value):
        """直接设置缓存值。"""
        self._caches.setdefault(name, {})[key] = value

    def clear(self, name=None):
        """清空缓存。name=None 清空全部。"""
        if name:
            self._caches.pop(name, None)
        else:
            self._caches.clear()

    def clear_by_key(self, name, key):
        """清空单条缓存。"""
        ns = self._caches.get(name)
        if ns:
            ns.pop(key, None)

    def stats(self):
        """返回缓存统计信息。"""
        return {name: len(ns) for name, ns in self._caches.items()}


# 全局单例
cache = CacheManager()
