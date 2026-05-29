# -*- coding: utf-8 -*-
"""
================================================================================
 文件备份与还原管理器
================================================================================
 职责:
   1. 在修改游戏文件前创建完整备份
   2. 支持按需还原
   3. 生成 .backup_originals/ 目录存放原始文件
================================================================================
"""

import os
import shutil
import json
from datetime import datetime


class BackupManager:
    """
    备份管理器。

    备份目录结构:
      <game_root>/.backup_originals/
        ├── manifest.json          # 备份清单（记录原始文件列表 + 时间戳）
        └── www/data/Items.json    # 按原目录结构存放
    """

    BACKUP_DIR_NAME = ".backup_originals"
    MANIFEST_NAME = "manifest.json"

    def __init__(self, game_root: str):
        """
        参数:
            game_root: 游戏根目录（.exe 所在目录）
        """
        self._game_root = os.path.abspath(game_root)
        self._backup_root = os.path.join(self._game_root, self.BACKUP_DIR_NAME)

    # ---------- 清单管理 ----------

    def _load_manifest(self) -> dict:
        """加载备份清单"""
        manifest_path = os.path.join(self._backup_root, self.MANIFEST_NAME)
        if not os.path.exists(manifest_path):
            return {"created": "", "files": []}
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"created": "", "files": []}

    def _save_manifest(self, manifest: dict):
        """保存备份清单"""
        os.makedirs(self._backup_root, exist_ok=True)
        manifest_path = os.path.join(self._backup_root, self.MANIFEST_NAME)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    # ---------- 备份 ----------

    def backup_file(self, relative_path: str) -> bool:
        """
        备份单个文件（相对于游戏根目录）。

        参数:
            relative_path: 相对路径，如 "www/data/Items.json"
        返回:
            是否备份成功（若已备份过则直接返回 True）
        """
        source = os.path.join(self._game_root, relative_path)
        if not os.path.isfile(source):
            return False

        dest = os.path.join(self._backup_root, relative_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        # 仅在未备份时复制
        if not os.path.exists(dest):
            shutil.copy2(source, dest)

        # 更新清单
        manifest = self._load_manifest()
        if not manifest["created"]:
            manifest["created"] = datetime.now().isoformat()
        if relative_path not in manifest["files"]:
            manifest["files"].append(relative_path)
        self._save_manifest(manifest)
        return True

    def backup_files(self, relative_paths: list) -> int:
        """
        批量备份文件。

        返回:
            成功备份的文件数
        """
        count = 0
        for rp in relative_paths:
            if self.backup_file(rp):
                count += 1
        return count

    # ---------- 还原 ----------

    def restore_file(self, relative_path: str) -> bool:
        """
        从备份还原单个文件。

        参数:
            relative_path: 相对路径
        返回:
            是否还原成功
        """
        backup_src = os.path.join(self._backup_root, relative_path)
        if not os.path.isfile(backup_src):
            return False
        dest = os.path.join(self._game_root, relative_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(backup_src, dest)
        return True

    def restore_all(self) -> int:
        """
        还原所有已备份的文件。

        返回:
            成功还原的文件数
        """
        manifest = self._load_manifest()
        count = 0
        for rp in manifest.get("files", []):
            if self.restore_file(rp):
                count += 1
        return count

    # ---------- 一键清理注入产物 ----------

    def clean_injected_artifacts(self) -> dict:
        """
        清理所有注入产生的文件（不含备份内容）。

        清理目标:
          1. .translator_cache.json（翻译缓存库）
          2. game/tl/chinese/（Ren'Py 翻译文件）
          3. translation_progress.json（进度文件 — 程序目录）

        返回:
            {"cleaned": [...], "errors": [...]}
        """
        cleaned = []
        errors = []

        # 1. 翻译缓存库
        cache = os.path.join(self._game_root, ".translator_cache.json")
        if os.path.exists(cache):
            try:
                os.remove(cache)
                cleaned.append(".translator_cache.json")
            except OSError as e:
                errors.append(f".translator_cache.json: {e}")

        # 2. Ren'Py 翻译目录
        tl_dir = os.path.join(self._game_root, "game", "tl", "chinese")
        if os.path.isdir(tl_dir):
            try:
                shutil.rmtree(tl_dir)
                cleaned.append("game/tl/chinese/")
            except OSError as e:
                errors.append(f"game/tl/chinese/: {e}")

        # 3. 进度文件
        progress_file = os.path.join(
            os.path.dirname(self._game_root),
            "translation_progress.json",
        )
        if os.path.exists(progress_file):
            try:
                os.remove(progress_file)
                cleaned.append("translation_progress.json")
            except OSError as e:
                errors.append(f"translation_progress.json: {e}")

        return {"cleaned": cleaned, "errors": errors}

    # ---------- 查询 ----------

    def is_backed_up(self) -> bool:
        """是否有备份记录"""
        return os.path.exists(self._backup_root) and len(
            self._load_manifest().get("files", [])
        ) > 0

    def get_backup_info(self) -> dict:
        """获取备份信息"""
        return self._load_manifest()