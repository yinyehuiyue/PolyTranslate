# -*- coding: utf-8 -*-
"""
================================================================================
 文本安全检查工具
================================================================================
 提供占位符验证、乱码检测等功能，确保 AI 翻译不破坏游戏文本格式。
================================================================================
"""

import re


# 占位符正则模式（支持多种游戏引擎的变量语法）
_PLACEHOLDER_PATTERNS = [
    re.compile(r"\{[^}]*\}"),            # {name}, {0}, {color:#fff}
    re.compile(r"%[dsf]"),               # %d, %s, %f
    re.compile(r"%\(\w+\)[dsf]"),        # %(name)s
    re.compile(r"\\[ntr]"),              # \n, \t, \r
    re.compile(r"<[^>]+>"),              # <color=...>, <b>, <size=...>
    re.compile(r"\[\[[^\]]+\]\]"),       # [[var]]
    re.compile(r"\[[a-zA-Z_]\w*\]"),     # [name]
    re.compile(r"\$\w+"),                # $variable
]


class TextGuard:
    """文本安全检查工具（纯静态方法）"""

    @staticmethod
    def has_repeating_garbage(text: str, threshold: int = 8) -> bool:
        """
        检测文本中是否存在连续重复字符（判定为乱码/幻觉输出）。

        检测逻辑：寻找同一个字符连续出现 threshold 次及以上的情况。
        例如 "啊啊啊啊啊啊啊啊" 会被检测为乱码。

        参数:
            text: 待检测文本
            threshold: 重复字符阈值（默认 8）
        返回:
            True 表示检测到乱码
        """
        if not text:
            return False
        pattern = re.compile(r"(.)\1{" + str(threshold - 1) + r",}")
        return bool(pattern.search(text))

    @staticmethod
    def extract_placeholders(text: str) -> list[str]:
        """
        提取文本中所有占位符/特殊标记。

        参数:
            text: 原始文本
        返回:
            所有匹配到的占位符列表（去重，保持发现顺序）
        """
        if not text:
            return []
        seen = set()
        result = []
        for pattern in _PLACEHOLDER_PATTERNS:
            for match in pattern.findall(text):
                if match not in seen:
                    seen.add(match)
                    result.append(match)
        return result

    @classmethod
    def validate_placeholders(
        cls, original: str, translated: str
    ) -> list[str]:
        """
        对比原文和译文，检测缺失的占位符。

        参数:
            original: 原文
            translated: AI 译文
        返回:
            译文中缺失的占位符列表（无缺失则返回空列表）
        """
        orig_placeholders = set(cls.extract_placeholders(original))
        trans_placeholders = set(cls.extract_placeholders(translated))
        missing = orig_placeholders - trans_placeholders
        return sorted(missing)

    @staticmethod
    def is_likely_code(text: str) -> bool:
        """
        判断文本是否更像代码而非自然语言（避免翻译程序脚本）。

        启发式规则:
          - 包含大量符号（>, =, {, }, ; 占比超 30%）
          - 包含常见编程关键词
          - 长度超过 500 字符且无标点

        返回:
            True 表示可能是代码
        """
        if not text:
            return False
        stripped = text.strip()
        # 符号占比检测
        symbol_count = sum(1 for c in stripped if c in "{}();=><[]+-*/&|!@#$%^")
        if len(stripped) > 0 and symbol_count / len(stripped) > 0.3:
            return True
        # 编程关键词检测
        code_keywords = [
            "function", "return", "var", "const", "let", "class",
            "import", "export", "require", "def", "self", "this"
        ]
        words = stripped.lower().split()
        if any(kw in words for kw in code_keywords):
            return True
        return False