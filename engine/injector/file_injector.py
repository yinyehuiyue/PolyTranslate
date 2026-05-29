# -*- coding: utf-8 -*-
"""
================================================================================
 文件注入器 — 常规注入 (RPG Maker + Ren'Py 合并)
================================================================================
 继承 BaseInjector，实现基于文件覆写的常规译文注入。
 优先级最高：安全、可靠、非侵入式。
================================================================================
"""

import os
import json
from engine.injector.base_injector import BaseInjector, InjectionState, RetryCategory
from engine.backup_manager import BackupManager
from engine.extractor.detector import TranslationProject


class FileInjector(BaseInjector):
    """文件注入器 — 常规注入首选方案"""

    CACHE_FILENAME = ".translator_cache.json"

    def inject(self, project: TranslationProject,
               apply_corrections: bool = False) -> dict:
        """
        执行文件级注入。

        路由:
          rpgmaker_mv/mz → _inject_rpgmaker()
          renpy → _inject_renpy()
        """
        if not project.entries:
            return {"error": "无翻译条目"}

        self._set_state(InjectionState.INJECTING_NORMAL,
                        f"常规文件注入 第 {self.current_attempt}/10 次")

        try:
            if project.engine_type in ("rpgmaker_mv", "rpgmaker_mz"):
                result = self._inject_rpgmaker(project, apply_corrections)
            elif project.engine_type == "renpy":
                result = self._inject_renpy(project, apply_corrections)
            else:
                result = {"injected": 0, "cache_path": ""}

            if result.get("injected", 0) > 0:
                self._counter.record(RetryCategory.SUCCESS)
                self._set_state(InjectionState.DONE)
            else:
                self._counter.record(RetryCategory.CORE, "文件注入无有效条目")
            return result

        except Exception as e:
            self._counter.record(RetryCategory.CORE, str(e))
            raise

    # ==================== RPG Maker 注入 ====================

    def _inject_rpgmaker(self, project: TranslationProject,
                         apply_corrections: bool) -> dict:
        """RPG Maker MV/MZ JSON 回写"""
        backup_mgr = BackupManager(project.game_root)

        # 按文件分组
        file_groups = {}
        for entry in project.entries:
            file_groups.setdefault(entry.file_path, []).append(entry)

        # 备份
        backup_mgr.backup_files(list(file_groups.keys()))

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

            for entry in entries:
                target = (entry.approved_text
                          if (apply_corrections and entry.approved_text)
                          else entry.translated_text)
                if not target or target.startswith("[翻译失败]"):
                    continue
                if self._set_json_value(data, entry.key_path, target):
                    injected_count += 1

            try:
                with open(abs_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except IOError:
                continue

        cache_path = self._generate_cache(project)
        return {
            "injected": injected_count,
            "cache_path": os.path.relpath(cache_path, project.game_root),
            "backed_up": True,
        }

    # ==================== Ren'Py 注入 ====================

    def _inject_renpy(self, project: TranslationProject,
                      apply_corrections: bool) -> dict:
        """Ren'Py .rpy 翻译文件生成"""
        tl_dir = os.path.join(project.game_root, "game", "tl", "chinese")
        os.makedirs(tl_dir, exist_ok=True)

        file_groups = {}
        for entry in project.entries:
            file_groups.setdefault(entry.file_path, []).append(entry)

        injected_count = 0
        for rel_path, entries in file_groups.items():
            base_name = os.path.basename(rel_path)
            tl_file = os.path.join(tl_dir, base_name)

            lines = [
                "# -*- coding: utf-8 -*-",
                f"# Auto-generated translation for {rel_path}",
                "",
                "translate chinese strings:",
                "",
            ]
            file_injected = 0
            for entry in entries:
                target = (entry.approved_text
                          if (apply_corrections and entry.approved_text)
                          else entry.translated_text)
                if not target or target.startswith("[翻译失败]"):
                    continue
                lines.append(f'    old "{entry.source_text}"')
                lines.append(f'    new "{target}"')
                lines.append("")
                file_injected += 1

            if file_injected > 0:
                try:
                    with open(tl_file, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines))
                except IOError:
                    continue
                injected_count += file_injected

        cache_path = self._generate_cache(project)
        return {
            "injected": injected_count,
            "cache_path": os.path.relpath(cache_path, project.game_root),
        }

    # ==================== 辅助方法 ====================

    @staticmethod
    def _set_json_value(data, key_path: str, value: str) -> bool:
        """JSON 路径回写"""
        try:
            parts = []
            path = key_path.strip()
            if path.startswith("$."):
                path = path[2:]
            elif path.startswith("$"):
                path = path[1:]
            cur = ""
            i = 0
            while i < len(path):
                ch = path[i]
                if ch == ".":
                    if cur:
                        parts.append(cur)
                    cur = ""
                    i += 1
                elif ch == "[":
                    if cur:
                        parts.append(cur)
                    cur = ""
                    i += 1
                    idx_str = ""
                    while i < len(path) and path[i] != "]":
                        idx_str += path[i]
                        i += 1
                    i += 1
                    parts.append(int(idx_str))
                else:
                    cur += ch
                    i += 1
            if cur:
                parts.append(cur)

            node = data
            for p in parts[:-1]:
                node = node[p] if isinstance(p, str) else node[p]
            last = parts[-1]
            node[last] = value
            return True
        except (KeyError, IndexError, TypeError, ValueError):
            return False

    def _generate_cache(self, project: TranslationProject) -> str:
        """生成 .translator_cache.json"""
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