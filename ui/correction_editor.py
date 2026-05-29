# -*- coding: utf-8 -*-
"""
================================================================================
 玩家译文字典纠错编辑器
================================================================================
 允许玩家手动修正 AI 翻译结果，并实时联动注入到游戏文件。
 从 .translator_cache.json 加载数据，修改后同步更新缓存文件和游戏注入文件。
================================================================================
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from engine.injector.rpgmaker_injector import RPGMakerInjector
from engine.extractor.detector import TextEntry, TranslationProject


class CorrectionEditor(tk.Toplevel):
    """译文字典纠错编辑器"""

    def __init__(self, parent, game_root: str = "", cache_data: dict = None, on_apply_callback=None):
        super().__init__(parent)
        self.title("📝 译文字典纠错编辑器")
        self.geometry("880x500")
        self.resizable(True, True)
        self.transient(parent)

        self._game_root = game_root
        self._cache = cache_data or {"records": [], "engine_type": "", "game_root": game_root}
        self._records = self._cache.get("records", [])
        self._on_apply = on_apply_callback
        self._modified = False

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        # 搜索栏
        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=(10, 5))
        tk.Label(top, text="🔍 搜索:", font=("微软雅黑", 9)).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace("w", lambda *a: self._filter())
        tk.Entry(top, textvariable=self._search_var, font=("微软雅黑", 9), width=30).pack(side="left", padx=5)

        tk.Label(top, text=f"共 {len(self._records)} 条", font=("微软雅黑", 9), fg="#666").pack(side="right")

        # Treeview
        columns = ("src", "ai", "approved", "file")
        self._tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="extended")
        self._tree.heading("src", text="原文 (Source)")
        self._tree.heading("ai", text="AI 译文")
        self._tree.heading("approved", text="✅ 我的修正")
        self._tree.heading("file", text="文件")
        self._tree.column("src", width=220, minwidth=120)
        self._tree.column("ai", width=220, minwidth=120)
        self._tree.column("approved", width=220, minwidth=120)
        self._tree.column("file", width=150, minwidth=100)
        self._tree.pack(fill="both", expand=True, padx=10, pady=5)
        self._tree.bind("<Double-1>", self._on_double_click)

        # 底栏
        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(5, 10))
        tk.Button(bottom, text="↩️ 还原选中", font=("微软雅黑", 9), command=self._revert_selected).pack(side="left")
        tk.Button(bottom, text="✅ 全部确认", font=("微软雅黑", 9), command=self._approve_all).pack(side="left", padx=5)
        tk.Button(bottom, text="📤 导出CSV", font=("微软雅黑", 9), command=self._export_csv).pack(side="left")
        tk.Button(bottom, text="💾 保存修正", font=("微软雅黑", 9, "bold"), bg="#FF9800", fg="white", padx=12, command=self._save).pack(side="right")
        tk.Button(bottom, text="🚀 应用修正并注入游戏", font=("微软雅黑", 9, "bold"), bg="#4CAF50", fg="white", padx=12, command=self._apply_and_inject).pack(side="right", padx=(5, 0))

    def _load_data(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        self._all_iids = []
        for rec in self._records:
            approved = rec.get("approved_text", "") or ""
            is_approved = rec.get("is_approved", False)
            marker = "☑ " if is_approved and approved else ""
            iid = self._tree.insert("", "end", values=(
                rec.get("source_text", ""),
                rec.get("translated_text", ""),
                marker + approved,
                rec.get("file_path", ""),
            ))
            self._all_iids.append(iid)

    def _filter(self):
        keyword = self._search_var.get().lower()
        for iid in self._all_iids:
            if not iid or not self._tree.exists(iid):
                continue
            values = self._tree.item(iid, "values")
            if not keyword or any(keyword in str(v).lower() for v in values):
                self._tree.reattach(iid, "", "end")
            else:
                self._tree.detach(iid)

    def _on_double_click(self, event):
        item = self._tree.selection()
        if not item:
            return
        column = self._tree.identify_column(event.x)
        if column != "#3":  # 只允许编辑"我的修正"列
            return
        bbox = self._tree.bbox(item[0], column)
        if not bbox:
            return
        x, y, w, h = bbox
        values = self._tree.item(item[0], "values")
        current = values[2].replace("☑ ", "")

        edit = tk.Entry(self._tree, font=("微软雅黑", 9))
        edit.insert(0, current)
        edit.place(x=x, y=y, width=w, height=h)

        def on_confirm(event=None):
            new_val = edit.get().strip()
            edit.destroy()
            if new_val != current:
                vals = list(values)
                vals[2] = "☑ " + new_val
                self._tree.item(item[0], values=tuple(vals))
                self._modified = True
                # 更新内存中的记录
                idx = self._all_iids.index(item[0])
                self._records[idx]["approved_text"] = new_val
                self._records[idx]["is_approved"] = True

        edit.bind("<Return>", on_confirm)
        edit.bind("<FocusOut>", on_confirm)
        edit.focus_set()

    def _revert_selected(self):
        for item in self._tree.selection():
            idx = self._all_iids.index(item)
            self._records[idx]["approved_text"] = ""
            self._records[idx]["is_approved"] = False
        self._modified = True
        self._load_data()

    def _approve_all(self):
        for rec in self._records:
            if not rec.get("approved_text"):
                rec["approved_text"] = rec.get("translated_text", "")
            rec["is_approved"] = True
        self._modified = True
        self._load_data()

    def _export_csv(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV文件", "*.csv")])
        if not path:
            return
        import csv
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["原文", "AI译文", "玩家修正", "文件路径"])
            for rec in self._records:
                writer.writerow([
                    rec.get("source_text", ""),
                    rec.get("translated_text", ""),
                    rec.get("approved_text", ""),
                    rec.get("file_path", ""),
                ])
        messagebox.showinfo("成功", "已导出 CSV 文件")

    def _save(self):
        """仅保存缓存文件，不重新注入游戏"""
        cache_path = os.path.join(self._game_root, ".translator_cache.json")
        self._cache["records"] = self._records
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)
        self._modified = False
        messagebox.showinfo("成功", "修正内容已保存到缓存文件。\n请点击「应用修正并注入游戏」以生效。")

    def _apply_and_inject(self):
        """应用修正并重新注入到游戏文件"""
        if not self._game_root or not os.path.isdir(self._game_root):
            messagebox.showerror("错误", "未找到游戏目录")
            return

        # 先保存缓存
        self._save()

        # 重建 TranslationProject 并注入
        engine_type = self._cache.get("engine_type", "")
        entries = []
        for rec in self._records:
            entry = TextEntry(
                file_path=rec.get("file_path", ""),
                key_path=rec.get("key_path", ""),
                source_text=rec.get("source_text", ""),
                translated_text=rec.get("translated_text", ""),
                approved_text=rec.get("approved_text", ""),
                is_approved=rec.get("is_approved", False),
            )
            entries.append(entry)

        project = TranslationProject(
            engine_type=engine_type,
            game_root=self._game_root,
            exe_path="",
            entries=entries,
            total_strings=len(entries),
        )

        if engine_type in ("rpgmaker_mv", "rpgmaker_mz"):
            injector = RPGMakerInjector()
            result = injector.inject(project, apply_corrections=True)
            msg = f"注入完成: {result.get('injected', 0)} 条已更新。\n下次启动游戏即可看到修正后的译文。"
        else:
            msg = f"引擎类型 [{engine_type}] 暂不支持运行时注入修正。\n修正已保存到缓存文件。"

        messagebox.showinfo("注入完成", msg)
        if self._on_apply:
            self._on_apply()