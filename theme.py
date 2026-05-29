# -*- coding: utf-8 -*-
"""
================================================================================
 全局主题配置 — 深色模式极简 UI
================================================================================
 所有颜色、字体、间距、圆角集中管理，便于一键换肤。
 配合 CustomTkinter 使用。
================================================================================
"""


class Theme:
    """深色主题色彩体系"""

    # ── 基础色 ──
    BG_PRIMARY = "#1E1E1E"         # 主背景
    BG_SECONDARY = "#252526"       # 次背景（卡片/面板）
    BG_TERTIARY = "#2D2D30"        # 输入框/选中态背景
    TEXT_PRIMARY = "#D4D4D4"       # 主文字
    TEXT_SECONDARY = "#9CDCFE"     # 强调文字
    TEXT_MUTED = "#6A6A6A"         # 弱化文字

    # ── 功能色 ──
    ACCENT = "#0078D4"             # 科技蓝强调
    ACCENT_HOVER = "#1A8CDC"       # 悬停
    ACCENT_PRESSED = "#005A9E"     # 按下
    SUCCESS = "#4CAF50"            # 成功绿
    WARNING = "#FF9800"            # 警告橙
    DANGER = "#F44336"             # 危险红
    DANGER_HOVER = "#D32F2F"       # 危险红悬停

    # ── 指示灯专用 ──
    INDICATOR_IDLE = "#555555"
    INDICATOR_WORKING = "#FFC107"
    INDICATOR_FORCE = "#F44336"
    INDICATOR_SUCCESS = "#4CAF50"
    INDICATOR_FATAL = "#F44336"

    # ── 隐私徽章 ──
    LOCAL_BADGE_BG = "#1B3A1B"
    LOCAL_BADGE_FG = "#4CAF50"
    CLOUD_BADGE_BG = "#3A2E1B"
    CLOUD_BADGE_FG = "#FF9800"

    # ── 边框 / 分割线 ──
    BORDER = "#3E3E42"
    DIVIDER = "#333337"

    # ── 圆角 ──
    CORNER_RADIUS = 8
    CORNER_RADIUS_SM = 4

    # ── 间距 ──
    PADDING_XS = 4
    PADDING_SM = 8
    PADDING_MD = 12
    PADDING_LG = 16
    PADDING_XL = 24

    # ── 字体 ──
    FONT_FAMILY = "Microsoft YaHei"  # 微软雅黑 (Windows 默认)
    FONT_SIZE_XS = 10
    FONT_SIZE_SM = 11
    FONT_SIZE_MD = 13
    FONT_SIZE_LG = 16
    FONT_SIZE_XL = 20

    # ── 窗口 ──
    WINDOW_WIDTH = 1100
    WINDOW_HEIGHT = 700
    WINDOW_MIN_WIDTH = 920
    WINDOW_MIN_HEIGHT = 580


# ── 导出 CustomTkinter 配置 ──

def apply_ctk_theme():
    """设置 CustomTkinter 全局主题"""
    try:
        import customtkinter as ctk
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        # 覆盖默认颜色
        ctk.ThemeManager.theme["CTkButton"]["fg_color"] = [Theme.ACCENT, Theme.ACCENT]
        ctk.ThemeManager.theme["CTkButton"]["hover_color"] = [Theme.ACCENT_HOVER, Theme.ACCENT_HOVER]
        ctk.ThemeManager.theme["CTk"]["fg_color"] = [Theme.BG_PRIMARY, Theme.BG_PRIMARY]
        ctk.ThemeManager.theme["CTkFrame"]["fg_color"] = [Theme.BG_SECONDARY, Theme.BG_SECONDARY]
        ctk.ThemeManager.theme["CTkEntry"]["fg_color"] = [Theme.BG_TERTIARY, Theme.BG_TERTIARY]
        ctk.ThemeManager.theme["CTkEntry"]["text_color"] = [Theme.TEXT_PRIMARY, Theme.TEXT_PRIMARY]
        ctk.ThemeManager.theme["CTkTextbox"]["fg_color"] = [Theme.BG_TERTIARY, Theme.BG_TERTIARY]
        ctk.ThemeManager.theme["CTkTextbox"]["text_color"] = [Theme.TEXT_PRIMARY, Theme.TEXT_PRIMARY]
    except ImportError:
        pass