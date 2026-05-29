# -*- coding: utf-8 -*-
"""
================================================================================
 注入框架抽象基类 + 智能分级重试计数器
================================================================================
"""

import time
from enum import Enum, auto
from dataclasses import dataclass


# ── 重试类别 ──

class RetryCategory(Enum):
    NETWORK = auto()         # 网络超时/API 限流 → 不扣核心额度
    CORE = auto()            # 指针未找到/Hook拒绝/写入失败 → 扣额度
    SUCCESS = auto()         # 成功


# ── 注入状态 ──

class InjectionState(Enum):
    IDLE = "idle"
    EXTRACTING = "extracting"
    TRANSLATING = "translating"
    INJECTING_NORMAL = "injecting_normal"       # 常规注入循环
    INJECTING_FORCE = "injecting_force"         # 强制注入
    DONE = "done"
    FATAL_ERROR = "fatal_error"


# ── 重试计数器 ──

@dataclass
class InjectionRetryCounter:
    """智能分级重试计数器"""
    max_core_retries: int = 10
    core_errors: int = 0
    network_retries: int = 0
    force_inject_triggered: bool = False
    last_error: str = ""
    _start_time: float = 0.0

    def record(self, category: RetryCategory, error_msg: str = "") -> bool:
        """
        记录一次结果。

        返回: True → 应触发 Force Inject
        """
        self.last_error = error_msg
        if category == RetryCategory.SUCCESS:
            self.reset()
            return False
        elif category == RetryCategory.CORE:
            self.core_errors += 1
            if self.core_errors >= self.max_core_retries:
                self.force_inject_triggered = True
                return True
        else:
            self.network_retries += 1
        return False

    def reset(self):
        self.core_errors = 0
        self.network_retries = 0
        self.force_inject_triggered = False
        self.last_error = ""


# ── 抽象基类 ──

class BaseInjector:
    """注入器抽象基类 — 定义状态机接口"""

    def __init__(self):
        self._counter = InjectionRetryCounter()
        self._state = InjectionState.IDLE
        self._on_state_change = None

    def set_state_callback(self, callback):
        """设置状态变更回调: callable(InjectionState, str)"""
        self._on_state_change = callback

    def _set_state(self, state: InjectionState, msg: str = ""):
        self._state = state
        if self._on_state_change:
            self._on_state_change(state, msg)

    @property
    def state(self) -> InjectionState:
        return self._state

    @property
    def retry_counter(self) -> InjectionRetryCounter:
        return self._counter

    @property
    def current_attempt(self) -> int:
        return self._counter.core_errors + 1

    def inject(self, project, **kwargs) -> dict:
        """子类必须实现"""
        raise NotImplementedError