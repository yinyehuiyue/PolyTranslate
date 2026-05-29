# -*- coding: utf-8 -*-
"""
================================================================================
 断点续传进度管理器
================================================================================
 通过本地缓存 translation_progress.json 记录翻译进度。
 中途退出或断网后再次打开自动跳过已翻译部分继续执行。
================================================================================
"""

import os
import json
import time


class ProgressTracker:
    """断点续传进度管理器"""

    PROGRESS_FILE = "translation_progress.json"

    def __init__(self, game_root: str, engine_type: str, total: int):
        """
        参数:
            game_root: 游戏根目录路径
            engine_type: 引擎类型标识
            total: 总条目数
        """
        self._game_root = os.path.abspath(game_root)
        self._engine_type = engine_type
        self._total = total
        self._completed = set()

        # 进度文件路径（保存在程序目录而非游戏目录）
        self._progress_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            self.PROGRESS_FILE
        )
        self._load()

    # ── 加载/保存 ──

    def _load(self):
        """加载已有进度"""
        if not os.path.exists(self._progress_path):
            return
        try:
            with open(self._progress_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        # 校验 game_root 匹配（不同游戏不应共用进度）
        if data.get("game_root") != self._game_root:
            self._completed = set()
            return
        if data.get("engine_type") != self._engine_type:
            self._completed = set()
            return

        self._completed = set(data.get("completed_indices", []))
        self._total = max(self._total, data.get("total_entries", self._total))

    def _save(self):
        """保存进度"""
        data = {
            "game_root": self._game_root,
            "engine_type": self._engine_type,
            "total_entries": self._total,
            "completed_indices": sorted(list(self._completed)),
            "last_checkpoint": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        try:
            with open(self._progress_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    # ── 进度操作 ──

    def is_completed(self, index: int) -> bool:
        """检查某条是否已完成"""
        return index in self._completed

    def mark_completed(self, index: int):
        """标记一条完成，每 20 条自动保存一次"""
        self._completed.add(index)
        if len(self._completed) % 20 == 0:
            self._save()

    def mark_batch_completed(self, indices: list):
        """批量标记完成"""
        for i in indices:
            self._completed.add(i)
        self._save()

    def get_pending_indices(self) -> list:
        """获取所有未完成的索引"""
        return [i for i in range(self._total) if i not in self._completed]

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    @property
    def pending_count(self) -> int:
        return self._total - len(self._completed)

    @property
    def is_finished(self) -> bool:
        return self.pending_count == 0

    def clear(self):
        """清除进度记录（翻译全部完成后调用）"""
        self._completed = set()
        if os.path.exists(self._progress_path):
            try:
                os.remove(self._progress_path)
            except OSError:
                pass

    # ── 预估剩余时间 ──

    _start_time: float = 0.0
    _completed_at_start: int = 0

    def start_timer(self):
        """开始计时"""
        self._start_time = time.time()
        self._completed_at_start = self.completed_count

    def estimate_remaining(self) -> str:
        """
        预估剩余时间。

        返回: 格式化的时间字符串
        """
        if self._start_time == 0 or self.completed_count <= self._completed_at_start:
            return "计算中..."
        elapsed = time.time() - self._start_time
        done_since_start = self.completed_count - self._completed_at_start
        if done_since_start <= 0:
            return "计算中..."
        avg = elapsed / done_since_start
        remaining_sec = avg * self.pending_count
        if remaining_sec < 60:
            return f"{int(remaining_sec)} 秒"
        elif remaining_sec < 3600:
            return f"{int(remaining_sec / 60)} 分钟"
        else:
            return f"{remaining_sec / 3600:.1f} 小时"