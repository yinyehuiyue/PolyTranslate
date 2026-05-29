# -*- coding: utf-8 -*-
"""
================================================================================
 RPG Maker MV / MZ 文本提取器
================================================================================
 策略: 递归遍历 www/data/ (MV) 或 data/ (MZ) 下的所有 .json 文件，
       收集所有 str 类型叶子节点，记录 jsonpath 用于回写。
================================================================================
"""

import os
import json
from engine.extractor.detector import TextEntry, TranslationProject


# 需要提取的 JSON 字段名关键词（不区分大小写）
_TEXT_FIELD_KEYWORDS = [
    "name", "description", "message", "note", "text",
    "displayname", "nickname", "title", "profile",
    "memo", "hint", "caption", "label", "tooltip",
    "info", "detail", "content", "summary",
    "parametername", "battlername",
]

# 排除的 JSON 文件名（不含可翻译文本）
_EXCLUDE_FILES = [
    "System.json.bak", "manifest.json", "version.json",
]

# 排除的值模式（非自然语言）
_EXCLUDE_VALUE_PATTERNS = [
    lambda v: v.isdigit(),                                     # 纯数字
    lambda v: len(v) <= 1,                                     # 单字符
    lambda v: all(c in "0123456789,.[]{}():;+-*/=<>!@#$%^&|" for c in v),  # 纯符号
]


class RPGMakerExtractor:
    """RPG Maker MV / MZ 文本提取器"""

    def __init__(self):
        self._entries: list[TextEntry] = []

    def extract(self, game_root: str, engine_type: str, exe_path: str) -> TranslationProject:
        """
        执行提取。

        参数:
            game_root: 游戏根目录
            engine_type: "rpgmaker_mv" 或 "rpgmaker_mz"
            exe_path: .exe 完整路径
        返回:
            TranslationProject 对象
        """
        self._entries = []

        # 确定数据目录
        if engine_type == "rpgmaker_mv":
            data_dir = os.path.join(game_root, "www", "data")
        else:
            data_dir = os.path.join(game_root, "data")

        if not os.path.isdir(data_dir):
            project = TranslationProject(
                engine_type=engine_type,
                game_root=game_root,
                exe_path=exe_path,
                entries=[],
                total_strings=0,
            )
            return project

        # 遍历所有 JSON 文件
        for root, _, files in os.walk(data_dir):
            for filename in files:
                if not filename.endswith(".json"):
                    continue
                if filename in _EXCLUDE_FILES:
                    continue
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, game_root).replace("\\", "/")
                self._extract_json(filepath, rel_path)

        project = TranslationProject(
            engine_type=engine_type,
            game_root=game_root,
            exe_path=exe_path,
            entries=self._entries,
            total_strings=len(self._entries),
        )
        return project

    def _extract_json(self, filepath: str, rel_path: str):
        """
        递归提取单个 JSON 文件中的所有文本。

        参数:
            filepath: JSON 文件绝对路径
            rel_path: 相对于游戏根目录的路径
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError, UnicodeDecodeError):
            return

        self._walk_json(data, rel_path, "$")

    def _walk_json(self, node, rel_path: str, current_path: str):
        """
        递归遍历 JSON 节点。

        参数:
            node: 当前 JSON 节点（dict, list, str, int 等）
            rel_path: JSON 文件相对路径
            current_path: 当前 jsonpath 表达式
        """
        if isinstance(node, dict):
            for key, value in node.items():
                child_path = f"{current_path}.{key}" if current_path != "$" else f"$.{key}"
                if isinstance(value, str):
                    if self._is_translatable(key, value):
                        self._entries.append(TextEntry(
                            file_path=rel_path,
                            key_path=child_path,
                            source_text=value,
                        ))
                else:
                    self._walk_json(value, rel_path, child_path)
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                child_path = f"{current_path}[{idx}]"
                if isinstance(item, str):
                    if self._is_translatable("", item):
                        self._entries.append(TextEntry(
                            file_path=rel_path,
                            key_path=child_path,
                            source_text=item,
                        ))
                else:
                    self._walk_json(item, rel_path, child_path)

    def _is_translatable(self, key: str, value: str) -> bool:
        """
        判断一个字符串值是否需要翻译。

        过滤规则:
          1. 纯数字/纯符号/单字符 → 跳过
          2. 如果 key 匹配文本关键词 → 通过
          3. 如果 key 为空（数组元素），判断值是否为自然语言
        """
        if not value or not value.strip():
            return False

        # 排除纯符号/数字
        for pattern in _EXCLUDE_VALUE_PATTERNS:
            if pattern(value):
                return False

        # 如果 key 是已知的文本字段 → 通过
        if key:
            key_lower = key.lower()
            if any(kw in key_lower for kw in _TEXT_FIELD_KEYWORDS):
                return True

        # 对匿名文本（无 key 或 key 不匹配），长度 >= 4 且含字母/中文则可通过
        if len(value) >= 4:
            has_letter = any(c.isalpha() for c in value)
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in value)
            if has_letter or has_chinese:
                return True

        return False