# -*- coding: utf-8 -*-
"""
================================================================================
 Windows API 封装 (ctypes)
================================================================================
 提供进程操作、内存操作所需的所有 Win32 API 声明。
 仅在 Windows 平台上可用。
================================================================================
"""

import ctypes
from ctypes import wintypes

# ── 常量 ──

PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
SYNCHRONIZE = 0x00100000

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000

PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

TH32CS_SNAPTHREAD = 0x00000004

WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
INFINITE = 0xFFFFFFFF

# ── 结构体 ──

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]

class SYSTEM_INFO(ctypes.Structure):
    _fields_ = [
        ("wProcessorArchitecture", wintypes.WORD),
        ("wReserved", wintypes.WORD),
        ("dwPageSize", wintypes.DWORD),
        ("lpMinimumApplicationAddress", ctypes.c_void_p),
        ("lpMaximumApplicationAddress", ctypes.c_void_p),
        ("dwActiveProcessorMask", ctypes.c_ulonglong),
        ("dwNumberOfProcessors", wintypes.DWORD),
        ("dwProcessorType", wintypes.DWORD),
        ("dwAllocationGranularity", wintypes.DWORD),
        ("wProcessorLevel", wintypes.WORD),
        ("wProcessorRevision", wintypes.WORD),
    ]

class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", wintypes.LONG),
        ("tpDeltaPri", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
    ]

# ── Kernel32 函数声明 ──

_kernel32 = ctypes.windll.kernel32

OpenProcess = _kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

CloseHandle = _kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

VirtualAllocEx = _kernel32.VirtualAllocEx
VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                            wintypes.DWORD, wintypes.DWORD]
VirtualAllocEx.restype = ctypes.c_void_p

VirtualFreeEx = _kernel32.VirtualFreeEx
VirtualFreeEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                           wintypes.DWORD]
VirtualFreeEx.restype = wintypes.BOOL

VirtualProtectEx = _kernel32.VirtualProtectEx
VirtualProtectEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                              wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
VirtualProtectEx.restype = wintypes.BOOL

ReadProcessMemory = _kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                               ctypes.c_void_p, ctypes.c_size_t,
                               ctypes.POINTER(ctypes.c_size_t)]
ReadProcessMemory.restype = wintypes.BOOL

WriteProcessMemory = _kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                ctypes.c_void_p, ctypes.c_size_t,
                                ctypes.POINTER(ctypes.c_size_t)]
WriteProcessMemory.restype = wintypes.BOOL

VirtualQueryEx = _kernel32.VirtualQueryEx
VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                            ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                            ctypes.c_size_t]
VirtualQueryEx.restype = ctypes.c_size_t

GetSystemInfo = _kernel32.GetSystemInfo
GetSystemInfo.argtypes = [ctypes.POINTER(SYSTEM_INFO)]
GetSystemInfo.restype = None

CreateToolhelp32Snapshot = _kernel32.CreateToolhelp32Snapshot
CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
CreateToolhelp32Snapshot.restype = wintypes.HANDLE

Thread32First = _kernel32.Thread32First
Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
Thread32First.restype = wintypes.BOOL

Thread32Next = _kernel32.Thread32Next
Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
Thread32Next.restype = wintypes.BOOL

WaitForSingleObject = _kernel32.WaitForSingleObject
WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
WaitForSingleObject.restype = wintypes.DWORD

QueueUserAPC = _kernel32.QueueUserAPC
QueueUserAPC.argtypes = [ctypes.c_void_p, wintypes.HANDLE, wintypes.ULONG_PTR]
QueueUserAPC.restype = wintypes.DWORD

# ── EnumerateProcessModules (psapi) ──

_psapi = ctypes.windll.psapi
EnumProcessModules = _psapi.EnumProcessModules
EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE),
                                wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
EnumProcessModules.restype = wintypes.BOOL

GetModuleFileNameExW = _psapi.GetModuleFileNameExW
GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE,
                                  ctypes.c_wchar_p, wintypes.DWORD]
GetModuleFileNameExW.restype = wintypes.DWORD