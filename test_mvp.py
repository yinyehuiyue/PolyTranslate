# -*- coding: utf-8 -*-
"""MVP 极简测试 — 证明按钮事件绑定正常工作"""
import tkinter as tk

root = tk.Tk()
root.title("MVP 测试 — 按钮事件绑定验证")
root.geometry("400x300")

def on_click():
    """按钮点击回调 — 更新文本框 + 控制台打印"""
    text_box.insert("end", "[OK] 点击成功!\n")
    text_box.see("end")
    print(">>> [MVP Heartbeat] 按钮被点击了！事件绑定正常 <<<")

# 按钮 (command=on_click 就是 Tkinter 的事件绑定)
tk.Button(root, text="测试按钮 (点击我)", font=("微软雅黑", 14),
          bg="#4CAF50", fg="white", padx=20, pady=10,
          command=on_click).pack(pady=20)

# 文本框
text_box = tk.Text(root, font=("微软雅黑", 10), height=8)
text_box.pack(fill="both", expand=True, padx=20, pady=10)
text_box.insert("1.0", "等待按钮点击...\n")

tk.Label(root, text="提示: 点击按钮后，控制台和文本框应同时显示响应",
         font=("微软雅黑", 8), fg="#888").pack()

root.mainloop()