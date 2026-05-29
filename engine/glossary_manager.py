# -*- coding: utf-8 -*-
"""
================================================================================
 术语字典管理器
================================================================================
 支持从 config.json 内联存储加载、dict.json 文件导入/导出、CRUD 操作。
 v3.0: 术语字典数据内联存储在 config.json 的 glossary_entries 字段中。
================================================================================
"""

import json
import os

# dict.json 路径（兼容旧版）
_DICT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dict.json"
)


class GlossaryManager:
    """术语字典管理器（纯静态方法）"""

    # ---------- 内联存储（config.json 中的 glossary_entries） ----------

    @staticmethod
    def from_config(config: dict) -> dict:
        """从配置字典中提取术语表"""
        return config.get("glossary_entries", {}) or {}

    @staticmethod
    def to_config(config: dict, glossary: dict) -> dict:
        """将术语表写入配置字典"""
        config["glossary_entries"] = dict(glossary)
        return config

    # ---------- dict.json 兼容（导入/导出） ----------

    @staticmethod
    def import_from_json(filepath: str = None) -> dict:
        """
        从外部 JSON 文件导入术语表。

        参数:
            filepath: JSON 文件路径，默认为 dict.json
        返回:
            术语字典
        """
        path = filepath or _DICT_PATH
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError):
            return {}

    @staticmethod
    def export_to_json(glossary: dict, filepath: str = None) -> bool:
        """
        导出术语表到外部 JSON 文件。

        参数:
            glossary: 术语字典
            filepath: 输出路径，默认 dict.json
        返回:
            是否成功
        """
        path = filepath or _DICT_PATH
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(glossary, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False

    # ---------- CRUD ----------

    @staticmethod
    def add_term(glossary: dict, src: str, tgt: str) -> dict:
        """添加或更新一条术语。返回修改后的字典。"""
        glossary[src.strip()] = tgt.strip()
        return glossary

    @staticmethod
    def remove_term(glossary: dict, src: str) -> dict:
        """删除一条术语。返回修改后的字典。"""
        glossary.pop(src, None)
        return glossary

    @staticmethod
    def get_terms_as_list(glossary: dict) -> list:
        """获取术语表为列表 [(src, tgt), ...] 便于 Treeview 展示"""
        return [(k, v) for k, v in glossary.items()]