# -*- coding: utf-8 -*-
"""
================================================================================
 CustomTkinter 自定义控件
================================================================================
 拖拽区域 + 进度面板 + 注入模式指示灯
================================================================================
"""
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from theme import Theme


class DragDropZone(ctk.CTkFrame):
    """文件拖拽区域 — 深色圆角虚线边框"""

    def __init__(self, parent, on_drop_callback, **kwargs):
        super().__init__(parent, fg_color=Theme.BG_SECONDARY,
                         corner_radius=Theme.CORNER_RADIUS,
                         border_width=2, border_color=Theme.BORDER, **kwargs)
        self._on_drop = on_drop_callback
        self._label = ctk.CTkLabel(self, text="拖入游戏 .exe 文件\n或点击此处选择文件",
                                    font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_MD),
                                    text_color=Theme.TEXT_MUTED)
        self._label.pack(expand=True)
        self._file_label = ctk.CTkLabel(self, text="",
                                         font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                                         text_color=Theme.ACCENT)
        self._file_label.pack(pady=(0, Theme.PADDING_SM))
        self._label.bind("<Button-1>", self._on_click)
        self._file_label.bind("<Button-1>", self._on_click)
        self.bind("<Button-1>", self._on_click)

    def register_drop(self, tk_root):
        try:
            from tkinterdnd2 import DND_FILES
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop_event)
        except ImportError:
            pass

    def _on_drop_event(self, event):
        fp = event.data
        if fp.startswith("{") and fp.endswith("}"):
            fp = fp[1:-1]
        if fp.lower().endswith(".exe"):
            self.set_file(fp)
            if self._on_drop:
                self._on_drop(fp)

    def _on_click(self, event):
        fp = filedialog.askopenfilename(
            title="选择游戏启动文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")])
        if fp:
            self.set_file(fp)
            if self._on_drop:
                self._on_drop(fp)

    def set_file(self, filepath: str):
        import os
        self._label.configure(text="✅ 已选择游戏文件", text_color=Theme.SUCCESS)
        self._file_label.configure(text=os.path.basename(filepath))

    def reset(self):
        self._label.configure(text="拖入游戏 .exe 文件\n或点击此处选择文件",
                              text_color=Theme.TEXT_MUTED)
        self._file_label.configure(text="")


class ProgressPanel(ctk.CTkFrame):
    """进度面板 — CTkProgressBar + 百分比 + 状态"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._bar = ctk.CTkProgressBar(self, width=500, height=12,
                                        corner_radius=6,
                                        fg_color=Theme.BG_TERTIARY,
                                        progress_color=Theme.ACCENT)
        self._bar.pack(side="left", padx=(0, Theme.PADDING_MD))
        self._bar.set(0)
        self._pct = ctk.CTkLabel(self, text="0%", width=45,
                                  font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                                  text_color=Theme.TEXT_MUTED)
        self._pct.pack(side="right")
        self._status = ctk.CTkLabel(self, text="",
                                     font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                                     text_color=Theme.TEXT_MUTED)
        self._status.pack(side="right", padx=(0, Theme.PADDING_MD))

    def update(self, current: int, total: int, status_text: str = ""):
        if total <= 0:
            return
        self._bar.set(current / total)
        self._pct.configure(text=f"{int(current / total * 100)}%")
        if status_text:
            self._status.configure(text=status_text)

    def reset(self):
        self._bar.set(0)
        self._pct.configure(text="0%")
        self._status.configure(text="")


class InjectionIndicator(ctk.CTkFrame):
    """
    注入模式指示灯。

    状态对应:
      idle      → ⚫ 灰色
      working   → 🟡 黄色
      force     → 🔴 红色闪烁
      success   → 🟢 绿色
      fatal     → 🔴 红色脉冲
    """

    _STATES = {
        "idle":         ("#555555", "注入引擎待命"),
        "working":      ("#FFC107", "常规注入中"),
        "force":        ("#F44336", "⚠ 强制注入协议已激活"),
        "safe_fallback":("#0078D4", "🔵 安全模式 — 仅文件注入"),
        "success":      ("#4CAF50", "注入成功 ✓"),
        "fatal":        ("#F44336", "✗ 注入失败"),
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=Theme.BG_PRIMARY, **kwargs)
        self._color = Theme.INDICATOR_IDLE
        self._blink_id = None
        self._blink_on = True
        self._canvas = tk.Canvas(self, width=20, height=20,
                                  bg=Theme.BG_PRIMARY, highlightthickness=0)
        self._canvas.pack(side="left", padx=(0, 6))
        self._dot = self._canvas.create_oval(2, 2, 18, 18, fill=self._color, outline="")
        self._label = ctk.CTkLabel(self, text="注入引擎待命",
                                    font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                                    text_color=Theme.TEXT_MUTED)
        self._label.pack(side="left")

    def set_state(self, state: str, msg: str = ""):
        color, default_msg = self._STATES.get(state, self._STATES["idle"])
        self._stop_blink()
        self._color = color
        self._canvas.itemconfig(self._dot, fill=color)
        self._label.configure(text=msg or default_msg,
                              text_color=ColorMapper.text_for_state(state))
        if state in ("force", "fatal"):
            self._start_blink()
        elif state == "idle":
            self._label.configure(text_color=Theme.TEXT_MUTED)

    def _start_blink(self):
        if self._blink_id:
            return
        def toggle():
            self._blink_on = not self._blink_on
            fill = self._color if self._blink_on else Theme.BG_PRIMARY
            self._canvas.itemconfig(self._dot, fill=fill)
            self._blink_id = self.after(500, toggle)
        self._blink_on = True
        toggle()

    def _stop_blink(self):
        if self._blink_id:
            self.after_cancel(self._blink_id)
            self._blink_id = None
        self._canvas.itemconfig(self._dot, fill=self._color)


class ColorMapper:
    @staticmethod
    def text_for_state(state: str) -> str:
        return {
            "idle": Theme.TEXT_MUTED,
            "working": Theme.WARNING,
            "force": Theme.DANGER,
            "success": Theme.SUCCESS,
            "fatal": Theme.DANGER,
        }.get(state, Theme.TEXT_MUTED)