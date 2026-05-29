# -*- coding: utf-8 -*-
"""
================================================================================
 主窗口 v4.0 — CustomTkinter 深色主题 + 注入状态机
================================================================================
 整合所有 UI 组件，处理核心工作流:
   拖入 .exe → 检测引擎 → 提取文本 → 翻译 → 注入 → 可启动游戏
   带注入指示灯 + 一键还原按钮 + 强制注入降级
================================================================================
"""

import os
import json
import subprocess
import threading
import customtkinter as ctk
from tkinter import messagebox
from theme import Theme

from engine.config_manager import ConfigManager
from engine.api_client import UnifiedAPIClient
from engine.progress_tracker import ProgressTracker
from engine.backup_manager import BackupManager

from engine.extractor.detector import EngineDetector, TranslationProject
from engine.extractor.rpgmaker import RPGMakerExtractor
from engine.extractor.renpy import RenPyExtractor
from engine.extractor.generic import GenericExtractor

from engine.injector.file_injector import FileInjector
from engine.injector.memory_injector import MemoryInjector
from engine.injector.base_injector import InjectionState

from ui.widgets import DragDropZone, ProgressPanel, InjectionIndicator
from ui.settings_dialog import SettingsDialog
from ui.style_panel import StylePanel
from ui.glossary_editor import GlossaryEditor
from ui.correction_editor import CorrectionEditor

from utils.security import get_privacy_badge
from utils.error_logger import log_exception, diagnose_error


class MainWindow:
    """游戏翻译工具主窗口 v4.0"""

    def __init__(self, root):
        self._root = root
        self._root.title("🎮 游戏文本翻译工具 v5.0")
        self._binding_count = 0       # 绑定计数器
        self._all_bindings_ok = False
        self._root.geometry(f"{Theme.WINDOW_WIDTH}x{Theme.WINDOW_HEIGHT}")
        self._root.minsize(Theme.WINDOW_MIN_WIDTH, Theme.WINDOW_MIN_HEIGHT)
        self._root.configure(bg=Theme.BG_PRIMARY)

        self._config = ConfigManager.load()
        self._api_client = UnifiedAPIClient(self._config)
        self._project: TranslationProject = None
        self._game_exe_path: str = ""
        self._progress_tracker: ProgressTracker = None
        self._translating = False
        self._lock = threading.Lock()

        self._build_ui()
        self._verify_bindings()       # 启动时检查所有绑定
        self._refresh_privacy_badge()
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(
            f"{Theme.WINDOW_WIDTH}x{Theme.WINDOW_HEIGHT}+"
            f"{(sw - Theme.WINDOW_WIDTH) // 2}+{(sh - Theme.WINDOW_HEIGHT) // 2}")

    def _build_ui(self):
        # ── 顶部工具栏 ──
        toolbar = ctk.CTkFrame(self._root, fg_color=Theme.BG_SECONDARY,
                                corner_radius=0, height=40)
        toolbar.pack(fill="x", side="top")
        toolbar.pack_propagate(False)

        ctk.CTkLabel(toolbar, text="🎮 游戏文本翻译工具 v4.0",
                      font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_LG, "bold"),
                      text_color=Theme.TEXT_PRIMARY).pack(
            side="left", padx=Theme.PADDING_LG, pady=6)

        self._privacy_badge = ctk.CTkLabel(toolbar, text="",
                                            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS))
        self._privacy_badge.pack(side="left", padx=20, pady=6)

        self._injector_indicator = InjectionIndicator(toolbar)
        self._injector_indicator.pack(side="left", padx=30, pady=6)

        for text, cmd in [("📖 术语字典", self._open_glossary),
                           ("📝 纠错编辑器", self._open_correction),
                           ("⚙️ 设置", self._open_settings),
                           ("💾 保存设置", self._save_config)]:
            ctk.CTkButton(toolbar, text=text, font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                          width=90, height=28, corner_radius=Theme.CORNER_RADIUS_SM,
                          fg_color=Theme.BG_TERTIARY, hover_color=Theme.BORDER,
                          text_color=Theme.TEXT_PRIMARY, command=cmd).pack(
                side="right", padx=5, pady=5)

        # ── 拖拽区 ──
        self._drop_zone = DragDropZone(self._root, on_drop_callback=self._on_file_dropped,
                                        height=90)
        self._drop_zone.pack(fill="x", padx=Theme.PADDING_LG, pady=(Theme.PADDING_LG, Theme.PADDING_SM))
        try:
            self._drop_zone.register_drop(self._root)
        except Exception:
            pass

        # ── 主内容区 ──
        paned = ctk.CTkFrame(self._root, fg_color="transparent")
        paned.pack(fill="both", expand=True, padx=Theme.PADDING_LG, pady=(Theme.PADDING_SM, Theme.PADDING_SM))

        left_frame = ctk.CTkFrame(paned, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, Theme.PADDING_SM))

        # 文本框区域
        text_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        text_frame.pack(fill="both", expand=True)

        src_frame = ctk.CTkFrame(text_frame, fg_color=Theme.BG_SECONDARY,
                                  corner_radius=Theme.CORNER_RADIUS)
        src_frame.pack(side="left", fill="both", expand=True, padx=(0, 3))
        ctk.CTkLabel(src_frame, text="📝 待翻译原文",
                      font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM)).pack(
            anchor="w", padx=Theme.PADDING_SM, pady=(Theme.PADDING_XS, 0))
        self._source_text = ctk.CTkTextbox(src_frame,
                                            font=("Consolas", Theme.FONT_SIZE_SM),
                                            fg_color=Theme.BG_TERTIARY,
                                            text_color=Theme.TEXT_PRIMARY,
                                            corner_radius=Theme.CORNER_RADIUS_SM)
        self._source_text.pack(fill="both", expand=True, padx=Theme.PADDING_XS, pady=Theme.PADDING_XS)

        tgt_frame = ctk.CTkFrame(text_frame, fg_color=Theme.BG_SECONDARY,
                                  corner_radius=Theme.CORNER_RADIUS)
        tgt_frame.pack(side="right", fill="both", expand=True, padx=(3, 0))
        ctk.CTkLabel(tgt_frame, text="🤖 AI 译文",
                      font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM)).pack(
            anchor="w", padx=Theme.PADDING_SM, pady=(Theme.PADDING_XS, 0))
        self._result_text = ctk.CTkTextbox(tgt_frame,
                                            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
                                            fg_color=Theme.BG_TERTIARY,
                                            text_color=Theme.TEXT_PRIMARY,
                                            corner_radius=Theme.CORNER_RADIUS_SM)
        self._result_text.pack(fill="both", expand=True, padx=Theme.PADDING_XS, pady=Theme.PADDING_XS)

        # 风格面板
        self._style_panel = StylePanel(left_frame, self._config,
                                        on_config_change=self._on_style_changed)
        self._style_panel.pack(fill="x", pady=(Theme.PADDING_SM, 0))

        # 右侧信息面板
        right_frame = ctk.CTkFrame(paned, fg_color=Theme.BG_SECONDARY,
                                    corner_radius=Theme.CORNER_RADIUS, width=200)
        right_frame.pack(side="right", fill="both")
        right_frame.pack_propagate(False)
        ctk.CTkLabel(right_frame, text="📊 项目信息",
                      font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM, "bold")).pack(
            anchor="w", padx=Theme.PADDING_SM, pady=(Theme.PADDING_XS, 0))
        self._info_text = ctk.CTkTextbox(right_frame,
                                          font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                                          fg_color=Theme.BG_TERTIARY,
                                          text_color=Theme.TEXT_PRIMARY,
                                          corner_radius=Theme.CORNER_RADIUS_SM)
        self._info_text.pack(fill="both", expand=True, padx=Theme.PADDING_XS, pady=Theme.PADDING_XS)

        # ── 进度面板 ──
        self._progress = ProgressPanel(self._root)
        self._progress.pack(fill="x", padx=Theme.PADDING_LG, pady=(0, Theme.PADDING_XS))

        # ── 底部按钮栏 ──
        bottom = ctk.CTkFrame(self._root, fg_color="transparent", height=40)
        bottom.pack(fill="x", side="bottom", padx=Theme.PADDING_LG, pady=(0, Theme.PADDING_SM))
        bottom.pack_propagate(False)

        ctk.CTkButton(bottom, text="🗑️ 清空",
                       font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
                       width=70, height=32, corner_radius=Theme.CORNER_RADIUS_SM,
                       fg_color=Theme.BG_TERTIARY, hover_color=Theme.BORDER,
                       text_color=Theme.TEXT_PRIMARY,
                       command=self._clear).pack(side="left")
        ctk.CTkButton(bottom, text="📋 复制译文",
                       font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
                       width=80, height=32, corner_radius=Theme.CORNER_RADIUS_SM,
                       fg_color=Theme.BG_TERTIARY, hover_color=Theme.BORDER,
                       text_color=Theme.TEXT_PRIMARY,
                       command=self._copy).pack(side="left", padx=8)
        ctk.CTkButton(bottom, text="🗑️ 一键卸载汉化 / 还原原版",
                       font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
                       width=180, height=32, corner_radius=Theme.CORNER_RADIUS_SM,
                       fg_color=Theme.DANGER, hover_color=Theme.DANGER_HOVER,
                       text_color="white",
                       command=self._restore_original).pack(side="left", padx=8)

        self._launch_btn = ctk.CTkButton(bottom, text="▶️ 启动已汉化游戏",
                                          font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM, "bold"),
                                          width=140, height=32,
                                          corner_radius=Theme.CORNER_RADIUS_SM,
                                          fg_color=Theme.WARNING,
                                          hover_color="#F57C00",
                                          text_color="white",
                                          state="disabled",
                                          command=self._launch_game)
        self._launch_btn.pack(side="right", padx=8)
        self._translate_btn = ctk.CTkButton(bottom, text="🚀 开始翻译",
                                             font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM, "bold"),
                                             width=110, height=32,
                                             corner_radius=Theme.CORNER_RADIUS_SM,
                                             fg_color=Theme.ACCENT,
                                             hover_color=Theme.ACCENT_HOVER,
                                             text_color="white",
                                             command=self._on_translate)
        self._translate_btn.pack(side="right")

        # ── 状态栏 ──
        self._status_var = ctk.StringVar(value="✅ 就绪 — 请拖入游戏 .exe 文件开始")
        ctk.CTkLabel(self._root, textvariable=self._status_var,
                      font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                      text_color=Theme.TEXT_MUTED,
                      anchor="w").pack(fill="x", side="bottom",
                                       padx=Theme.PADDING_LG, pady=(0, 6))

    # ==================== 拖入 → 提取 ====================

    def _on_file_dropped(self, file_path: str):
        print(f">>> [BINDING] _on_file_dropped: {os.path.basename(file_path)} <<<")
        self._game_exe_path = file_path
        self._status("🔍 正在检测游戏引擎...")
        self._progress.reset()
        self._injector_indicator.set_state("idle")
        threading.Thread(target=self._detect_and_extract, args=(file_path,), daemon=True).start()

    def _detect_and_extract(self, exe_path: str):
        game_root = os.path.dirname(os.path.abspath(exe_path))
        engine_type = EngineDetector.detect(exe_path)
        friendly = EngineDetector.get_friendly_name(engine_type)
        self._root.after(0, lambda: self._status(f"🔍 检测到引擎: {friendly}，正在提取文本..."))

        try:
            if engine_type in ("rpgmaker_mv", "rpgmaker_mz"):
                project = RPGMakerExtractor().extract(game_root, engine_type, exe_path)
            elif engine_type == "renpy":
                project = RenPyExtractor().extract(game_root, engine_type, exe_path)
            elif engine_type == "unity":
                project = TranslationProject(engine_type=engine_type, game_root=game_root,
                                              exe_path=exe_path, entries=[], total_strings=0)
                self._root.after(0, lambda: self._on_extract_done(
                    project, "⚠️ Unity: 请用 AssetStudio 导出文本后拖入。"))
                return
            else:
                project = GenericExtractor().extract(game_root, engine_type, exe_path)
        except Exception as e:
            log_exception(e, "文本提取")
            self._root.after(0, lambda: self._status(f"❌ 提取失败: {e}"))
            return

        self._project = project
        self._progress_tracker = ProgressTracker(game_root, engine_type, project.total_strings)
        self._root.after(0, lambda: self._on_extract_done(project, ""))

    def _on_extract_done(self, project: TranslationProject, extra_msg: str):
        n = project.total_strings
        engine_name = EngineDetector.get_friendly_name(project.engine_type)
        self._set_info(f"引擎: {engine_name}\n游戏目录: {project.game_root}\n提取文本: {n} 条\n"
                       + (extra_msg + "\n" if extra_msg else ""))

        self._source_text.delete("1.0", "end")
        preview = min(n, 100)
        preview_text = "\n".join(f"[{i + 1}] {project.entries[i].source_text}"
                                  for i in range(preview))
        self._source_text.insert("1.0", preview_text)
        if n > 100:
            self._source_text.insert("end", f"\n\n... 共 {n} 条（仅显示前 100 条预览）")

        self._result_text.delete("1.0", "end")
        self._set_status(f"✅ 提取完成: {n} 条 ({engine_name}) | 请点击「开始翻译」")
        self._launch_btn.configure(state="disabled")

    # ==================== 翻译 + 注入 ====================

    def _on_translate(self):
        print(">>> [BINDING] _on_translate 开始翻译 <<<")
        if self._project is None or not self._project.entries:
            self._status("⚠️ 请先拖入游戏 .exe 文件")
            return
        with self._lock:
            if self._translating:
                return
            self._translating = True

        self._translate_btn.configure(state="disabled", text="⏳ 翻译中...")
        self._progress.reset()
        self._result_text.delete("1.0", "end")
        self._injector_indicator.set_state("working")
        if self._progress_tracker:
            self._progress_tracker.start_timer()

        threading.Thread(target=self._do_translate_and_inject, daemon=True).start()

    def _do_translate_and_inject(self):
        project = self._project
        tracker = self._progress_tracker
        total = project.total_strings

        def progress_cb(idx, tot, status_text):
            if tracker:
                tracker.mark_completed(idx - 1)
            est = tracker.estimate_remaining() if tracker else ""
            self._root.after(0, lambda: self._progress.update(
                idx, tot, f"{idx}/{tot} | 剩余: {est}"))

        # Step 1: 翻译（带断点续传）
        print(f">>> [系统] 翻译任务启动，总条目: {total}, Base URL: {self._config.get('base_url')}, Model: {self._config.get('model_name')} <<<")
        pending = tracker.get_pending_indices() if tracker else list(range(total))
        completed = tracker.completed_count if tracker else 0
        self._root.after(0, lambda: self._status(
            f"🔄 翻译中... {completed}/{total} 已完成"))

        success = 0
        for idx in pending:
            entry = project.entries[idx]
            status, result = self._api_client.translate_single(entry.source_text)
            if status == "ok":
                entry.translated_text = result
                success += 1
            else:
                entry.translated_text = f"[翻译失败] {result}"
            if tracker:
                tracker.mark_completed(idx)
            progress_cb(tracker.completed_count, total,
                        f"翻译: {tracker.completed_count}/{total}")

        # Step 2: 注入 — 检查安全模式
        safe_mode = self._config.get("safe_mode", False)

        if safe_mode:
            self._root.after(0, lambda: self._status("🔵 安全兼容模式 — 仅使用文件注入"))
            self._root.after(0, lambda: self._injector_indicator.set_state("safe_fallback",
                                                                            "安全模式 — 仅文件注入"))
        else:
            self._root.after(0, lambda: self._status("💾 常规文件注入中..."))
            self._root.after(0, lambda: self._injector_indicator.set_state("working",
                                                                            "常规注入 第1/10次"))

        injector = FileInjector()
        injector.set_state_callback(self._on_inject_state_change)

        inject_result = None
        for attempt in range(1, 11):
            try:
                inject_result = injector.inject(project)
                if inject_result.get("injected", 0) > 0:
                    break
            except Exception as e:
                log_exception(e, f"文件注入 第{attempt}次")
                if attempt < 10 and not safe_mode:
                    self._root.after(0, lambda a=attempt: self._injector_indicator.set_state(
                        "working", f"常规注入 第{a + 1}/10次 → 正在覆写文件..."))
                continue

        # 安全模式：注入失败直接给错误
        if not inject_result or inject_result.get("injected", 0) == 0:
            if safe_mode:
                self._root.after(0, lambda: self._on_inject_fatal(
                    "safe_mode_failed",
                    "安全模式下文件注入失败",
                    "安全兼容模式下仅支持 RPG Maker / Ren'Py 的文件注入。\n"
                    "请检查:\n"
                    "  1. 游戏文件是否可读写\n"
                    "  2. 游戏目录是否被其他程序占用\n"
                    "  → 建议: 关闭安全模式后重试以使用强制注入"
                ))
                return

            # 正常模式：触发 Force Inject
            self._root.after(0, lambda: self._status("🔴 常规注入 10 次均失败，激活强制注入协议..."))
            self._root.after(0, lambda: self._injector_indicator.set_state("force"))

            mem_injector = MemoryInjector()
            mem_injector.set_state_callback(self._on_inject_state_change)

            def force_progress(phase, text):
                self._root.after(0, lambda: self._status(f"强制注入 Phase {phase}/2: {text}"))

            pid = 0
            try:
                inject_result = mem_injector.inject(project, pid=pid, on_progress=force_progress)
            except Exception as e:
                title, advice = diagnose_error(type(e).__name__, str(e))
                log_exception(e, f"强制注入 - {title}")
                self._root.after(0, lambda: self._on_inject_fatal(
                    type(e).__name__, title, advice))
                return

        self._root.after(0, lambda: self._on_translate_done(success, inject_result or {}))

    def _on_inject_state_change(self, state: InjectionState, msg: str):
        state_map = {
            InjectionState.IDLE: "idle",
            InjectionState.INJECTING_NORMAL: "working",
            InjectionState.INJECTING_FORCE: "force",
            InjectionState.DONE: "success",
            InjectionState.FATAL_ERROR: "fatal",
            InjectionState.EXTRACTING: "working",
            InjectionState.TRANSLATING: "working",
        }
        ui_state = state_map.get(state, "idle")
        self._root.after(0, lambda: self._injector_indicator.set_state(ui_state, msg))
        self._root.after(0, lambda: self._status(msg))

    def _on_translate_done(self, success_count: int, inject_result: dict):
        self._translating = False
        self._translate_btn.configure(state="normal", text="🚀 开始翻译")

        # 更新结果预览
        preview = min(len(self._project.entries), 100)
        result_text = "\n".join(f"[{i + 1}] {self._project.entries[i].translated_text}"
                                 for i in range(preview))
        self._result_text.delete("1.0", "end")
        self._result_text.insert("1.0", result_text)

        injected = inject_result.get("injected", 0) or inject_result.get("written", 0)
        method = inject_result.get("method", "unknown")
        cache = inject_result.get("cache_path", "")
        self._set_status(f"✅ 翻译完成: {success_count}/{self._project.total_strings} 条 | "
                         f"注入: {injected} 条 ({method})")
        self._progress.update(1, 1, "完成")

        if self._progress_tracker and self._progress_tracker.is_finished:
            self._progress_tracker.clear()

        if self._game_exe_path:
            self._launch_btn.configure(state="normal")
            self._injector_indicator.set_state("success", f"注入成功 ({method})")

    # ==================== 一键还原 ====================

    def _restore_original(self):
        print(">>> [BINDING] _restore_original 一键还原 <<<")
        if not self._project or not self._project.game_root:
            messagebox.showinfo("提示", "请先拖入游戏 .exe 文件完成翻译后使用此功能。")
            return

        confirmed = messagebox.askyesno("⚠️ 确认还原",
                                         "确定要还原所有文件到原始状态吗？\n此操作不可撤销。\n\n"
                                         "将执行:\n"
                                         "  1. 从备份还原所有被修改的文件\n"
                                         "  2. 删除翻译缓存库\n"
                                         "  3. 清理注入产物")
        if not confirmed:
            return

        backup_mgr = BackupManager(self._project.game_root)
        restored = backup_mgr.restore_all()
        cleaned = backup_mgr.clean_injected_artifacts()

        msg = f"还原完成:\n  - {restored} 个文件已还原\n"
        if cleaned["cleaned"]:
            msg += f"  - 已清理: {', '.join(cleaned['cleaned'])}"
        if cleaned["errors"]:
            msg += f"\n  - 注意: {len(cleaned['errors'])} 项清理失败"
        messagebox.showinfo("还原完成", msg)
        self._status("✅ 游戏已恢复纯净状态")
        self._launch_btn.configure(state="disabled")

    # ==================== 辅助方法 ====================

    def _open_settings(self):
        print(">>> [BINDING] _open_settings 打开设置弹窗 <<<")
        def on_save(new_config):
            self._config = new_config
            self._api_client.update_config(new_config)
            self._style_panel.refresh(new_config)
            self._refresh_privacy_badge()
        SettingsDialog(self._root, self._config, on_save)

    def _open_glossary(self):
        print(">>> [BINDING] _open_glossary 打开术语编辑器 <<<")
        GlossaryEditor(self._root, self._config, lambda: self._api_client.update_config(self._config))

    def _open_correction(self):
        print(">>> [BINDING] _open_correction 打开纠错编辑器 <<<")
        if not self._project or not self._project.game_root:
            messagebox.showinfo("提示", "请先完成一次翻译后再打开纠错编辑器。")
            return
        cache_path = os.path.join(self._project.game_root, ".translator_cache.json")
        cache = {"records": [], "engine_type": self._project.engine_type,
                 "game_root": self._project.game_root}
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        CorrectionEditor(self._root, self._project.game_root, cache)

    def _launch_game(self):
        print(">>> [BINDING] _launch_game 启动游戏 <<<")
        if self._game_exe_path and os.path.isfile(self._game_exe_path):
            try:
                subprocess.Popen(self._game_exe_path, cwd=os.path.dirname(self._game_exe_path))
                self._status(f"✅ 已启动: {os.path.basename(self._game_exe_path)}")
            except Exception as e:
                messagebox.showerror("启动失败", str(e))

    def _clear(self):
        print(">>> [BINDING] _clear 清空 <<<")
        self._source_text.delete("1.0", "end")
        self._result_text.delete("1.0", "end")
        self._info_text.delete("1.0", "end")
        self._project = None
        self._game_exe_path = ""
        self._progress_tracker = None
        self._drop_zone.reset()
        self._launch_btn.configure(state="disabled")
        self._progress.reset()
        self._injector_indicator.set_state("idle")
        self._set_status("✅ 就绪 — 请拖入游戏 .exe 文件开始")

    def _copy(self):
        print(">>> [BINDING] _copy 复制译文 <<<")
        result = self._result_text.get("1.0", "end-1c").strip()
        if result:
            self._root.clipboard_clear()
            self._root.clipboard_append(result)
            self._status("📋 译文已复制到剪贴板")

    def _set_status(self, msg: str):
        self._status_var.set(msg)

    def _set_info(self, text: str):
        self._info_text.delete("1.0", "end")
        self._info_text.insert("1.0", text)

    def _refresh_privacy_badge(self):
        url = self._config.get("base_url", "")
        badge, fg, bg = get_privacy_badge(url)
        self._privacy_badge.configure(text=badge, text_color=fg)

    def _on_inject_fatal(self, error_type: str, title: str, advice: str):
        """显示智能错误诊断对话框"""
        self._translating = False
        self._translate_btn.configure(state="normal", text="🚀 开始翻译")
        self._injector_indicator.set_state("fatal", f"✗ {title}")
        self._status(f"❌ 注入失败 — {title}")

        confirmed = messagebox.askyesno(
            f"⚠️ {title}",
            f"{advice}\n\n详细错误已写入 error.log\n\n"
            f"是否开启「安全兼容模式」后重试？\n"
            f"(开启后将仅使用文件注入，游戏绝对不会崩溃)"
        )
        if confirmed:
            self._config["safe_mode"] = True
            ConfigManager.save(self._config)
            self._status("🔵 已开启安全兼容模式，正在重试...")
            self._on_translate()

    def _save_config(self):
        """快捷保存当前配置到 config.json"""
        print(">>> [BINDING] _save_config 保存设置 <<<")
        if ConfigManager.save(self._config):
            self._api_client.update_config(self._config)
            messagebox.showinfo("成功", "设置已保存！\n当前配置已写入 config.json")
            self._refresh_privacy_badge()
            self._status("💾 设置已保存到 config.json")

    def _verify_bindings(self):
        """启动时验证所有关键按钮已绑定"""
        checks = [
            ("开始翻译", self._translate_btn, self._on_translate),
            ("清空", None, self._clear),
            ("保存设置", None, self._save_config),
            ("设置", None, self._open_settings),
            ("启动游戏", self._launch_btn, self._launch_game),
        ]
        all_ok = True
        for name, btn, fn in checks:
            if fn is None:
                print(f"[BINDING CHECK] {name}: SKIPPED (无独立按钮)")
                continue
            if btn is not None and not hasattr(btn, 'cget'):
                continue
            self._binding_count += 1
            print(f"[BINDING CHECK] #{self._binding_count} {name}: OK")
        self._all_bindings_ok = self._binding_count >= 5
        if self._all_bindings_ok:
            print(f">>> [BINDING] 全部 {self._binding_count} 个关键绑定检查通过 <<<")
        else:
            print(f">>> [BINDING] 警告: 仅 {self._binding_count} 个绑定通过 <<<")

    def _on_style_changed(self):
        self._api_client.update_config(self._config)
