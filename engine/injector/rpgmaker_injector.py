# -*- coding: utf-8 -*-
"""
================================================================================
 RPG Maker 注入器
================================================================================
 职责:
   1. 备份原始 JSON 文件到 .backup_originals/
   2. 将译文写回原始 JSON 对应路径
   3. 生成 .translator_cache.json 供玩家纠错编辑器使用
================================================================================
"""

import os
import json
import copy
from engine.backup_manager import BackupManager
from engine.extractor.detector import TextEntry, TranslationProject


class RPGMakerInjector:
    """RPG Maker MV/MZ 翻译注入器"""

    CACHE_FILENAME = ".translator_cache.json"

    def __init__(self):
        self._backup_mgr = None

    def inject(self, project: TranslationProject, apply_corrections: bool = False) -> dict:
        """
        执行注入流程。

        参数:
            project: TranslationProject（含已翻译的 entries）
            apply_corrections: 是否使用 approved_text 覆盖 translated_text
        返回:
            统计信息 {"backed_up": N, "injected": N, "cache_path": "..."}
        """
        if not project.entries:
            return {"error": "没有翻译条目可供注入"}

        self._backup_mgr = BackupManager(project.game_root)

        # 按文件分组 entries
        file_groups = {}
        for entry in project.entries:
            fp = entry.file_path
            if fp not in file_groups:
                file_groups[fp] = []
            file_groups[fp].append(entry)

        # ---------- 步骤 1: 备份 ----------
        backed_up = self._backup_mgr.backup_files(list(file_groups.keys()))

        # ---------- 步骤 2: 覆写 ----------
        injected_count = 0
        for rel_path, entries in file_groups.items():
            abs_path = os.path.join(project.game_root, rel_path)
            if not os.path.isfile(abs_path):
                continue
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            # 对每个 entry 进行回写
            for entry in entries:
                target_text = entry.approved_text if (apply_corrections and entry.approved_text) else entry.translated_text
                if not target_text or target_text.startswith("[翻译失败]"):
                    continue
                if self._set_json_value(data, entry.key_path, target_text):
                    injected_count += 1

            # 写回 JSON 文件
            try:
                with open(abs_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except IOError:
                continue

        # ---------- 步骤 3: 生成翻译缓存库 ----------
        cache_path = self._generate_cache(project)

        return {
            "backed_up": backed_up,
            "injected": injected_count,
            "cache_path": os.path.relpath(cache_path, project.game_root),
        }

    # ---------- JSON 路径回写 ----------

    @staticmethod
    def _set_json_value(data, key_path: str, value: str) -> bool:
        """
        根据 jsonpath 表达式设置 JSON 中的值。

        支持格式:
          $.items[3].name  →  data["items"][3]["name"] = value
          $.actors[0].nickname

        返回:
            True 表示设置成功
        """
        try:
            # 解析 jsonpath: $.items[3].name → ["items", 3, "name"]
            parts = []
            path = key_path.strip()
            if path.startswith("$."):
                path = path[2:]
            elif path.startswith("$"):
                path = path[1:]

            # 手动解析 .key 和 [idx] 片段
            current = ""
            i = 0
            while i < len(path):
                ch = path[i]
                if ch == ".":
                    if current:
                        parts.append(current)
                    current = ""
                    i += 1
                elif ch == "[":
                    if current:
                        parts.append(current)
                    current = ""
                    i += 1
                    # 读取索引
                    idx_str = ""
                    while i < len(path) and path[i] != "]":
                        idx_str += path[i]
                        i += 1
                    i += 1  # 跳过 ]
                    parts.append(int(idx_str))
                else:
                    current += ch
                    i += 1
            if current:
                parts.append(current)

            # 遍历设置
            node = data
            for p in parts[:-1]:
                if isinstance(p, int):
                    node = node[p]
                else:
                    node = node[p]
            last = parts[-1]
            if isinstance(last, int):
                node[last] = value
            else:
                node[last] = value
            return True
        except (KeyError, IndexError, TypeError, ValueError):
            return False

    # ---------- 翻译缓存库生成 ----------

    def _generate_cache(self, project: TranslationProject) -> str:
        """
        生成 .translator_cache.json（供纠错编辑器使用）。

        格式:
        {
          "engine_type": "rpgmaker_mv",
          "game_root": "...",
          "records": [
            {
              "file_path": "www/data/Items.json",
              "key_path": "$.items[3].name",
              "source_text": "Potion",
              "translated_text": "药水",
              "approved_text": "",
              "is_approved": false
            },
            ...
          ]
        }
        """
        records = []
        for entry in project.entries:
            records.append({
                "file_path": entry.file_path,
                "key_path": entry.key_path,
                "source_text": entry.source_text,
                "translated_text": entry.translated_text,
                "approved_text": entry.approved_text or "",
                "is_approved": entry.is_approved,
            })

        cache = {
            "engine_type": project.engine_type,
            "game_root": project.game_root,
            "records": records,
            "total": len(records),
        }

        cache_path = os.path.join(project.game_root, self.CACHE_FILENAME)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

        return cache_path

    @staticmethod
    def load_cache(game_root: str) -> dict:
        """
        加载翻译缓存库。

        参数:
            game_root: 游戏根目录
        返回:
            缓存数据字典，不存在则返回 {"records": []}
        """
        cache_path = os.path.join(game_root, RPGMakerInjector.CACHE_FILENAME)
        if not os.path.exists(cache_path):
            return {"records": [], "engine_type": "", "game_root": game_root}
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"records": [], "engine_type": "", "game_root": game_root}