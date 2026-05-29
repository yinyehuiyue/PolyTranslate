# -*- coding: utf-8 -*-
"""
================================================================================
 安全守卫工具
================================================================================
 提供本地/云端检测、隐私徽章、内存清理等安全相关功能。
 五大安全防护机制的代码级实现。
================================================================================
"""

import gc
import atexit
from urllib.parse import urlparse
from typing import Callable

# ==================== 本地/云端检测 ====================

_LOCAL_HOST_PREFIXES = (
    "localhost",
    "127.",
    "192.168.",
    "10.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "[::1]",
    "0.0.0.0",
)


def is_local_endpoint(base_url: str) -> bool:
    """
    检测 Base URL 是否指向本机/局域网。

    参数:
        base_url: 完整的 Base URL 字符串
    返回:
        True 表示指向本地地址
    """
    if not base_url:
        return True  # 空 URL 默认视为本地
    try:
        host = urlparse(base_url).hostname or ""
        return any(host.startswith(prefix) for prefix in _LOCAL_HOST_PREFIXES)
    except Exception:
        return False


def get_privacy_badge(base_url: str) -> tuple:
    """
    获取隐私状态徽章信息。

    参数:
        base_url: Base URL 字符串
    返回:
        (徽章文本, 前景色, 背景色)
    """
    if is_local_endpoint(base_url):
        return (
            "🔒 本地离线模式 · 数据不出本机",
            "#2E7D32",
            "#E8F5E9",
        )
    else:
        return (
            "🌐 云端模式 · 文本将发送至远程服务器",
            "#E65100",
            "#FFF3E0",
        )


# ==================== 内存清理 ====================

class MemoryGuard:
    """
    内存守卫：追踪敏感变量，退出时自动清理。

    用法:
        guard = MemoryGuard()
        guard.track(my_sensitive_dict)
        # ... 程序结束时自动调用 guard._cleanup()
    """

    def __init__(self, on_cleanup: Callable = None):
        self._tracked = []
        self._on_cleanup = on_cleanup
        atexit.register(self._cleanup)

    def track(self, obj):
        """
        注册需要退出时清理的对象（如 dict, list, str）。

        参数:
            obj: 任意 Python 对象
        """
        self._tracked.append(obj)

    def _cleanup(self):
        """退出时清理所有被追踪的变量"""
        for obj in self._tracked:
            try:
                if hasattr(obj, "clear"):
                    obj.clear()
                elif isinstance(obj, list):
                    obj[:] = []
                elif isinstance(obj, str):
                    # 不可变对象，用 del 清除引用
                    pass
            except Exception:
                pass
        self._tracked.clear()
        # 强制垃圾回收
        gc.collect()
        if self._on_cleanup:
            self._on_cleanup()


# ==================== API Key 掩码 ====================

def mask_api_key(key: str) -> str:
    """
    对 API Key 进行掩码处理，仅显示首尾部分。

    参数:
        key: 明文 API Key
    返回:
        掩码后的字符串，如 "sk-a***b1c2"
    """
    if not key:
        return "（未设置）"
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * min(len(key) - 8, 12) + key[-4:]


# ==================== 模块自检 ====================

if __name__ == "__main__":
    # 本地/云端检测测试
    test_urls = [
        "http://localhost:1234/v1",
        "http://127.0.0.1:11434/v1",
        "https://api.deepseek.com",
        "http://192.168.1.100:8080/v1",
        "",
    ]
    for url in test_urls:
        badge = get_privacy_badge(url)
        is_local = is_local_endpoint(url)
        print(f"URL: {url:45s}  本地: {is_local}  徽章: {badge[0][:20]}...")

    # 掩码测试
    print(f"\nAPI Key 掩码测试:")
    print(f"  sk-a1b2c3d4e5f6g7h8i9j0  →  {mask_api_key('sk-a1b2c3d4e5f6g7h8i9j0')}")
    print(f"  short                   →  {mask_api_key('short')}")
    print(f"  (空)                    →  {mask_api_key('')}")