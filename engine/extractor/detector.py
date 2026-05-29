# -*- coding: utf-8 -*-
"""
================================================================================
 游戏引擎检测器 (纯规则引擎)
================================================================================
 扫描 .exe 所在目录的特征文件，判定游戏引擎类型。
 零 AI 参与，毫秒级判定。
================================================================================
"""

import os
from dataclasses import dataclass, field


# ==================== 翻译项目数据模型 ====================

@dataclass
class TextEntry:
    """单条可翻译文本"""
    file_path: str = ""            # 相对路径，如 "www/data/Items.json"
    key_path: str = ""             # JSON 路径或行号，如 "$.items[3].name"
    source_text: str = ""          # 原文
    translated_text: str = ""      # AI 译文
    approved_text: str = ""        # 玩家人工修正后译文
    is_approved: bool = False      # 是否已经玩家确认


@dataclass
class TranslationProject:
    """翻译项目 — 所有提取器统一输出此结构"""
    engine_type: str = ""          # "rpgmaker_mv", "renpy", "generic_json" 等
    game_root: str = ""            # 游戏根目录（.exe 所在目录）
    exe_path: str = ""             # .exe 完整路径
    entries: list = field(default_factory=list)  # TextEntry 列表
    total_strings: int = 0


# ==================== 检测器 ====================

class EngineDetector:
    """
    游戏引擎检测器。

    检测策略: 扫描 .exe 所在目录及子目录，匹配特征文件。
    """

    # 特征定义: (引擎标识, [特征文件列表], 描述)
    SIGNATURES = [
        (
            "rpgmaker_mv",
            ["www/data/System.json", "www/data/Items.json"],
            "RPG Maker MV",
        ),
        (
            "rpgmaker_mz",
            ["data/System.json", "data/Items.json"],
            "RPG Maker MZ",
        ),
        (
            "renpy",
            ["game/script.rpy", "game/screens.rpy"],
            "Ren'Py",
        ),
        (
            "renpy",
            ["game/script.rpyc"],
            "Ren'Py (编译)",
        ),
        (
            "generic_json",
            ["localization/", "lang/"],
            "通用 JSON I18N",
        ),
    ]

    # Unity 特征（需单独检测）
    UNITY_SIGNATURES = [
        "globalgamemanagers",
        "UnityPlayer.dll",
        "GameAssembly.dll",
        "*.assets",
    ]

    @classmethod
    def detect(cls, exe_path: str) -> str:
        """
        检测游戏引擎类型。

        参数:
            exe_path: .exe 文件的完整路径
        返回:
            引擎类型标识字符串，如 "rpgmaker_mv", "unity", "unknown"
        """
        game_root = os.path.dirname(os.path.abspath(exe_path))

        # 收集目录下所有文件路径
        all_files = set()
        for root, _, files in os.walk(game_root):
            # 限制深度：最多遍历 4 层
            depth = root.replace(game_root, "").count(os.sep)
            if depth > 4:
                continue
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), game_root).replace("\\", "/")
                all_files.add(rel)

        # 匹配已知引擎特征
        for engine_type, signatures, _ in cls.SIGNATURES:
            if all(sig in all_files for sig in signatures):
                return engine_type

        # Unity 检测
        unity_hits = 0
        for sig in cls.UNITY_SIGNATURES:
            if sig.endswith("*"):
                # 通配符模式：匹配扩展名
                ext = sig[1:]
                if any(f.endswith(ext) for f in all_files):
                    unity_hits += 1
            elif sig in all_files:
                unity_hits += 1
        if unity_hits >= 2:
            return "unity"

        return "unknown"

    @classmethod
    def get_friendly_name(cls, engine_type: str) -> str:
        """获取引擎的友好显示名称"""
        names = {
            "rpgmaker_mv": "RPG Maker MV",
            "rpgmaker_mz": "RPG Maker MZ",
            "renpy": "Ren'Py",
            "unity": "Unity",
            "generic_json": "通用 JSON 本地化",
            "unknown": "未知引擎",
        }
        return names.get(engine_type, engine_type)