# -*- coding: utf-8 -*-
"""
================================================================================
 进程守护 + 自毁清理
================================================================================
 500ms 轮询目标进程，退出时执行 UnhookAll + VirtualFreeEx + CloseHandle。
================================================================================
"""

import ctypes
import threading
import time
from memory.winapi import (
    OpenProcess, CloseHandle, VirtualFreeEx, WaitForSingleObject,
    SYNCHRONIZE, WAIT_OBJECT_0, INFINITE,
)


class ProcessGuard:
    """
    进程守护线程。

    监控目标进程存活状态。
    进程退出 → 自动执行清理回调。
    """

    def __init__(self, pid: int, on_exit=None):
        """
        参数:
            pid: 目标进程 ID
            on_exit: callable() — 进程退出时的清理回调
        """
        self._pid = pid
        self._on_exit = on_exit or (lambda: None)
        self._running = False
        self._hProcess = None
        self._injected_regions = []      # [(addr, size), ...]
        self._thread = None

    def track_allocation(self, addr: int, size: int):
        """记录已分配的内存区域，供清理时使用"""
        self._injected_regions.append((addr, size))

    def start(self, interval_ms: int = 500):
        """
        启动守护线程。

        参数:
            interval_ms: 轮询间隔（毫秒）
        """
        if self._running:
            return
        self._running = True

        self._hProcess = OpenProcess(SYNCHRONIZE, False, self._pid)
        self._thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_ms / 1000.0,),
            daemon=True,
        )
        self._thread.start()

    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self._running:
            if self._hProcess:
                ret = WaitForSingleObject(self._hProcess, 0)
                if ret == WAIT_OBJECT_0:
                    # 进程已退出
                    self._running = False
                    self._cleanup()
                    self._on_exit()
                    break
            time.sleep(interval)

    def _cleanup(self):
        """自毁清理 — 释放所有注入的内存"""
        for addr, size in self._injected_regions:
            try:
                VirtualFreeEx(self._hProcess, addr, size, 0x8000)  # MEM_RELEASE
            except Exception:
                pass
        self._injected_regions.clear()

        if self._hProcess:
            try:
                CloseHandle(self._hProcess)
            except Exception:
                pass
            self._hProcess = None

    def stop(self):
        """手动停止守护"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._cleanup()