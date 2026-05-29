# -*- coding: utf-8 -*-
"""
================================================================================
 强制内存注入器 — Force Inject Fallback
================================================================================
 当文件注入连续 10 次失败后激活。
 独立于常规注入器，直接操作目标进程内存。

 降级链:
   Phase 1: 内存扫描 + 暴力覆写
   Phase 2: 降级到文件注入（终极兜底）
   均失败 → FATAL_ERROR
================================================================================
"""

import os
import time
from engine.injector.base_injector import BaseInjector, InjectionState, RetryCategory
from engine.extractor.detector import TranslationProject
from engine.backup_manager import BackupManager
from utils.error_logger import log_exception
from utils.text_guard import TextGuard


class MemoryInjector(BaseInjector):
    """
    强制内存注入器。

    在独立后台线程中运行，绝不阻塞主 GUI。
    120 秒超时保护。
    """

    def __init__(self):
        super().__init__()
        self._pid: int = 0
        self._hProcess = None
        self._guard = None      # ProcessGuard 守护线程

    def inject(self, project: TranslationProject,
               pid: int = 0,
               on_progress=None,
               **kwargs) -> dict:
        """
        执行强制注入。

        参数:
            project: 翻译项目
            pid: 目标进程 ID（若游戏正在运行）
            on_progress: callable(phase, text) 进度回调
        返回:
            {"success": bool, "method": str, "written": int}
        """
        self._pid = pid
        self._set_state(InjectionState.INJECTING_FORCE,
                        "强制注入协议已激活")

        try:
            # 构建翻译映射
            translation_map = {}
            for entry in project.entries:
                target = entry.approved_text or entry.translated_text
                if target and not target.startswith("[翻译失败]"):
                    translation_map[entry.source_text] = target

            if not translation_map:
                self._counter.record(RetryCategory.CORE, "无有效翻译用于注入")
                return {"success": False, "method": "none", "error": "无有效翻译"}

            # ===== Phase 1: 内存扫描 + 暴力覆写 =====
            if on_progress:
                on_progress(1, "Phase 1/2: 内存文本扫描中...")

            scan_result = self._phase1_memory_scan(project, translation_map)

            if scan_result.get("written", 0) > 0:
                self._counter.record(RetryCategory.SUCCESS)
                self._set_state(InjectionState.DONE, "内存扫描注入成功")
                return scan_result

            # ===== Phase 2: 降级到文件注入 =====
            if on_progress:
                on_progress(2, "Phase 2/2: 内存扫描失败，降级到文件注入...")

            from engine.injector.file_injector import FileInjector
            file_inj = FileInjector()
            result = file_inj.inject(project, apply_corrections=True)

            if result.get("injected", 0) > 0:
                self._counter.record(RetryCategory.SUCCESS)
                self._set_state(InjectionState.DONE, "降级文件注入成功")
                return {"success": True, "method": "file_fallback",
                        "written": result["injected"]}

            # 全部失败
            self._counter.record(RetryCategory.CORE, "全部注入方案失败")
            self._set_state(InjectionState.FATAL_ERROR,
                            "所有注入方案均失败")
            return {"success": False, "method": "none",
                    "error": "Force Inject 失败：内存扫描 + 文件注入均无效"}

        except MemoryError as e:
            log_exception(e, "强制注入 - 内存不足")
            self._set_state(InjectionState.FATAL_ERROR, f"内存不足: {e}")
            return {"success": False, "method": "none", "error": str(e)}
        except PermissionError as e:
            log_exception(e, "强制注入 - 权限不足")
            self._set_state(InjectionState.FATAL_ERROR,
                            "权限不足，请以管理员身份运行")
            return {"success": False, "method": "none", "error": str(e)}
        except Exception as e:
            log_exception(e, "强制注入")
            self._set_state(InjectionState.FATAL_ERROR, str(e))
            return {"success": False, "method": "none", "error": str(e)}
        finally:
            self._cleanup()

    # ==================== Phase 1: 内存扫描 ====================

    def _phase1_memory_scan(self, project: TranslationProject,
                            translation_map: dict) -> dict:
        """
        扫描目标进程内存，暴力覆写文本。

        仅在 Windows 上可用（需 memory 包）。
        """
        # 如果没有 pid 或不在 Windows 上，直接跳过
        if not self._pid:
            return {"written": 0, "method": "no_pid"}

        try:
            from memory.memory_scanner import MemoryScanner
            from memory.winapi import (
                OpenProcess, CloseHandle, VirtualProtectEx,
                WriteProcessMemory, PROCESS_ALL_ACCESS,
                PAGE_EXECUTE_READWRITE,
            )

            hProcess = OpenProcess(PROCESS_ALL_ACCESS, False, self._pid)
            if not hProcess:
                return {"written": 0, "method": "open_failed"}

            self._hProcess = hProcess
            written = 0

            try:
                # 准备搜索模式
                patterns = [(k, k.encode("utf-8"))
                            for k in translation_map.keys() if len(k) >= 4]

                if not patterns:
                    return {"written": 0, "method": "no_patterns"}

                # 内存扫描
                scanner = MemoryScanner()
                results = scanner.scan_game_memory(self._pid, patterns)

                # 暴力覆写每个找到的地址
                for original, locations in results.items():
                    tgt_text = translation_map.get(original)
                    if not tgt_text:
                        continue
                    tgt_bytes = tgt_text.encode("utf-8")

                    for addr, src_len in locations:
                        try:
                            # 解锁页面保护
                            old_protect = __import__('ctypes').c_ulong()
                            region_size = max(len(tgt_bytes), src_len)
                            if VirtualProtectEx(
                                hProcess, addr, region_size,
                                PAGE_EXECUTE_READWRITE,
                                __import__('ctypes').byref(old_protect)
                            ):
                                # 写入译文
                                buf = (__import__('ctypes').c_char * len(tgt_bytes))()
                                buf[:] = tgt_bytes
                                _ = __import__('ctypes').c_size_t()
                                if WriteProcessMemory(
                                    hProcess, addr, buf,
                                    len(tgt_bytes),
                                    __import__('ctypes').byref(_)
                                ):
                                    written += 1
                        except Exception:
                            continue

            finally:
                CloseHandle(hProcess)
                self._hProcess = None

            return {"success": written > 0, "method": "memory_scan",
                    "written": written}

        except ImportError:
            # 非 Windows 或 memory 包不可用
            return {"written": 0, "method": "not_supported"}
        except Exception as e:
            log_exception(e, "内存扫描")
            return {"written": 0, "method": "exception", "error": str(e)}

    # ==================== 清理 ====================

    def _cleanup(self):
        """释放资源"""
        if self._guard:
            try:
                self._guard.stop()
            except Exception:
                pass
            self._guard = None
        self._hProcess = None