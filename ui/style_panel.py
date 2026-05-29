# -*- coding: utf-8 -*-
"""
================================================================================
 翻译风格控制面板
================================================================================
 提供风格预设下拉框 + 自定义提示词多行文本框。
 嵌入在主窗口的侧边栏或折叠面板中。
================================================================================
"""

import tkinter as tk
from tkinter import ttk
from engine.prompt_builder import PromptBuilder
from engine.config_manager import ConfigManager


class StylePanel(tk.LabelFrame):
    """翻译风格控制面板"""

    def __init__(self, parent, config: dict, on_config_change=None, **kwargs):
        super().__init__(parent, text="🎨 翻译风格设置", font=("微软雅黑", 10, "bold"), **kwargs)
        self._config = config
        self._on_config_change = on_config_change
        self._build_ui()

    def _build_ui(self):
        pad_x = 10
        pad_y = 4

        # 风格预设下拉框
        tk.Label(self, text="风格预设:", font=("微软雅黑", 9)).pack(
            anchor="w", padx=pad_x, pady=(pad_y + 2, 0)
        )
        self._style_var = tk.StringVar(value=self._config.get("style_preset", "无特定风格"))
        styles = PromptBuilder.get_style_names()
        self._style_combo = ttk.Combobox(
            self, textvariable=self._style_var, values=styles,
            state="readonly", font=("微软雅黑", 9), width=20,
        )
        self._style_combo.pack(fill="x", padx=pad_x, pady=(2, 0))
        self._style_combo.bind("<<ComboboxSelected>>", self._on_style_change)

        # 自定义提示词
        tk.Label(self, text="自定义提示词 (最高优先级):", font=("微软雅黑", 9)).pack(
            anchor="w", padx=pad_x, pady=(pad_y + 6, 0)
        )
        self._prompt_text = tk.Text(
            self, font=("微软雅黑", 9), wrap="word", height=4,
            relief="sunken", bd=1,
        )
        self._prompt_text.pack(fill="both", expand=True, padx=pad_x, pady=(2, 0))
        self._prompt_text.insert("1.0", self._config.get("custom_prompt", ""))

        # 保存按钮
        tk.Button(
            self, text="💾 保存风格设置", font=("微软雅黑", 9),
            padx=12, command=self._save,
        ).pack(anchor="e", padx=pad_x, pady=(6, pad_y))

    def _on_style_change(self, event=None):
        self._save()

    def _save(self):
        self._config["style_preset"] = self._style_var.get()
        self._config["custom_prompt"] = self._prompt_text.get("1.0", "end-1c").strip()
        ConfigManager.save(self._config)
        if self._on_config_change:
            self._on_config_change()

    def refresh(self, config: dict):
        self._config = config
        self._style_var.set(config.get("style_preset", "无特定风格"))
        self._prompt_text.delete("1.0", "end")
        self._prompt_text.insert("1.0", config.get("custom_prompt", ""))