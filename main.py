# -*- coding: utf-8 -*-
"""
================================================================================
 游戏文本翻译工具 v4.0 — 一键启动入口
================================================================================
 使用 CustomTkinter 深色主题 GUI + tkinterdnd2 拖拽支持。
 首次运行自动安装缺失依赖。
================================================================================
"""

import sys
import os
import subprocess


def _ensure_dependencies():
    """检查并安装必要的第三方依赖"""
    deps = {
        "openai": "openai",
        "tkinterdnd2": "tkinterdnd2",
        "customtkinter": "customtkinter",
    }
    for import_name, pip_name in deps.items():
        try:
            __import__(import_name)
        except ImportError:
            print(f"[安装] 正在安装 {pip_name}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pip_name, "-q"])


_ensure_dependencies()


def main():
    from theme import apply_ctk_theme
    apply_ctk_theme()

    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        import tkinter as tk
        root = tk.Tk()
        print("⚠️ tkinterdnd2 未安装，拖拽功能不可用")

    from ui.main_window import MainWindow
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except Exception as e:
        # 全局异常捕获 — 防止 .exe 闪退
        import traceback
        from utils.error_logger import diagnose_error, setup_error_logger
        logger = setup_error_logger()
        logger.error(f"FATAL: {type(e).__name__} — {e}", exc_info=True)

        title, advice = diagnose_error(type(e).__name__, str(e))
        try:
            import tkinter.messagebox as mb
            mb.showerror(
                f"程序崩溃 — {title}",
                f"{advice}\n\n"
                f"原始错误: {e}\n\n"
                f"详细日志已写入 error.log\n"
                f"请联系开发者并附上 error.log 文件"
            )
        except Exception:
            # 连 MessageBox 都弹不出来时，写文件
            crash_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "crash_report.txt"
            )
            with open(crash_path, "w", encoding="utf-8") as f:
                f.write(f"FATAL: {type(e).__name__}\n{e}\n\n")
                traceback.print_exc(file=f)
            input("程序崩溃，详情已写入 crash_report.txt，按回车退出...")
