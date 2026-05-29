# -*- coding: utf-8 -*-
"""
================================================================================
 通用重试工具
================================================================================
 提供装饰器和函数形式的通用重试机制，消除各处重复的 try/except。
 用于: API 调用、文件写入等易失败操作。
================================================================================
"""

import time
import functools
from typing import Callable, Type, Tuple


def retry_on_failure(
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] = None,
):
    """
    通用重试装饰器。

    参数:
        max_retries: 最大重试次数（含首次执行）
        base_delay: 基础等待秒数（第 n 次重试等待 base_delay * n 秒）
        retryable_exceptions: 可重试的异常类型元组
        on_retry: 每次重试前的回调 (attempt, exception) -> None

    用法:
        @retry_on_failure(max_retries=3, on_retry=lambda a,e: print(f"重试{a}: {e}"))
        def unstable_api_call():
            ...
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * attempt
                        if on_retry:
                            on_retry(attempt, e)
                        time.sleep(delay)
            raise last_exception  # 所有重试均失败

        return wrapper

    return decorator


def retry_call(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs,
):
    """
    函数式重试调用（不需要装饰器时使用）。

    参数:
        func: 待调用的函数
        *args, **kwargs: 传给 func 的参数
        max_retries: 最大重试次数
        base_delay: 基础等待秒数

    返回:
        func 的返回值（若成功）

    抛出:
        最后一次的异常（若全部重试失败）
    """
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                time.sleep(base_delay * attempt)
    raise last_exception