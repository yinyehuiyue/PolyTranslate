# -*- coding: utf-8 -*-
"""
================================================================================
 Shellcode 模板库
================================================================================
 提供嵌入在 Python 中的 x86 汇编 Shellcode 模板（十六进制字节形式）。
 用于内存注入时的查表替换和 GDI Hook 跳板。
================================================================================
"""

# ==================== 翻译查表函数 (x86) ====================
# 功能: 遍历嵌入的翻译表, 查找原文 → 返回译文字符串指针
# 调用约定: __stdcall
# 参数: (char* src, int len, TABLE* table) → char* tgt or NULL

SHELLCODE_LOOKUP_X86 = bytes([
    # ── 函数序言 ──
    0x55,                          # push ebp
    0x89, 0xE5,                    # mov ebp, esp
    0x56,                          # push esi
    0x57,                          # push edi
    0x53,                          # push ebx

    # ── 加载参数 ──
    0x8B, 0x75, 0x08,              # mov esi, [ebp+8]   ; esi = src
    0x8B, 0x4D, 0x0C,              # mov ecx, [ebp+12]  ; ecx = len
    0x8B, 0x5D, 0x10,              # mov ebx, [ebp+16]  ; ebx = table

    # ── 读取 num_entries ──
    0x8B, 0x13,                    # mov edx, [ebx]      ; edx = table->num_entries
    0x83, 0xC3, 0x04,              # add ebx, 4          ; ebx = &entries[0]

    # ========== search_loop ==========
    # 检查是否遍历完毕
    0x85, 0xD2,                    # test edx, edx
    0x74, 0x27,                    # jz not_found (+0x27 = 39 bytes ahead)

    # 比较 src_len
    0x3B, 0x0B,                    # cmp ecx, [ebx]       ; cmp(len, entry->src_len)
    0x75, 0x1D,                    # jne next_entry (+0x1D)

    # 比较内容 (repe cmpsb)
    0x51,                          # push ecx
    0x8D, 0x7B, 0x04,               # lea edi, [ebx+4]   ; edi = entry->src
    0x56,                          # push esi
    0x57,                          # push edi
    0x8B, 0x0B,                    # mov ecx, [ebx]      ; ecx = entry->src_len
    0xF3, 0xA6,                    # repe cmpsb           ; 逐字节比较
    0x5F,                          # pop edi
    0x5E,                          # pop esi
    0x59,                          # pop ecx
    0x75, 0x0B,                    # jne next_entry

    # ── 找到了! eax = &entry->tgt (UTF-8/null-terminated) ──
    0x8D, 0x43, 0x04,               # lea eax, [ebx+4]   ; 跳过 src_len
    0x03, 0x03,                    # add eax, [ebx]      ; 跳过 src 内容
    0x83, 0xC0, 0x04,               # add eax, 4         ; 跳过 tgt_len
    0xEB, 0x10,                    # jmp done

    # ========== next_entry ==========
    # entry_size = 4 + src_len + 4 + tgt_len
    0x8B, 0x03,                    # mov eax, [ebx]      ; eax = src_len
    0x83, 0xC0, 0x04,               # add eax, 4         ; + src_len field
    0x03, 0x44, 0x18, 0x04,         # 破解: add eax,[ebx+eax+4]; + tgt_len
    # 简化重写:
    0x83, 0xC0, 0x04,               # add eax, 4         ; + tgt_len field
    0x01, 0xC3,                    # add ebx, eax        ; ebx = next entry
    0x4A,                          # dec edx
    0xEB, 0xC0,                    # jmp search_loop (跳回 -0x40)

    # ========== not_found ==========
    0x31, 0xC0,                    # xor eax, eax         ; return NULL

    # ========== done ==========
    0x5B,                          # pop ebx
    0x5F,                          # pop edi
    0x5E,                          # pop esi
    0x5D,                          # pop ebp
    0xC2, 0x0C, 0x00,              # ret 12             ; __stdcall 3参数
])

# NOTE: 上面的 Shellcode 为简化示意版本。实际使用需在 MSVC 或 NASM 中
# 编译完整版本，包括:
#   1. 内存对齐 (避免未对齐访问在严格模式崩溃)
#   2. SEH 帧保护 (防止单字节异常导致整个游戏崩溃)
#   3. 冗余校验 (在翻译表末尾添加魔法数字校验)


# ==================== 暴力内存覆写 Shellcode ====================
#
# 功能: 接收 (src_ptr, src_len, tgt_ptr, tgt_len) → 覆写内存
# 用于 WriteProcessMemory 之后的原地替换

BRUTE_OVERWRITE_STUB = bytes([
    0xB8, 0x00, 0x00, 0x00, 0x00,  # mov eax, <original_func_addr>
    0xFF, 0xE0,                     # jmp eax
])


# ==================== 翻译表序列化 ====================

import struct


def build_translation_table(translation_map: dict) -> bytes:
    """
    将翻译字典序列化为 Shellcode 可读的二进制格式。

    格式:
      [4 bytes] num_entries (uint32 LE)
      for each entry:
        [4 bytes] src_len  (uint32 LE)
        [N bytes] src       (UTF-8, 无 null 终止)
        [4 bytes] tgt_len  (uint32 LE)
        [N+1 bytes] tgt     (UTF-8, null 终止: 1 字节 '\0')
    """
    buf = bytearray()
    # num_entries
    buf += struct.pack("<I", len(translation_map))

    for src, tgt in translation_map.items():
        src_bytes = src.encode("utf-8")
        tgt_bytes = tgt.encode("utf-8") + b"\x00"  # null 终止

        buf += struct.pack("<I", len(src_bytes))
        buf += src_bytes
        buf += struct.pack("<I", len(tgt_bytes) - 1)  # tgt_len 不含 null
        buf += tgt_bytes

    return bytes(buf)