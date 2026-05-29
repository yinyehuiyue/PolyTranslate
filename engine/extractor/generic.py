# -*- coding: utf-8 -*-
"""
================================================================================
 通用文本提取器
================================================================================
 支持格式: JSON I18N (localization/*.json), CSV, GNU gettext .po 文件。
 用于: Unity 导出数据、自定义引擎、通用国际化格式。
================================================================================
"""

import os
import json
import csv
import re
from engine.extractor.detector import TextEntry, TranslationProject


# .po 文件 msgid 正则
_PO_MSGID = re.compile(r'^msgid\s+"(.*)"$')


class GenericExtractor:
    """通用文本提取器"""

    def __init__(self):
        self._entries: list[TextEntry] = []

    def extract(self, game_root: str, engine_type: str, exe_path: str) -> TranslationProject:
        """
        提取通用格式的文本。

        参数:
            game_root: 游戏根目录
            engine_type: "generic_json" 或 "unknown"
            exe_path: .exe 完整路径
        """
        self._entries = []

        # 搜索常见本地化目录
        search_dirs = [
            os.path.join(game_root, "localization"),
            os.path.join(game_root, "lang"),
            os.path.join(game_root, "locale"),
            os.path.join(game_root, "i18n"),
            os.path.join(game_root, "locales"),
            game_root,
        ]

        for search_dir in search_dirs:
            if not os.path.isdir(search_dir):
                continue
            for root, _, files in os.walk(search_dir):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, game_root).replace("\\", "/")
                    ext = os.path.splitext(filename)[1].lower()
                    if ext == ".json":
                        self._extract_json(filepath, rel_path)
                    elif ext == ".csv":
                        self._extract_csv(filepath, rel_path)
                    elif ext == ".po" or ext == ".pot":
                        self._extract_po(filepath, rel_path)

        return TranslationProject(
            engine_type=engine_type,
            game_root=game_root,
            exe_path=exe_path,
            entries=self._entries,
            total_strings=len(self._entries),
        )

    # ---------- JSON ----------

    def _extract_json(self, filepath: str, rel_path: str):
        """提取 JSON 国际化文件"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError, UnicodeDecodeError):
            return

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and self._is_text(value):
                    self._entries.append(TextEntry(
                        file_path=rel_path,
                        key_path=f"$.{key}",
                        source_text=value,
                    ))

    # ---------- CSV ----------

    def _extract_csv(self, filepath: str, rel_path: str):
        """提取 CSV 本地化文件"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = None
                for row_idx, row in enumerate(reader):
                    if row_idx == 0:
                        headers = row
                        continue
                    if not row:
                        continue
                    # 尝试找到源文本列
                    for col_idx, cell in enumerate(row):
                        if self._is_text(cell):
                            header = headers[col_idx] if headers and col_idx < len(headers) else f"col_{col_idx}"
                            self._entries.append(TextEntry(
                                file_path=rel_path,
                                key_path=f"row_{row_idx}.{header}",
                                source_text=cell.strip(),
                            ))
        except (IOError, UnicodeDecodeError):
            return

    # ---------- GNU gettext .po ----------

    def _extract_po(self, filepath: str, rel_path: str):
        """提取 .po / .pot 文件"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (IOError, UnicodeDecodeError):
            return

        for line_no, line in enumerate(lines, 1):
            match = _PO_MSGID.match(line.strip())
            if match:
                text = match.group(1)
                if self._is_text(text):
                    self._entries.append(TextEntry(
                        file_path=rel_path,
                        key_path=f"line_{line_no}",
                        source_text=text,
                    ))

    # ---------- 辅助 ----------

    @staticmethod
    def _is_text(value: str) -> bool:
        """判断是否为需要翻译的自然语言文本"""
        if not value or not value.strip():
            return False
        s = value.strip()
        if len(s) <= 1:
            return False
        if s.isdigit():
            return False
        # 必须至少含有一个字母
        return any(c.isalpha() for c in s)