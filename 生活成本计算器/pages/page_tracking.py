# -*- coding: utf-8 -*-
"""page_tracking.py —— 长期跟踪页

关闭程序时存的多次快照，在这里看变化趋势（折线图）+ 历次明细表，
可导出人读文本档案、删除档案。让用户看到"自己有没有在变好"。
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import tracking as T
import gui_widgets as W
from gui_widgets import COLOR_SURPLUS, COLOR_ACCENT, COLOR_DEFICIT


class TrackingPage(ttk.Frame):
    def __init__(self, parent, app=None):
        super().__init__(parent)
        self._app = app
        self._snapshots = []
        self._build()

    def _build(self):
        # 顶部：档案选择
        top = W.CardFrame(self, padding=10)
        top.pack(side="top", fill="x", padx=8, pady=(8, 4))
        ttk.Label(top, text="长期跟踪：看你的结余/存款/成本有没有在变好",
                  style="Header.TLabel").pack(anchor="w", pady=(0, 6))
        row = ttk.Frame(top)
        row.pack(fill="x")
        ttk.Label(row, text="选择档案：").pack(side="left")
        self.var_track = tk.StringVar()
        self.cb_track = ttk.Combobox(row, textvariable=self.var_track, state="readonly",
                                     width=20, values=[])
        self.cb_track.pack(side="left", padx=6)
        self.cb_track.bind("<<ComboboxSelected>>", lambda e: self._load())
        ttk.Button(row, text="刷新列表", command=self._refresh).pack(side="left", padx=6)
        ttk.Label(row, text="（档案在关闭程序时的弹窗里生成）",
                  style="Sub.TLabel").pack(side="left", padx=8)

        # 中部：趋势图
        mid = W.CardFrame(self, padding=8)
        mid.pack(side="top", fill="both", expand=True, padx=8, pady=4)
        ttk.Label(mid, text="变化趋势（绿=月结余 / 蓝=存款 / 橙=月度成本 / 红=月负债 / 紫=结余率%）",
                  style="Header.TLabel").pack(anchor="w", pady=(0, 4))
        self.chart = W.TrendLineChart(mid, height=320)
        self.chart.pack(fill="both", expand=True)

        # 下部：历次明细表 + 操作
        bot = W.CardFrame(self, padding=8)
        bot.pack(side="top", fill="x", padx=8, pady=(4, 8))
        ttk.Label(bot, text="历次记录（最新在上）", style="Header.TLabel").pack(anchor="w", pady=(0, 4))
        self.table = W.ResultTreeview(
            bot,
            columns=[("time", "时间", "w"), ("surplus", "月结余", "e"),
                     ("savings", "存款", "e"), ("cost", "月度成本", "e"),
                     ("debt", "月负债", "e"), ("rate", "结余率", "e")],
            col_widths={"time": 120, "surplus": 100, "savings": 100,
                        "cost": 100, "debt": 100, "rate": 80},
            height=8)
        self.table.pack(fill="x")
        ops = ttk.Frame(bot)
        ops.pack(fill="x", pady=(8, 0))
        ttk.Button(ops, text="导出文本档案另存…",
                   command=self._export_txt).pack(side="left")
        ttk.Button(ops, text="删除该档案",
                   command=self._delete).pack(side="left", padx=6)

        self._refresh()

    def _refresh(self):
        names = T.list_tracks()
        self.cb_track["values"] = names
        cur = self.var_track.get()
        if names and (not cur or cur not in names):
            self.var_track.set(names[0])
        if not names:
            self.var_track.set("")
        self._load()

    def _load(self):
        name = self.var_track.get()
        snaps = T.load_track(name)["snapshots"] if name else []
        self._snapshots = snaps
        labels = [s.get("time", "")[5:] for s in snaps]  # 去年份，留 MM-DD HH:MM

        def vals(key):
            return [s.get("metrics", {}).get(key, 0) for s in snaps]

        self.chart.set_data(labels, [
            ("月结余", vals("surplus"), COLOR_SURPLUS, "left"),
            ("存款", vals("savings"), COLOR_ACCENT, "left"),
            ("月度成本", vals("cost_total"), "#d97706", "left"),
            ("月负债", vals("debt_monthly"), COLOR_DEFICIT, "left"),
            ("结余率%", vals("surplus_rate"), "#8e44ad", "right"),
        ])
        self.table.clear()
        for s in reversed(snaps):  # 最新在上
            m = s.get("metrics", {})
            sp = m.get("surplus", 0)
            sp_s = f"{sp:+,.0f}" if sp else "0"
            self.table.add_row([
                s.get("time", ""),
                sp_s,
                f"{m.get('savings', 0):,.0f}",
                f"{m.get('cost_total', 0):,.0f}",
                f"{m.get('debt_monthly', 0):,.0f}",
                f"{m.get('surplus_rate', 0):.0f}%",
            ])

    def _export_txt(self):
        name = self.var_track.get()
        if not name:
            messagebox.showinfo("提示", "请先选择一个档案。")
            return
        text = T.render_txt(name, self._snapshots)
        path = filedialog.asksaveasfilename(
            title="导出文本档案", defaultextension=".txt",
            initialfile=f"{name}_跟踪档案.txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("已导出", f"文本档案已保存到：\n{path}")
        except OSError as e:
            messagebox.showerror("导出失败", str(e))

    def _delete(self):
        name = self.var_track.get()
        if not name:
            return
        if not messagebox.askyesno("确认删除",
                                   f"确定删除档案「{name}」的全部记录？\n（不可恢复）"):
            return
        T.delete_track(name)
        self._refresh()
