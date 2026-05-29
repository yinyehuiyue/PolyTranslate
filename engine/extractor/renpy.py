# -*- coding: utf-8 -*-
"""
================================================================================
 Ren'Py 文本提取器
================================================================================
 策略: 正则解析 .rpy 文件中的 say 语句和 menu 语句。
       保留 Ren'Py 插值语法: [var], %(name)s, {color=...} 等。
================================================================================
"""

import os
import re
from engine.extractor.detector import TextEntry, TranslationProject


# Ren'Py 对话/菜单正则模式
_PATTERNS = [
    # 角色对话:  char "text"
    re.compile(r'(?:^|\n)\s*([a-zA-Z_]\w*)\s+"([^"]*)"'),
    # 角色对话带参数:  char "text" (style)
    re.compile(r'(?:^|\n)\s*([a-zA-Z_]\w*)\s+"([^"]*)"\s*\([^)]*\)'),
    # 旁白:  "text"  
    re.compile(r'(?:^|\n)\s*"([^"]*)"\s*(?:#.*)?$', re.MULTILINE),
    # Menu 选项:  "Option":
    re.compile(r'(?:^|\n)\s*"([^"]*)":\s*(?:#.*)?$', re.MULTILINE),
]

# 排除的文本模式（非自然语言）
_EXCLUDE_PATTERNS = [
    re.compile(r'^\s*$'),                                    # 空白
    re.compile(r'^[0-9.,+\-*/(){}[\]:;<>!@#$%^&=|\\/\'`~_]+$'),  # 纯符号/数字
    re.compile(r'^[a-z_][\w.]*\.[\w.]+$'),                   # 方法调用/属性
    re.compile(r'^[\s#]'),                                    # 注释
]


class RenPyExtractor:
    """Ren'Py 文本提取器"""

    def __init__(self):
        self._entries: list[TextEntry] = []

    def extract(self, game_root: str, engine_type: str, exe_path: str) -> TranslationProject:
        """
        提取 Ren'Py 游戏中的所有可翻译文本。

        参数:
            game_root: 游戏根目录
            engine_type: "renpy"
            exe_path: .exe 完整路径
        返回:
            TranslationProject
        """
        self._entries = []

        game_dir = os.path.join(game_root, "game")
        if not os.path.isdir(game_dir):
            return TranslationProject(
                engine_type=engine_type,
                game_root=game_root,
                exe_path=exe_path,
                entries=[],
                total_strings=0,
            )

        # 遍历 game/ 下所有 .rpy 文件（跳过 .rpyc 编译文件）
        for root, _, files in os.walk(game_dir):
            for filename in files:
                if not filename.endswith(".rpy"):
                    continue
                # 跳过已有翻译文件
                if "/tl/" in root.replace("\\", "/"):
                    continue
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, game_root).replace("\\", "/")
                self._extract_rpy(filepath, rel_path)

        project = TranslationProject(
            engine_type=engine_type,
            game_root=game_root,
            exe_path=exe_path,
            entries=self._entries,
            total_strings=len(self._entries),
        )
        return project

    def _extract_rpy(self, filepath: str, rel_path: str):
        """
        从单个 .rpy 文件提取文本。

        参数:
            filepath: .rpy 文件绝对路径
            rel_path: 相对路径
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            return

        lines = content.split("\n")
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            # 跳过注释
            if stripped.startswith("#"):
                continue
            # 跳过 translate 语句（已翻译内容）
            if stripped.startswith("old ") or stripped.startswith("new "):
                continue

            for pattern in _PATTERNS:
                for match in pattern.finditer(line):
                    text = match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(1)
                    if not text:
                        continue
                    text = text.strip()
                    if self._is_translatable(text):
                        self._entries.append(TextEntry(
                            file_path=rel_path,
                            key_path=f"line_{line_no}",
                            source_text=text,
                        ))

    @staticmethod
    def _is_translatable(text: str) -> bool:
        """判断文本是否需要翻译"""
        if not text or not text.strip():
            return False
        for pat in _EXCLUDE_PATTERNS:
            if pat.match(text):
                return False
        # 至少含有一个字母或已含中文（但长度需 >= 2）
        has_letter = any(c.isalpha() for c in text)
        if has_letter and len(text) >= 2:
            return True
        return False