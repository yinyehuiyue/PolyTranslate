# -*- coding: utf-8 -*-
"""
================================================================================
 API 设置对话框 v5.0
================================================================================
 功能:
   - 模型厂商下拉 (OpenAI兼容/DeepSeek/Ollama/LM Studio/自定义)
   - 模型名称可编辑下拉 (20+ 预置 + 手动输入)
   - 每个字段独立 [💾] 保存按钮
   - 本地 Ollama/LM Studio 自动隐藏 API Key
   - 隐私徽章 + 安全兼容模式
================================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
from engine.config_manager import ConfigManager
from utils.security import get_privacy_badge, mask_api_key


class SettingsDialog:
    """API 设置模态弹窗 v5.0"""

    def __init__(self, parent, current_config: dict, on_save_callback):
        self._parent = parent
        self._config = dict(current_config)
        self._on_save = on_save_callback

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("⚙️ API 设置 v5.0")
        self._dialog.geometry("580x560")
        self._dialog.resizable(False, False)
        self._dialog.transient(parent)
        self._dialog.grab_set()
        self._dialog.configure(bg="#1E1E1E")

        x = parent.winfo_rootx() + (parent.winfo_width() - 580) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 560) // 2
        self._dialog.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        pad_x = 16
        bg = "#1E1E1E"
        fg = "#D4D4D4"
        entry_bg = "#2D2D30"

        # ── 隐私徽章 ──
        url = self._config.get("base_url", "")
        badge_text, badge_fg, badge_bg = get_privacy_badge(url)
        badge_frame = tk.Frame(self._dialog, bg=badge_bg, height=28)
        badge_frame.pack(fill="x", padx=pad_x, pady=(12, 0))
        badge_frame.pack_propagate(False)
        self._badge_frame = badge_frame
        self._badge_label = tk.Label(badge_frame, text=badge_text,
                                      font=("微软雅黑", 9, "bold"),
                                      fg=badge_fg, bg=badge_bg)
        self._badge_label.pack(expand=True)

        def _refresh_badge():
            url = self._url_var.get()
            t, f, b = get_privacy_badge(url)
            self._badge_frame.configure(bg=b)
            self._badge_label.configure(text=t, fg=f, bg=b)

        # ── 模型厂商下拉 ──
        tk.Label(self._dialog, text="模型厂商:", font=("微软雅黑", 10, "bold"),
                 fg=fg, bg=bg).pack(anchor="w", padx=pad_x, pady=(14, 0))

        self._provider_var = tk.StringVar(value=self._config.get("provider", "OpenAI 兼容 (万能)"))
        providers = list(ConfigManager.PROVIDER_PRESETS.keys())
        self._provider_combo = ttk.Combobox(self._dialog, textvariable=self._provider_var,
                                             values=providers, state="readonly",
                                             font=("微软雅黑", 10), width=52)
        self._provider_combo.pack(fill="x", padx=pad_x, pady=(2, 0))
        self._provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        # ── Base URL ──
        row1 = tk.Frame(self._dialog, bg=bg)
        row1.pack(fill="x", padx=pad_x, pady=(10, 0))
        tk.Label(row1, text="Base URL:", font=("微软雅黑", 9), fg=fg, bg=bg).pack(side="left")
        tk.Button(row1, text="💾", font=("微软雅黑", 8), bg="#4CAF50", fg="white",
                  padx=6, command=self._save_url).pack(side="right")

        self._url_var = tk.StringVar(value=url)
        self._url_entry = tk.Entry(self._dialog, textvariable=self._url_var,
                                    font=("Consolas", 10), bg=entry_bg, fg=fg,
                                    insertbackground=fg, width=56)
        self._url_entry.pack(fill="x", padx=pad_x, pady=(2, 0))
        self._url_entry.bind("<KeyRelease>", lambda e: _refresh_badge())

        # ── 模型名称 (可编辑下拉) ──
        row2 = tk.Frame(self._dialog, bg=bg)
        row2.pack(fill="x", padx=pad_x, pady=(10, 0))
        tk.Label(row2, text="模型名称:", font=("微软雅黑", 9), fg=fg, bg=bg).pack(side="left")
        tk.Button(row2, text="💾", font=("微软雅黑", 8), bg="#4CAF50", fg="white",
                  padx=6, command=self._save_model).pack(side="right")

        self._model_var = tk.StringVar(value=self._config.get("model_name", "gpt-4o"))
        self._model_combo = ttk.Combobox(self._dialog, textvariable=self._model_var,
                                          values=ConfigManager.MODEL_OPTIONS,
                                          font=("Consolas", 10), width=52)
        self._model_combo.pack(fill="x", padx=pad_x, pady=(2, 0))

        # ── API Key ──
        self._key_container = tk.Frame(self._dialog, bg=bg)
        self._key_container.pack(fill="x", padx=pad_x, pady=(10, 0))

        row3 = tk.Frame(self._key_container, bg=bg)
        row3.pack(fill="x")
        tk.Label(row3, text="API Key:", font=("微软雅黑", 9), fg=fg, bg=bg).pack(side="left")
        self._show_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(row3, text="显示", variable=self._show_key_var,
                       command=self._toggle_key, font=("微软雅黑", 7),
                       fg="#888", bg=bg, selectcolor=bg).pack(side="right", padx=(2, 0))
        tk.Button(row3, text="💾", font=("微软雅黑", 8), bg="#4CAF50", fg="white",
                  padx=6, command=self._save_key).pack(side="right", padx=2)

        self._key_var = tk.StringVar(value=self._config.get("api_key", ""))
        self._key_entry = tk.Entry(self._key_container, textvariable=self._key_var,
                                    show="•", font=("Consolas", 10),
                                    bg=entry_bg, fg=fg, insertbackground=fg, width=56)
        self._key_entry.pack(fill="x", pady=(2, 0))

        tk.Label(self._key_container, text="⚠️ 本地模型可留空，程序自动填入占位符",
                 font=("微软雅黑", 7), fg="#E65100", bg=bg).pack(anchor="w", padx=8)

        masked = mask_api_key(self._config.get("api_key", ""))
        tk.Label(self._key_container, text=f"当前已保存: {masked}",
                 font=("微软雅黑", 7), fg="#888", bg=bg).pack(anchor="w", padx=8, pady=(0, 4))

        # ── 安全兼容模式 ──
        tk.Frame(self._dialog, height=1, bg="#3E3E42").pack(fill="x", padx=pad_x, pady=(12, 0))
        tk.Label(self._dialog, text="🛡️ 安全兼容模式", font=("微软雅黑", 9, "bold"),
                 fg=fg, bg=bg).pack(anchor="w", padx=pad_x, pady=(6, 0))
        self._safe_mode_var = tk.BooleanVar(value=self._config.get("safe_mode", False))
        tk.Checkbutton(self._dialog, text="启用 (禁用所有内存注入，游戏不会崩溃)",
                       variable=self._safe_mode_var, font=("微软雅黑", 8),
                       fg="#FF9800", bg=bg, selectcolor=bg).pack(anchor="w", padx=pad_x + 12)

        # ── 底部按钮 ──
        tk.Frame(self._dialog, height=1, bg="#3E3E42").pack(fill="x", padx=pad_x, pady=(10, 0))
        btn_frame = tk.Frame(self._dialog, bg=bg)
        btn_frame.pack(fill="x", padx=pad_x, pady=(10, 12))
        tk.Button(btn_frame, text="💾 保存全部", font=("微软雅黑", 10, "bold"),
                  bg="#4CAF50", fg="white", padx=18, command=self._save_all).pack(side="right", padx=4)
        tk.Button(btn_frame, text="取消", font=("微软雅黑", 10),
                  bg="#555", fg="white", padx=14,
                  command=self._dialog.destroy).pack(side="right")

        # 初始显隐
        self._on_provider_change()

    # ── 单个字段保存 ──

    def _save_to_config_and_notify(self):
        self._config["provider"] = self._provider_var.get()
        self._config["base_url"] = self._url_var.get().strip()
        self._config["model_name"] = self._model_var.get().strip()
        self._config["api_key"] = self._key_var.get().strip()
        self._config["safe_mode"] = self._safe_mode_var.get()
        if ConfigManager.save(self._config):
            self._on_save(self._config)

    def _save_url(self):
        self._save_to_config_and_notify()
        messagebox.showinfo("成功", "Base URL 已保存！", parent=self._dialog)

    def _save_model(self):
        self._save_to_config_and_notify()
        messagebox.showinfo("成功", "模型名称已保存！", parent=self._dialog)

    def _save_key(self):
        self._save_to_config_and_notify()
        messagebox.showinfo("成功", "API Key 已保存！", parent=self._dialog)

    def _save_all(self):
        self._save_to_config_and_notify()
        messagebox.showinfo("成功", "全部设置已保存！", parent=self._dialog)
        self._dialog.destroy()

    # ── 厂商切换联动 ──

    def _on_provider_change(self, event=None):
        provider = self._provider_var.get()
        preset = ConfigManager.PROVIDER_PRESETS.get(provider, ("", ""))
        self._url_var.set(preset[0])
        if preset[1]:
            self._model_var.set(preset[1])

        url = self._url_var.get()
        t, f, b = get_privacy_badge(url)
        self._badge_frame.configure(bg=b)
        self._badge_label.configure(text=t, fg=f, bg=b)

        # Ollama/LM Studio/vLLM → 隐藏 API Key
        if "本地" in provider:
            self._key_container.pack_forget()
        else:
            self._key_container.pack(fill="x", padx=16, pady=(10, 0),
                                      after=self._model_combo)

    def _toggle_key(self):
        self._key_entry.config(show="" if self._show_key_var.get() else "•")