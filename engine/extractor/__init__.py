# -*- coding: utf-8 -*-
"""
游戏文本提取器子包。

检测器流程:
  用户拖入 .exe → detector.py 扫描目录特征 → 路由到对应提取器

支持的引擎:
  - RPG Maker MV / MZ
  - Ren'Py
  - Unity (特征检测 + 引导用户导出)
  - 通用 JSON / CSV / PO
"""

from engine.extractor.detector import EngineDetector
from engine.extractor.rpgmaker import RPGMakerExtractor
from engine.extractor.renpy import RenPyExtractor
from engine.extractor.generic import GenericExtractor