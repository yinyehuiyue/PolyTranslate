# -*- coding: utf-8 -*-
"""
================================================================================
 本地错误日志模块 — 零敏感内容
================================================================================
 仅记录异常类型 + 堆栈跟踪，绝不包含待翻译文本、API 返回内容、用户配置。
================================================================================
"""

import logging
import os
import sys

_logger = None


def setup_error_logger() -> logging.Logger:
    """
    配置错误日志。
    
    输出位置: 程序同目录下的 error.log
    内容: 仅时间戳 + 级别 + 异常类型 + 堆栈
    """
    global _logger
    if _logger is not None:
        return _logger

    log_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "error.log"
    )

    _logger = logging.getLogger("game_translator_v4")
    _logger.setLevel(logging.ERROR)

    # 避免重复添加 handler
    if _logger.handlers:
        return _logger

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s"
    ))
    _logger.addHandler(handler)

    return _logger


# ── 智能错误诊断映射 ──

_ERROR_DIAGNOSIS = {
    "PermissionError": (
        "权限不足",
        "请尝试以下操作:\n"
        "  1. 右键以管理员身份运行本程序\n"
        "  2. 暂时关闭杀毒软件 (Windows Defender/360等)\n"
        "  3. 将本程序添加到杀毒软件白名单"
    ),
    "MemoryError": (
        "内存不足",
        "请尝试以下操作:\n"
        "  1. 关闭其他占用内存的程序\n"
        "  2. 在设置中开启「安全兼容模式」"
    ),
    "OpenProcess": (
        "无法访问目标进程",
        "可能原因:\n"
        "  1. 游戏进程受反作弊系统保护 (EAC/BattlEye)\n"
        "  → 建议: 在设置中开启「安全兼容模式」\n"
        "  2. 需要管理员权限\n"
        "  → 建议: 右键以管理员身份运行"
    ),
    "WriteProcessMemory": (
        "内存写入被拒绝",
        "可能原因: 杀毒软件/反作弊拦截\n"
        "建议: 开启「安全兼容模式」或在杀毒软件中添加白名单"
    ),
    "VirtualProtectEx": (
        "内存保护修改被拒绝",
        "可能原因: 杀毒软件/反作弊拦截\n"
        "建议: 开启「安全兼容模式」或在杀毒软件中添加白名单"
    ),
    "scan_failed": (
        "内存扫描未找到文本",
        "可能原因:\n"
        "  1. 游戏使用了加密/压缩的文本存储\n"
        "  2. 游戏文本尚未加载到内存中\n"
        "  → 建议: 先进入游戏加载文本后再翻译，或使用文件注入模式"
    ),
    "api": (
        "API 请求失败",
        "可能原因:\n"
        "  1. Base URL 或 API Key 配置错误\n"
        "  2. 网络连接不稳定\n"
        "  3. API 服务商限流\n"
        "  → 建议: 检查设置中的 Base URL 和 API Key 是否正确"
    ),
    "rate_limit": (
        "API 请求被限流",
        "建议:\n"
        "  1. 等待 30 秒后重试\n"
        "  2. 降低翻译并发数\n"
        "  3. 使用本地模型避免限流"
    ),
    "ConnectionError": (
        "网络连接失败",
        "建议:\n"
        "  1. 检查网络连接是否正常\n"
        "  2. 检查 Base URL 是否可达\n"
        "  3. 本地模型请确认服务已启动 (LM Studio/Ollama)"
    ),
    "default": (
        "未知错误",
        "请将 error.log 发送给开发者协助排查。\n"
        "临时解决方案: 在设置中开启「安全兼容模式」后重试。"
    ),
}


def diagnose_error(exc_type: str, exc_msg: str = "") -> tuple:
    """
    根据异常类型返回 (简短标题, 详细排查建议)。

    参数:
        exc_type: 异常类名 (如 "PermissionError")
        exc_msg:  异常消息（用于匹配更细粒度）
    返回:
        (title, advice) 元组
    """
    combined = (exc_type + " " + exc_msg).lower()
    for key, (title, advice) in _ERROR_DIAGNOSIS.items():
        if key.lower() in combined:
            return (title, advice)
    return _ERROR_DIAGNOSIS["default"]


def log_exception(exc: Exception, context: str = ""):
    """
    安全记录异常（不包含数据内容）。

    参数:
        exc: 异常对象
        context: 操作描述（不含敏感数据），如 "文本提取"、"内存扫描"
    """
    logger = setup_error_logger()
    msg = f"{context} - {type(exc).__name__}"
    logger.error(msg, exc_info=True)