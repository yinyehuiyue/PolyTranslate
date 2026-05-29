# -*- coding: utf-8 -*-
"""
================================================================================
 内存文本扫描器 — Boyer-Moore-Horspool 字节序列搜索
================================================================================
 扫描目标进程的全部可读内存页，定位原文指针。
 支持 UTF-8 和 Shift-JIS 编码。
================================================================================
"""

import ctypes
from memory.winapi import (
    OpenProcess, CloseHandle, VirtualQueryEx, ReadProcessMemory,
    GetSystemInfo, SYSTEM_INFO, MEMORY_BASIC_INFORMATION,
    MEM_COMMIT, PAGE_READONLY, PAGE_READWRITE,
    PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE,
    PROCESS_VM_READ, PROCESS_QUERY_INFORMATION,
)


class MemoryScanner:
    """Boyer-Moore-Horspool 内存文本扫描器"""

    READABLE_PROTECTS = (
        PAGE_READONLY,
        PAGE_READWRITE,
        PAGE_EXECUTE_READ,
        PAGE_EXECUTE_READWRITE,
    )

    @staticmethod
    def _build_bad_char_table(pattern: bytes) -> dict:
        """构建 BMH 坏字符跳转表"""
        table = {}
        m = len(pattern)
        for i in range(m - 1):
            table[pattern[i]] = m - 1 - i
        return table

    @classmethod
    def search_in_buffer(cls, data: bytes, pattern: bytes,
                         base_addr: int) -> list:
        """
        在内存缓冲区中搜索模式字节序列。

        返回: [(绝对地址, 长度), ...]
        """
        results = []
        n = len(data)
        m = len(pattern)
        if m == 0 or n < m:
            return results

        bad_char = cls._build_bad_char_table(pattern)
        i = 0
        while i <= n - m:
            j = m - 1
            while j >= 0 and data[i + j] == pattern[j]:
                j -= 1
            if j < 0:
                results.append((base_addr + i, m))
                i += 1
            else:
                shift = bad_char.get(data[i + j], m)
                i += max(1, shift)
        return results

    @classmethod
    def scan_game_memory(cls, pid: int,
                         patterns: list) -> dict:
        """
        扫描目标进程的全部可读内存页。

        参数:
            pid: 目标进程 ID
            patterns: [(key, utf8_bytes), ...] 要搜索的文本
        返回:
            {key: [(address, length), ...]}
        """
        hProcess = OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid
        )
        if not hProcess:
            return {}

        results = {}
        try:
            si = SYSTEM_INFO()
            GetSystemInfo(ctypes.byref(si))
            min_addr = si.lpMinimumApplicationAddress
            max_addr = si.lpMaximumApplicationAddress

            mbi = MEMORY_BASIC_INFORMATION()
            addr = min_addr

            while addr < max_addr:
                ret = VirtualQueryEx(
                    hProcess, addr, ctypes.byref(mbi),
                    ctypes.sizeof(mbi)
                )
                if ret == 0:
                    addr += 0x10000
                    continue

                if (mbi.State == MEM_COMMIT and
                        mbi.Protect in cls.READABLE_PROTECTS):
                    region_size = min(mbi.RegionSize, 64 * 1024)
                    buf = (ctypes.c_char * region_size)()
                    bytes_read = ctypes.c_size_t()

                    if ReadProcessMemory(hProcess, addr, buf,
                                         region_size,
                                         ctypes.byref(bytes_read)):
                        data = bytes(buf[:bytes_read.value])
                        for key, pattern_bytes in patterns:
                            found = cls.search_in_buffer(
                                data, pattern_bytes, addr
                            )
                            if found:
                                results.setdefault(key, []).extend(found)

                addr += mbi.RegionSize
        finally:
            CloseHandle(hProcess)

        return results