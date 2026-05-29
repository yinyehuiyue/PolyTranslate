# -*- coding: utf-8 -*-
"""
================================================================================
 术语字典可视化编辑器
================================================================================
 使用 ttk.Treeview 实现术语表的增删改查。
 支持导入/导出 JSON 文件。
================================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from engine.glossary_manager import GlossaryManager
from engine.config_manager import ConfigManager


class GlossaryEditor(tk.Toplevel):
    """术语字典编辑器弹窗"""

    def __init__(self, parent, config: dict, on_save_callback=None):
        super().__init__(parent)
        self.title("📖 术语字典编辑器")
        self.geometry("600x450")
        self.resizable(True, True)
        self.transient(parent)
        self._config = config
        self._glossary = dict(config.get("glossary_entries", {}))
        self._on_save = on_save_callback
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        # 工具栏
        toolbar = tk.Frame(self)
        toolbar.pack(fill="x", padx=10, pady=(10, 5))
        tk.Button(toolbar, text="➕ 添加", font=("微软雅黑", 9), command=self._add_term).pack(side="left", padx=2)
        tk.Button(toolbar, text="🗑️ 删除", font=("微软雅黑", 9), command=self._delete_term).pack(side="left", padx=2)
        tk.Button(toolbar, text="📥 导入JSON", font=("微软雅黑", 9), command=self._import_json).pack(side="left", padx=2)
        tk.Button(toolbar, text="📤 导出JSON", font=("微软雅黑", 9), command=self._export_json).pack(side="left", padx=2)

        # Treeview
        columns = ("src", "tgt")
        self._tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self._tree.heading("src", text="源语言 (Source)")
        self._tree.heading("tgt", text="目标翻译 (Target)")
        self._tree.column("src", width=250, minwidth=150)
        self._tree.column("tgt", width=250, minwidth=150)
        self._tree.pack(fill="both", expand=True, padx=10, pady=5)
        self._tree.bind("<Double-1>", self._on_double_click)

        # 底部
        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(5, 10))
        tk.Button(bottom, text="💾 保存并关闭", font=("微软雅黑", 10, "bold"), bg="#4CAF50", fg="white", padx=16, command=self._save_and_close).pack(side="right")

    def _load_data(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for src, tgt in self._glossary.items():
            self._tree.insert("", "end", values=(src, tgt))

    def _add_term(self):
        src = "new_term"
        tgt = "新术语"
        self._glossary[src] = tgt
        self._tree.insert("", "end", values=(src, tgt))

    def _delete_term(self):
        selected = self._tree.selection()
        if selected:
            values = self._tree.item(selected[0], "values")
            src = values[0]
            self._glossary.pop(src, None)
            self._tree.delete(selected[0])

    def _on_double_click(self, event):
        item = self._tree.selection()
        if not item:
            return
        column = self._tree.identify_column(event.x)
        col_idx = int(column.replace("#", "")) - 1
        bbox = self._tree.bbox(item[0], column)
        if not bbox:
            return
        x, y, w, h = bbox
        values = self._tree.item(item[0], "values")
        current = values[col_idx]

        edit = tk.Entry(self._tree)
        edit.insert(0, current)
        edit.select_range(0, "end")
        edit.place(x=x, y=y, width=w, height=h)

        def on_confirm(event=None):
            new_val = edit.get().strip()
            edit.destroy()
            if new_val and new_val != current:
                vals = list(self._tree.item(item[0], "values"))
                old_src = vals[0]
                vals[col_idx] = new_val
                self._tree.item(item[0], values=tuple(vals))
                if col_idx == 0:
                    self._glossary.pop(old_src, None)
                    self._glossary[new_val] = vals[1]
                else:
                    self._glossary[vals[0]] = new_val

        edit.bind("<Return>", on_confirm)
        edit.bind("<FocusOut>", on_confirm)
        edit.focus_set()

    def _import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON文件", "*.json")])
        if path:
            imported = GlossaryManager.import_from_json(path)
            if imported:
                self._glossary.update(imported)
                self._load_data()
                messagebox.showinfo("成功", f"导入了 {len(imported)} 条术语")

    def _export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON文件", "*.json")])
        if path:
            GlossaryManager.export_to_json(self._glossary, path)
            messagebox.showinfo("成功", "术语表已导出")

    def _save_and_close(self):
        self._config["glossary_entries"] = self._glossary
        ConfigManager.save(self._config)
        if self._on_save:
            self._on_save()
        self.destroy()