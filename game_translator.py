# -*- coding: utf-8 -*-
"""
================================================================================
 游戏文本翻译工具 - 主程序 (View + Controller 层)
================================================================================
 功能：
   1. Tkinter 图形化界面，包含双文本框、翻译按钮、设置窗口
   2. 子线程执行 API 翻译，主线程保持 GUI 响应
   3. 状态栏实时显示翻译进度/错误信息
   4. 一键清空文本框
================================================================================

 使用前请先安装依赖:
   pip install openai

 运行方式:
   python game_translator.py
================================================================================
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading

# 导入 Model 层
from translator_core import ConfigManager, TranslationEngine, GlossaryManager


# ==================== 设置窗口（弹窗） ====================

class SettingsDialog:
    """
    API 设置弹窗
    允许用户填写/修改 API Key、Base URL、模型名称，并保存到本地配置。
    """

    def __init__(self, parent: tk.Tk, current_config: dict, on_save_callback):
        """
        参数:
            parent: 父窗口
            current_config: 当前配置字典（含 api_key, base_url, model_name）
            on_save_callback: 保存成功后的回调函数（用于刷新翻译引擎凭证）
        """
        self._parent = parent
        self._config = current_config
        self._on_save_callback = on_save_callback

        # 创建模态弹窗
        self._dialog = tk.Toplevel(parent)
        self._dialog.title("⚙️ API 设置")
        self._dialog.geometry("520x340")
        self._dialog.resizable(False, False)
        self._dialog.transient(parent)          # 设为父窗口的子窗口
        self._dialog.grab_set()                 # 模态：锁定父窗口

        # 窗口居中
        self._dialog.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 520) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 340) // 2
        self._dialog.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        """构建设置窗口的 UI 组件"""
        pad_x = 15
        pad_y = 8

        # ---- API Key ----
        tk.Label(self._dialog, text="API Key:", font=("微软雅黑", 10)).pack(
            anchor="w", padx=pad_x, pady=(pad_y + 5, 0)
        )
        self._api_key_var = tk.StringVar(value=self._config.get("api_key", ""))
        self._api_key_entry = tk.Entry(
            self._dialog,
            textvariable=self._api_key_var,
            show="•",                     # 密码掩码
            font=("Consolas", 10),
            width=55
        )
        self._api_key_entry.pack(fill="x", padx=pad_x, pady=(2, 0))

        # 显示/隐藏勾选框
        self._show_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self._dialog,
            text="显示密钥",
            variable=self._show_key_var,
            command=self._toggle_key_visibility
        ).pack(anchor="w", padx=pad_x, pady=(2, 0))

        # ---- Base URL ----
        tk.Label(self._dialog, text="Base URL:", font=("微软雅黑", 10)).pack(
            anchor="w", padx=pad_x, pady=(pad_y + 3, 0)
        )
        self._base_url_var = tk.StringVar(
            value=self._config.get("base_url", "https://api.deepseek.com")
        )
        tk.Entry(
            self._dialog,
            textvariable=self._base_url_var,
            font=("Consolas", 10),
            width=55
        ).pack(fill="x", padx=pad_x, pady=(2, 0))

        # ---- 模型名称 ----
        tk.Label(self._dialog, text="模型名称:", font=("微软雅黑", 10)).pack(
            anchor="w", padx=pad_x, pady=(pad_y + 3, 0)
        )
        self._model_var = tk.StringVar(
            value=self._config.get("model_name", "deepseek-chat")
        )
        tk.Entry(
            self._dialog,
            textvariable=self._model_var,
            font=("Consolas", 10),
            width=55
        ).pack(fill="x", padx=pad_x, pady=(2, 0))

        # ---- 分隔 + 提示 ----
        tk.Frame(self._dialog, height=1, bg="#ccc").pack(fill="x", padx=pad_x, pady=(15, 5))

        tk.Label(
            self._dialog,
            text="💡 提示: DeepSeek 默认 Base URL 为 https://api.deepseek.com\n"
                 "   模型名称通常为 deepseek-chat 或 deepseek-reasoner",
            font=("微软雅黑", 8),
            fg="#888",
            justify="left"
        ).pack(anchor="w", padx=pad_x, pady=(0, 5))

        # ---- 按钮区域 ----
        btn_frame = tk.Frame(self._dialog)
        btn_frame.pack(fill="x", padx=pad_x, pady=(5, 10))

        tk.Button(
            btn_frame,
            text="💾 保存",
            font=("微软雅黑", 10, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=20,
            command=self._save
        ).pack(side="right", padx=(5, 0))

        tk.Button(
            btn_frame,
            text="取消",
            font=("微软雅黑", 10),
            padx=20,
            command=self._dialog.destroy
        ).pack(side="right")

    def _toggle_key_visibility(self):
        """切换 API Key 的显示/隐藏"""
        if self._show_key_var.get():
            self._api_key_entry.config(show="")
        else:
            self._api_key_entry.config(show="•")

    def _save(self):
        """保存配置"""
        api_key = self._api_key_var.get().strip()
        base_url = self._base_url_var.get().strip()
        model_name = self._model_var.get().strip()

        if not api_key:
            messagebox.showwarning("警告", "API Key 不能为空！", parent=self._dialog)
            return
        if not base_url:
            messagebox.showwarning("警告", "Base URL 不能为空！", parent=self._dialog)
            return
        if not model_name:
            messagebox.showwarning("警告", "模型名称不能为空！", parent=self._dialog)
            return

        success = ConfigManager.save_config(api_key, base_url, model_name)
        if success:
            messagebox.showinfo("成功", "配置已保存！", parent=self._dialog)
            # 回调主窗口以更新翻译引擎
            self._on_save_callback(api_key, base_url, model_name)
            self._dialog.destroy()
        else:
            messagebox.showerror("错误", "配置保存失败，请检查磁盘权限。", parent=self._dialog)


# ==================== 主窗口 ====================

class TranslatorApp:
    """
    游戏翻译工具主窗口 (View + Controller)
    """

    def __init__(self):
        """初始化主窗口、翻译引擎、UI 组件"""
        self._root = tk.Tk()
        self._root.title("🎮 游戏文本翻译工具 - Powered by DeepSeek")
        self._root.geometry("1000x600")
        self._root.minsize(800, 450)

        # ---- 加载配置并初始化翻译引擎 ----
        config = ConfigManager.load_config()
        self._engine = TranslationEngine(
            api_key=config["api_key"],
            base_url=config["base_url"],
            model_name=config["model_name"]
        )

        # ---- 翻译锁：防止用户连续点击"开始翻译" ----
        self._translating = False
        self._lock = threading.Lock()

        # ---- 构建界面 ----
        self._build_ui()
        self._update_status_from_config(config)

        # 窗口居中
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        w = 1000
        h = 600
        self._root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ==================== UI 构建 ====================

    def _build_ui(self):
        """构建完整的 GUI 界面"""

        # ---- 顶部工具栏 ----
        toolbar = tk.Frame(self._root, bg="#f0f0f0", height=40)
        toolbar.pack(fill="x", side="top")
        toolbar.pack_propagate(False)

        tk.Label(
            toolbar,
            text="🎮 游戏文本自动翻译工具",
            font=("微软雅黑", 12, "bold"),
            bg="#f0f0f0"
        ).pack(side="left", padx=15, pady=6)

        # 设置按钮
        tk.Button(
            toolbar,
            text="⚙️ 设置",
            font=("微软雅黑", 9),
            padx=12,
            command=self._open_settings
        ).pack(side="right", padx=15, pady=5)

        # 术语表状态
        self._glossary_label = tk.Label(
            toolbar,
            text="",
            font=("微软雅黑", 9),
            fg="#666",
            bg="#f0f0f0"
        )
        self._glossary_label.pack(side="right", padx=10, pady=6)

        # ---- 主内容区域（左右并排文本框） ----
        main_frame = tk.Frame(self._root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        # 左侧：待翻译原文
        left_frame = tk.LabelFrame(main_frame, text="📝 待翻译原文", font=("微软雅黑", 10))
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self._source_text = scrolledtext.ScrolledText(
            left_frame,
            font=("Consolas", 11),
            wrap="word",
            undo=True,
            relief="flat",
            borderwidth=2
        )
        self._source_text.pack(fill="both", expand=True, padx=5, pady=5)
        # 设置默认占位文本
        self._source_text.insert("1.0", "在此粘贴游戏原文...")
        self._source_text.bind("<FocusIn>", self._clear_placeholder_source)
        self._source_text.bind("<FocusOut>", self._restore_placeholder_source)

        # 右侧：AI 译文
        right_frame = tk.LabelFrame(main_frame, text="🤖 AI 译文", font=("微软雅黑", 10))
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        self._result_text = scrolledtext.ScrolledText(
            right_frame,
            font=("微软雅黑", 11),
            wrap="word",
            relief="flat",
            borderwidth=2,
            state="disabled"            # 只读
        )
        self._result_text.pack(fill="both", expand=True, padx=5, pady=5)

        # ---- 底部操作栏 ----
        bottom_frame = tk.Frame(self._root, height=50)
        bottom_frame.pack(fill="x", side="bottom", padx=10, pady=(5, 5))

        # 清空按钮
        tk.Button(
            bottom_frame,
            text="🗑️ 清空",
            font=("微软雅黑", 10),
            padx=18,
            pady=4,
            command=self._clear_all
        ).pack(side="left")

        # 复制译文按钮
        tk.Button(
            bottom_frame,
            text="📋 复制译文",
            font=("微软雅黑", 10),
            padx=12,
            pady=4,
            command=self._copy_result
        ).pack(side="left", padx=(10, 0))

        # 开始翻译按钮（右侧）
        self._translate_btn = tk.Button(
            bottom_frame,
            text="🚀 开始翻译",
            font=("微软雅黑", 10, "bold"),
            bg="#2196F3",
            fg="white",
            padx=22,
            pady=4,
            command=self._on_translate_click
        )
        self._translate_btn.pack(side="right")

        # ---- 状态栏 ----
        self._status_var = tk.StringVar(value="✅ 就绪 - 请在左侧输入文本后点击「开始翻译」")
        status_bar = tk.Label(
            self._root,
            textvariable=self._status_var,
            font=("微软雅黑", 9),
            fg="#555",
            anchor="w",
            relief="sunken",
            bd=1
        )
        status_bar.pack(fill="x", side="bottom", padx=10, pady=(0, 8))

        # 更新术语表状态
        self._refresh_glossary_status()

    # ==================== 占位文本处理 ====================

    def _clear_placeholder_source(self, event=None):
        """当用户点击左侧文本框时，清除默认占位文本"""
        current = self._source_text.get("1.0", "end-1c")
        if current.strip() == "在此粘贴游戏原文...":
            self._source_text.delete("1.0", "end")

    def _restore_placeholder_source(self, event=None):
        """当左侧文本框失去焦点且为空时，恢复占位文本"""
        current = self._source_text.get("1.0", "end-1c")
        if not current.strip():
            self._source_text.delete("1.0", "end")
            self._source_text.insert("1.0", "在此粘贴游戏原文...")

    # ==================== 核心操作 ====================

    def _on_translate_click(self):
        """
        用户点击「开始翻译」按钮。
        在子线程中执行翻译，避免阻塞 GUI。
        """
        # 防止重复点击
        with self._lock:
            if self._translating:
                return
            self._translating = True

        # 获取原文
        source = self._source_text.get("1.0", "end-1c").strip()
        if not source or source == "在此粘贴游戏原文...":
            self._set_status("⚠️ 请先在左侧输入待翻译的文本。")
            with self._lock:
                self._translating = False
            return

        # UI 反馈：按钮置灰，状态更新
        self._translate_btn.config(state="disabled", text="⏳ 翻译中...")
        self._set_status("🔄 正在调用 DeepSeek API 进行翻译，请稍候...")
        self._clear_result()

        # 启动子线程执行翻译
        thread = threading.Thread(target=self._do_translate, args=(source,), daemon=True)
        thread.start()

    def _do_translate(self, source: str):
        """
        在子线程中执行实际的翻译调用。

        参数:
            source: 待翻译的原文
        """
        status, result = self._engine.translate(source)

        # 回到主线程更新 UI
        if status == "ok":
            self._root.after(0, lambda: self._on_translate_success(result))
        else:
            self._root.after(0, lambda: self._on_translate_error(result))

    def _on_translate_success(self, result: str):
        """翻译成功回调（主线程）"""
        self._set_result_text(result)
        self._set_status("✅ 翻译完成！")
        self._translate_btn.config(state="normal", text="🚀 开始翻译")
        with self._lock:
            self._translating = False

    def _on_translate_error(self, error_msg: str):
        """翻译失败回调（主线程）"""
        self._set_result_text(error_msg)
        self._set_status(f"❌ 翻译失败 - {error_msg}")
        self._translate_btn.config(state="normal", text="🚀 开始翻译")
        with self._lock:
            self._translating = False

    def _clear_all(self):
        """清空所有文本框"""
        self._source_text.delete("1.0", "end")
        self._source_text.insert("1.0", "在此粘贴游戏原文...")
        self._clear_result()

    def _clear_result(self):
        """清空右侧结果框"""
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.config(state="disabled")

    def _set_result_text(self, text: str):
        """设置右侧结果框内容"""
        self._result_text.config(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.insert("1.0", text)
        self._result_text.config(state="disabled")

    def _copy_result(self):
        """将译文复制到剪贴板"""
        result = self._result_text.get("1.0", "end-1c")
        if result.strip():
            self._root.clipboard_clear()
            self._root.clipboard_append(result)
            self._set_status("📋 译文已复制到剪贴板！")
        else:
            self._set_status("⚠️ 没有可复制的内容。")

    # ==================== 设置窗口 ====================

    def _open_settings(self):
        """
        打开设置弹窗。
        回调 on_save 用于在用户保存后更新翻译引擎凭证。
        """
        config = ConfigManager.load_config()

        def on_save(api_key, base_url, model_name):
            self._engine.update_credentials(api_key, base_url, model_name)
            self._update_status_from_config({"api_key": api_key, "base_url": base_url, "model_name": model_name})
            self._refresh_glossary_status()

        SettingsDialog(self._root, config, on_save)

    # ==================== 状态栏与辅助方法 ====================

    def _set_status(self, message: str):
        """更新状态栏文本"""
        self._status_var.set(message)

    def _update_status_from_config(self, config: dict):
        """根据配置更新状态栏提示"""
        if config.get("api_key"):
            model = config.get("model_name", "deepseek-chat")
            self._set_status(f"✅ 就绪 - 当前模型: {model} | 请在左侧输入文本后点击「开始翻译」")
        else:
            self._set_status("⚠️ 请点击右上角「⚙️ 设置」按钮配置 API Key 后再使用。")

    def _refresh_glossary_status(self):
        """刷新术语表状态标签"""
        glossary = GlossaryManager.load_glossary()
        if glossary:
            self._glossary_label.config(text=f"📖 术语表: {len(glossary)} 条")
        else:
            self._glossary_label.config(text="📖 术语表: 未加载")

    # ==================== 启动 ====================

    def run(self):
        """启动 GUI 主循环"""
        self._root.mainloop()


# ==================== 程序入口 ====================

if __name__ == "__main__":
    app = TranslatorApp()
    app.run()