# -*- coding: utf-8 -*-
"""
page_debt.py —— 借贷真相（5 个标签页，补债务信息差）

底层劳动者最常踩的坑之一就是债务。本页用一个 Notebook 把 5 个相关工具放在一起：
  ① 反算真实年化   —— 识破「日息万三 / 月费率0.7%」的真实成本（IRR）
  ② 还款方式对比   —— 等额本息 vs 等本等息（消费分期固定手续费陷阱）
  ③ 可承受负债上限 —— 按月结余算能借多少，超了警告（债务雪崩的起点）
  ④ 多笔债怎么还   —— 雪球法 vs 雪崩法；最低还款盖不住利息的失控检测
  ⑤ 以贷养贷螺旋   —— 利滚利的指数增长警示

业务逻辑全在 calc_engine 的纯函数里，本文件只负责输入/展示。
"""
import json
import os

import tkinter as tk
from tkinter import ttk

import calc_engine as E
import profile as P
import gui_widgets as W


class DebtPage(ttk.Frame):
    def __init__(self, parent, app=None):
        super().__init__(parent)
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=8, pady=8)
        self._build_apr()
        self._build_method_compare()
        self._build_affordable()
        self._build_snowball()
        self._build_spiral()
        self._build_health()
        self._nb.select(0)

    # ---------- 通用：只读解读 Text ----------
    def _make_note(self, parent, height=6, grid=None):
        return W.readonly_note(parent, height=height, grid=grid)

    def _set_note(self, tw, text):
        tw.config(state="normal")
        tw.delete("1.0", "end")
        tw.insert("1.0", text)
        tw.config(state="disabled")

    # ============================================================
    # ① 反算真实年化（原功能，整体保留）
    # ============================================================
    def _build_apr(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text="① 反算真实年化")
        sf = W.ScrollableFrame(tab); sf.pack(fill="both", expand=True)
        c = sf.inner

        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="反算借贷真实年化", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Label(form,
                  text="网贷、信用卡分期常说「日息万三」「月费率0.7%」，听着低，"
                       "但折成真实年化（IRR）往往高得吓人。填下面三项即可现原形。",
                  style="Sub.TLabel", wraplength=560, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(form, text="借款本金（元）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_principal = tk.StringVar(value="10000")
        ttk.Entry(form, textvariable=self.var_principal, width=14).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="每月还款（元）：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_monthly = tk.StringVar(value="900")
        ttk.Entry(form, textvariable=self.var_monthly, width=14).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="期数（月）：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_periods = tk.IntVar(value=12)
        ttk.Spinbox(form, from_=1, to=120, textvariable=self.var_periods, width=8).grid(
            row=4, column=1, sticky="w")
        ttk.Button(form, text="反算真实年化", command=self.on_apr_compute).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(12, 2))

        res = W.CardFrame(c, padding=10)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        res.columnconfigure(0, weight=1)
        ttk.Label(res, text="真实年化利率", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        self.lbl_apr = ttk.Label(res, text="—", font=W.FONT_BIG, foreground=W.COLOR_ACCENT)
        self.lbl_apr.grid(row=1, column=0, sticky="w", pady=(0, 4))
        self.lbl_apr_level = ttk.Label(res, text="", font=W.FONT_RESULT)
        self.lbl_apr_level.grid(row=2, column=0, sticky="w")
        ttk.Separator(res, orient="horizontal").grid(row=3, column=0, sticky="ew", pady=8)
        self.lbl_apr_detail = ttk.Label(res, text="", font=W.FONT, justify="left")
        self.lbl_apr_detail.grid(row=4, column=0, sticky="w")
        ttk.Label(res, text="白话解读与维权提示", style="Header.TLabel").grid(
            row=5, column=0, sticky="w", pady=(10, 4))
        self.txt_apr = self._make_note(res, height=5, grid=dict(row=6, column=0, sticky="ew"))
        ttk.Button(res, text="生成「问 AI」的提示词", style="AskAI.TButton",
                   command=self._open_apr_prompt).grid(row=7, column=0, sticky="w", pady=(8, 0))

    def on_apr_compute(self):
        try:
            p = float(self.var_principal.get())
            m = float(self.var_monthly.get())
            n = int(self.var_periods.get())
        except ValueError:
            self._set_note(self.txt_apr, "请输入有效的数字。")
            return
        r = E.compute_loan_apr(p, m, n)
        if "error" in r:
            self.lbl_apr.config(text="—", foreground=W.COLOR_DEFICIT)
            self.lbl_apr_level.config(text="")
            self.lbl_apr_detail.config(text="")
            self._set_note(self.txt_apr, r["error"])
            return
        color = {"极高": W.COLOR_DEFICIT, "高利贷": W.COLOR_DEFICIT,
                 "偏高": "#e67e22", "正常": W.COLOR_SURPLUS}.get(r["level"], "#222")
        self.lbl_apr.config(text=f"{r['annual_irr']*100:.1f} %", foreground=color)
        self.lbl_apr_level.config(text=f"评级：{r['level']}", foreground=color)
        self.lbl_apr_detail.config(
            text=(f"名义年化（机构常用口径）：{r['nominal_apr']*100:.1f}%\n"
                  f"总还款：{r['total_payment']:,.0f} 元　｜　总利息：{r['interest']:,.0f} 元"
                  f"（占本金 {r['interest_ratio']*100:.0f}%）"))
        self._set_note(self.txt_apr, r["note"])

    # ============================================================
    # ② 还款方式对比
    # ============================================================
    def _build_method_compare(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text="② 还款方式对比")
        sf = W.ScrollableFrame(tab); sf.pack(fill="both", expand=True)
        c = sf.inner

        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="等额本息 vs 等本等息", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Label(form,
                  text="同样是「借1万、12期」，消费分期（等本等息/固定手续费）"
                       "比银行房贷（等额本息）贵得多——它的手续费按初始本金收、"
                       "不随你还的钱递减。填三项看真实差距。",
                  style="Sub.TLabel", wraplength=560, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(form, text="借款本金（元）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_cmp_p = tk.StringVar(value="10000")
        ttk.Entry(form, textvariable=self.var_cmp_p, width=14).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="名义年化（%，机构报价）：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_cmp_apr = tk.StringVar(value="18")
        ttk.Entry(form, textvariable=self.var_cmp_apr, width=14).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="期数（月）：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_cmp_n = tk.IntVar(value=12)
        ttk.Spinbox(form, from_=1, to=120, textvariable=self.var_cmp_n, width=8).grid(
            row=4, column=1, sticky="w")
        ttk.Button(form, text="对比两种方式", command=self.on_compare_compute).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(12, 2))

        res = W.CardFrame(c, padding=10)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        res.columnconfigure(0, weight=1)
        self.lbl_cmp_diff = ttk.Label(res, text="—", font=W.FONT_BIG, foreground=W.COLOR_ACCENT)
        self.lbl_cmp_diff.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.cmp_tree = W.ResultTreeview(
            res,
            columns=[("method", "还款方式", "w"), ("monthly", "月供(元)", "e"),
                     ("interest", "总利息(元)", "e"), ("total", "总还款(元)", "e"),
                     ("apr", "真实年化", "e")],
            col_widths={"method": 170, "monthly": 100, "interest": 110,
                        "total": 110, "apr": 100},
            height=4)
        self.cmp_tree.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(res, text="白话解读", style="Header.TLabel").grid(
            row=2, column=0, sticky="w", pady=(4, 4))
        self.txt_cmp = self._make_note(res, height=7, grid=dict(row=3, column=0, sticky="ew"))
        ttk.Button(res, text="生成「问 AI」的提示词", style="AskAI.TButton",
                   command=self._open_compare_prompt).grid(row=4, column=0, sticky="w", pady=(8, 0))

    def on_compare_compute(self):
        try:
            p = float(self.var_cmp_p.get())
            apr = float(self.var_cmp_apr.get()) / 100
            n = int(self.var_cmp_n.get())
        except ValueError:
            self._set_note(self.txt_cmp, "请输入有效的数字。")
            return
        r = E.compare_loan_methods(p, apr, n)
        if "error" in r:
            self.lbl_cmp_diff.config(text="—", foreground=W.COLOR_DEFICIT)
            self.cmp_tree.clear()
            self._set_note(self.txt_cmp, r["error"])
            return
        ep = r["equal_payment"]
        epf = r["equal_principal_flat"]
        self.cmp_tree.clear()
        self.cmp_tree.add_row(["等额本息（银行房贷口径）",
                               f"{ep['monthly']:,.0f}", f"{ep['total_interest']:,.0f}",
                               f"{ep['total_payment']:,.0f}", f"{ep['annual_irr']*100:.1f}%"])
        self.cmp_tree.add_row(["等本等息（消费分期/手续费制）",
                               f"{epf['monthly']:,.0f}", f"{epf['total_interest']:,.0f}",
                               f"{epf['total_payment']:,.0f}", f"{epf['annual_irr']*100:.1f}%"],
                              tag="deficit")
        diff_apr = epf["annual_irr"] - ep["annual_irr"]
        self.lbl_cmp_diff.config(
            text=f"等本等息真实年化比等额本息高 {diff_apr*100:.1f} 个百分点",
            foreground=W.COLOR_DEFICIT)
        self._set_note(self.txt_cmp, r["note"])

    # ============================================================
    # ③ 可承受负债上限
    # ============================================================
    def _build_affordable(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text="③ 可承受负债上限")
        sf = W.ScrollableFrame(tab); sf.pack(fill="both", expand=True)
        c = sf.inner

        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="你最多能借多少（不压垮自己）", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Label(form,
                  text="按经验线，月还款别超过你能自由支配的钱（月结余）的一半。"
                       "先算清上限，再决定借不借——别等借完了才发现还不起。",
                  style="Sub.TLabel", wraplength=560, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(form, text="月结余（元，收入−必要开支）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_aff_surplus = tk.StringVar(value="2000")
        ttk.Entry(form, textvariable=self.var_aff_surplus, width=14).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="名义年化（%）：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_aff_apr = tk.StringVar(value="18")
        ttk.Entry(form, textvariable=self.var_aff_apr, width=14).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="期数（月）：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_aff_n = tk.IntVar(value=24)
        ttk.Spinbox(form, from_=1, to=120, textvariable=self.var_aff_n, width=8).grid(
            row=4, column=1, sticky="w")
        ttk.Label(form, text="月薪（元，可选）：").grid(row=5, column=0, sticky="w", pady=3)
        self.var_aff_income = tk.StringVar(value="")
        ttk.Entry(form, textvariable=self.var_aff_income, width=14).grid(row=5, column=1, sticky="w")
        ttk.Button(form, text="算我最多能借多少", command=self.on_affordable_compute).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(12, 2))

        res = W.CardFrame(c, padding=10)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        res.columnconfigure(0, weight=1)
        ttk.Label(res, text="可承受借款本金上限", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        self.lbl_aff_max = ttk.Label(res, text="—", font=W.FONT_BIG, foreground=W.COLOR_SURPLUS)
        self.lbl_aff_max.grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.lbl_aff_detail = ttk.Label(res, text="", font=W.FONT_RESULT, justify="left")
        self.lbl_aff_detail.grid(row=2, column=0, sticky="w")
        ttk.Label(res, text="白话解读", style="Header.TLabel").grid(
            row=3, column=0, sticky="w", pady=(10, 4))
        self.txt_aff = self._make_note(res, height=7, grid=dict(row=4, column=0, sticky="ew"))
        ttk.Button(res, text="生成「问 AI」的提示词", style="AskAI.TButton",
                   command=self._open_affordable_prompt).grid(row=5, column=0, sticky="w", pady=(8, 0))

    def on_affordable_compute(self):
        try:
            surplus = float(self.var_aff_surplus.get())
            apr = float(self.var_aff_apr.get()) / 100
            n = int(self.var_aff_n.get())
        except ValueError:
            self._set_note(self.txt_aff, "请输入有效的数字。")
            return
        inc_str = self.var_aff_income.get().strip()
        income = float(inc_str) if inc_str else None
        r = E.compute_affordable_debt(surplus, apr, n, income=income)
        if "error" in r:
            self.lbl_aff_max.config(text="—", foreground=W.COLOR_DEFICIT)
            self.lbl_aff_detail.config(text="")
            self._set_note(self.txt_aff, r["error"])
            return
        self.lbl_aff_max.config(text=f"{r['max_principal']:,.0f} 元", foreground=W.COLOR_SURPLUS)
        self.lbl_aff_detail.config(
            text=(f"月还款上限：{r['max_monthly']:,.0f} 元/月（约占月结余 50%）\n"
                  f"更保守（30%档）：可借 {r['safe_principal']:,.0f} 元"))
        self._set_note(self.txt_aff, r["note"])

    # ============================================================
    # ④ 多笔债：雪球法 vs 雪崩法
    # ============================================================
    def _build_snowball(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text="④ 多笔债怎么还")
        sf = W.ScrollableFrame(tab); sf.pack(fill="both", expand=True)
        c = sf.inner

        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        ttk.Label(form, text="雪球法 vs 雪崩法", style="Header.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(form,
                  text="多笔债时，除了每笔还最低，把每月挤得出的余钱集中砸向一笔——"
                       "砸余额最小的叫雪球法（先尝结清甜头），砸利率最高的叫雪崩法"
                       "（总利息最少）。下方对比两种，看差多少。",
                  style="Sub.TLabel", wraplength=600, justify="left").pack(anchor="w", pady=(0, 8))

        # 表头
        rows_hdr = ttk.Frame(form)
        rows_hdr.pack(fill="x", pady=(0, 2))
        for i, t in enumerate(["债务名称", "当前余额(元)", "年化(%)", "最低月还(元)"]):
            ttk.Label(rows_hdr, text=t, style="Sub.TLabel", width=12).grid(
                row=0, column=i, padx=2, sticky="w")
        self._rows_frame = ttk.Frame(form)
        self._rows_frame.pack(fill="x")
        self._debt_rows = []
        self._add_debt_row(("信用卡", "3000", "18", "300"))
        self._add_debt_row(("网贷", "10000", "36", "500"))
        ttk.Button(form, text="+ 加一笔债",
                   command=lambda: self._add_debt_row(("", "", "", ""))).pack(anchor="w", pady=(6, 6))

        opt = ttk.Frame(form)
        opt.pack(fill="x", pady=4)
        ttk.Label(opt, text="还清顺序按哪种展示：").pack(side="left")
        self.var_snow_strategy = tk.StringVar(value="avalanche")
        ttk.Radiobutton(opt, text="雪崩法", value="avalanche",
                        variable=self.var_snow_strategy).pack(side="left", padx=8)
        ttk.Radiobutton(opt, text="雪球法", value="snowball",
                        variable=self.var_snow_strategy).pack(side="left", padx=8)

        ttk.Label(form, text="每月额外多还（元，集中砸向目标债，这是能不能早还清的关键）：").pack(
            anchor="w", pady=(6, 0))
        self.var_snow_extra = tk.StringVar(value="500")
        ttk.Entry(form, textvariable=self.var_snow_extra, width=14).pack(anchor="w")
        ttk.Button(form, text="开始模拟", command=self.on_snowball_compute).pack(fill="x", pady=(12, 2))

        res = W.CardFrame(c, padding=10)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        res.columnconfigure(0, weight=1)
        self.lbl_snow_summary = ttk.Label(
            res, text="—", font=W.FONT_BIG, foreground=W.COLOR_ACCENT, justify="left")
        self.lbl_snow_summary.grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(res, text="还清顺序（按上方所选策略）", style="Header.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 4))
        self.snow_tree = W.ResultTreeview(
            res,
            columns=[("seq", "顺序", "center"), ("name", "债务", "w"),
                     ("month", "第几月还清", "center")],
            col_widths={"seq": 60, "name": 200, "month": 140}, height=6)
        self.snow_tree.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.txt_snow = self._make_note(res, height=6, grid=dict(row=3, column=0, sticky="ew"))
        ttk.Button(res, text="生成「问 AI」的提示词", style="AskAI.TButton",
                   command=self._open_snowball_prompt).grid(row=4, column=0, sticky="w", pady=(8, 0))

    def _add_debt_row(self, default):
        self._debt_rows.append({
            "name": tk.StringVar(value=default[0]),
            "balance": tk.StringVar(value=default[1]),
            "rate": tk.StringVar(value=default[2]),
            "min": tk.StringVar(value=default[3]),
        })
        self._rebuild_debt_rows()

    def _del_debt_row(self, idx):
        if len(self._debt_rows) <= 1:
            return
        self._debt_rows.pop(idx)
        self._rebuild_debt_rows()

    def _rebuild_debt_rows(self):
        for w in self._rows_frame.winfo_children():
            w.destroy()
        widths = [12, 12, 8, 10]
        for i, row in enumerate(self._debt_rows):
            ttk.Entry(self._rows_frame, textvariable=row["name"], width=widths[0]).grid(
                row=i, column=0, padx=2, pady=2)
            ttk.Entry(self._rows_frame, textvariable=row["balance"], width=widths[1]).grid(
                row=i, column=1, padx=2, pady=2)
            ttk.Entry(self._rows_frame, textvariable=row["rate"], width=widths[2]).grid(
                row=i, column=2, padx=2, pady=2)
            ttk.Entry(self._rows_frame, textvariable=row["min"], width=widths[3]).grid(
                row=i, column=3, padx=2, pady=2)
            ttk.Button(self._rows_frame, text="×", width=3,
                       command=lambda i=i: self._del_debt_row(i)).grid(row=i, column=4, padx=2)

    def on_snowball_compute(self):
        debts = []
        for i, row in enumerate(self._debt_rows):
            bal_s = row["balance"].get().strip()
            if not bal_s:
                continue  # 空行跳过
            try:
                debts.append({
                    "name": (row["name"].get().strip() or f"债{i+1}"),
                    "balance": float(bal_s),
                    "annual_rate": float(row["rate"].get()) / 100,
                    "min_monthly": float(row["min"].get()),
                })
            except ValueError:
                self._set_note(self.txt_snow, f"第 {i+1} 行有非数字输入，请检查余额/年化/月还。")
                return
        if not debts:
            self._set_note(self.txt_snow, "请至少填入一笔债（余额不能为空）。")
            return
        try:
            extra = float(self.var_snow_extra.get())
        except ValueError:
            self._set_note(self.txt_snow, "「每月额外多还」请填数字。")
            return

        sb = E.simulate_debt_payoff(debts, "snowball", extra_monthly=extra)
        av = E.simulate_debt_payoff(debts, "avalanche", extra_monthly=extra)

        # 失控优先（任一策略命中说明有债盖不住利息）
        unpayable = sb if sb.get("unpayable") else (av if av.get("unpayable") else None)
        if unpayable:
            self.lbl_snow_summary.config(text="⚠ 有债务失控", foreground=W.COLOR_DEFICIT)
            self.snow_tree.clear()
            self._set_note(self.txt_snow, unpayable["unpayable_reason"])
            return

        diff = sb["total_interest"] - av["total_interest"]
        self.lbl_snow_summary.config(
            text=(f"雪崩法：{av['total_months']} 个月还清，总利息 {av['total_interest']:,.0f} 元\n"
                  f"雪球法：{sb['total_months']} 个月还清，总利息 {sb['total_interest']:,.0f} 元\n"
                  f"→ 雪崩法比雪球法省 {diff:,.0f} 元"),
            foreground=W.COLOR_SURPLUS if diff >= 0 else W.COLOR_ACCENT)

        chosen = av if self.var_snow_strategy.get() == "avalanche" else sb
        self.snow_tree.clear()
        for i, item in enumerate(chosen["payoff_order"], 1):
            self.snow_tree.add_row([str(i), item["name"], f"第 {item['payoff_month']} 月"])
        self._set_note(self.txt_snow, chosen["note"])

    # ============================================================
    # ⑤ 以贷养贷螺旋
    # ============================================================
    def _build_spiral(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text="⑤ 以贷养贷螺旋")
        sf = W.ScrollableFrame(tab); sf.pack(fill="both", expand=True)
        c = sf.inner

        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="以贷养贷会滚成什么样", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Label(form,
                  text="借新还旧、只还最低、还不起了再借——这是债务失控的标准路径。"
                       "利息按复利指数增长，缺口滚进本金再生利息。看它多久翻倍。",
                  style="Sub.TLabel", wraplength=560, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(form, text="初始债务（元）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_sp_init = tk.StringVar(value="10000")
        ttk.Entry(form, textvariable=self.var_sp_init, width=14).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="年化（%）：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_sp_rate = tk.StringVar(value="24")
        ttk.Entry(form, textvariable=self.var_sp_rate, width=14).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="演示几个月：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_sp_months = tk.IntVar(value=24)
        ttk.Spinbox(form, from_=1, to=240, textvariable=self.var_sp_months, width=8).grid(
            row=4, column=1, sticky="w")
        ttk.Label(form, text="每月实际还款（元，0=完全不还）：").grid(row=5, column=0, sticky="w", pady=3)
        self.var_sp_pay = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.var_sp_pay, width=14).grid(row=5, column=1, sticky="w")
        ttk.Button(form, text="演示螺旋", command=self.on_spiral_compute).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(12, 2))

        res = W.CardFrame(c, padding=10)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        res.columnconfigure(0, weight=1)
        self.lbl_sp_head = ttk.Label(res, text="—", font=W.FONT_BIG, foreground=W.COLOR_DEFICIT)
        self.lbl_sp_head.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.sp_tree = W.ResultTreeview(
            res,
            columns=[("month", "月份", "center"), ("balance", "月末余额(元)", "e"),
                     ("interest", "当月新增利息(元)", "e")],
            col_widths={"month": 90, "balance": 160, "interest": 160}, height=10)
        self.sp_tree.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.txt_sp = self._make_note(res, height=7, grid=dict(row=2, column=0, sticky="ew"))
        ttk.Button(res, text="生成「问 AI」的提示词", style="AskAI.TButton",
                   command=self._open_spiral_prompt).grid(row=3, column=0, sticky="w", pady=(8, 0))

    def on_spiral_compute(self):
        try:
            init = float(self.var_sp_init.get())
            rate = float(self.var_sp_rate.get()) / 100
            months = int(self.var_sp_months.get())
            pay = float(self.var_sp_pay.get())
        except ValueError:
            self._set_note(self.txt_sp, "请输入有效的数字。")
            return
        r = E.simulate_loan_spiral(init, rate, months, pay)
        if "error" in r:
            self.lbl_sp_head.config(text="—", foreground=W.COLOR_DEFICIT)
            self.sp_tree.clear()
            self._set_note(self.txt_sp, r["error"])
            return
        growing = pay < r["breakeven_monthly"]
        if r["doubled"]:
            self.lbl_sp_head.config(
                text=f"{months} 个月后涨到 {r['final_balance']:,.0f} 元"
                     f"（仅 {r['doubling_month']} 个月就翻倍）",
                foreground=W.COLOR_DEFICIT)
        else:
            self.lbl_sp_head.config(
                text=f"{months} 个月后余额 {r['final_balance']:,.0f} 元",
                foreground=W.COLOR_DEFICIT if growing else W.COLOR_SURPLUS)
        self.sp_tree.clear()
        for s in r["monthly_snapshots"]:
            self.sp_tree.add_row(
                [f"第 {s['month']} 月", f"{s['balance']:,.0f}", f"{s['interest_accrued']:,.0f}"])
        self._set_note(self.txt_sp, r["note"])

    # ============================================================
    # 各 tab 的「生成问 AI 提示词」弹窗（复用通用弹窗，数据无效时弹窗内友好提示）
    # ============================================================
    def _collect_debts_desc(self):
        lines = []
        for i, row in enumerate(self._debt_rows):
            bal_s = row["balance"].get().strip()
            if not bal_s:
                continue
            name = row["name"].get().strip() or f"债{i+1}"
            lines.append(f"  - {name}：余额 {float(bal_s):,.0f} 元，"
                         f"年化 {float(row['rate'].get()):.1f}%，"
                         f"每月最低还 {float(row['min'].get()):,.0f} 元")
        if not lines:
            raise ValueError("没有有效的债务")
        return "\n".join(lines)

    def _open_apr_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI 的提示词（借贷真实年化）",
            build_fn=lambda city: E.build_loan_apr_prompt(
                float(self.var_principal.get()), float(self.var_monthly.get()),
                int(self.var_periods.get())))

    def _open_compare_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI 的提示词（还款方式对比）",
            build_fn=lambda city: E.build_compare_methods_prompt(
                float(self.var_cmp_p.get()), float(self.var_cmp_apr.get()),
                int(self.var_cmp_n.get())))

    def _open_affordable_prompt(self):
        inc_s = self.var_aff_income.get().strip()
        income = float(inc_s) if inc_s else None
        W.open_prompt_dialog(
            self, "问 AI 的提示词（可承受负债）",
            build_fn=lambda city: E.build_affordable_debt_prompt(
                float(self.var_aff_surplus.get()), float(self.var_aff_apr.get()),
                int(self.var_aff_n.get()), income))

    def _open_snowball_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI 的提示词（多笔债怎么还）",
            build_fn=lambda city: E.build_debt_payoff_prompt(
                self._collect_debts_desc(), float(self.var_snow_extra.get())))

    def _open_spiral_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI 的提示词（以贷养贷螺旋）",
            build_fn=lambda city: E.build_spiral_prompt(
                float(self.var_sp_init.get()), float(self.var_sp_rate.get()),
                int(self.var_sp_months.get()), float(self.var_sp_pay.get())))

    # ============================================================
    # ⑥ 债务健康仪表盘
    # ============================================================
    def _build_health(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text="⑥ 债务健康")
        sf = W.ScrollableFrame(tab); sf.pack(fill="both", expand=True)
        c = sf.inner

        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="债务健康仪表盘", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(form, text="总负债（元）：").grid(row=1, column=0, sticky="w", pady=3)
        self.var_health_debt = tk.StringVar(value="100000")
        ttk.Entry(form, textvariable=self.var_health_debt, width=14).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="月收入（元）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_health_income = tk.StringVar(value="8000")
        ttk.Entry(form, textvariable=self.var_health_income, width=14).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="每月能还（元）：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_health_pay = tk.StringVar(value="3000")
        ttk.Entry(form, textvariable=self.var_health_pay, width=14).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="平均年化（%）：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_health_apr = tk.StringVar(value="18")
        ttk.Entry(form, textvariable=self.var_health_apr, width=8).grid(row=4, column=1, sticky="w")
        ttk.Button(form, text="▶ 评估债务健康",
                   command=self.on_health_compute).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(8, 2))

        res = W.CardFrame(c, padding=8)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        self.lbl_health_level = ttk.Label(res, text="—", font=W.FONT_BIG,
                                          foreground=W.COLOR_ACCENT)
        self.lbl_health_level.pack(anchor="w", pady=(0, 4))
        ttk.Label(res, text="明细与建议", style="Header.TLabel").pack(anchor="w")
        self.txt_health = W.readonly_note(res, height=10, bg="#f0f7f0")
        ttk.Button(res, text="生成「问 AI」的提示词（给摆脱债务的建议）",
                   style="AskAI.TButton",
                   command=self._open_health_prompt).pack(anchor="w", pady=(8, 0))

    def on_health_compute(self):
        try:
            debt = float(self.var_health_debt.get() or 0)
            income = float(self.var_health_income.get() or 0)
            pay = float(self.var_health_pay.get() or 0)
            apr = float(self.var_health_apr.get()) / 100
        except ValueError:
            self._set_note(self.txt_health, "请输入有效的数字。")
            return
        r = E.assess_debt_health(debt, income, pay, apr)
        if "error" in r:
            self.lbl_health_level.config(text=r["error"], foreground=W.COLOR_DEFICIT)
            self._set_note(self.txt_health, "")
            return
        color = {"surplus": W.COLOR_SURPLUS, "accent": "#e67e22",
                 "deficit": W.COLOR_DEFICIT}.get(r["color"], W.COLOR_ACCENT)
        self.lbl_health_level.config(text=r["level"], foreground=color)
        self._set_note(self.txt_health, r["note"])

    def _open_health_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI（债务健康）",
            build_fn=lambda c: E.build_debt_health_prompt(
                float(self.var_health_debt.get() or 0), float(self.var_health_income.get() or 0),
                float(self.var_health_pay.get() or 0), float(self.var_health_apr.get()) / 100),
            intro="把这段复制给 AI，它会评估你的债务健康、给摆脱债务的步骤。")

    # ============================================================
    # 本地持久化：5 个 tab 的输入（含多笔债清单）
    # ============================================================
    def collect_state(self):
        """收集 5 个 tab 的全部输入为可序列化 dict。"""
        return {
            "version": 1,
            "apr": {
                "principal": self.var_principal.get(),
                "monthly": self.var_monthly.get(),
                "periods": self.var_periods.get(),
            },
            "compare": {
                "p": self.var_cmp_p.get(),
                "apr": self.var_cmp_apr.get(),
                "n": self.var_cmp_n.get(),
            },
            "affordable": {
                "surplus": self.var_aff_surplus.get(),
                "apr": self.var_aff_apr.get(),
                "n": self.var_aff_n.get(),
                "income": self.var_aff_income.get(),
            },
            "snowball": {
                "strategy": self.var_snow_strategy.get(),
                "extra": self.var_snow_extra.get(),
                "rows": [
                    {"name": r["name"].get(), "balance": r["balance"].get(),
                     "rate": r["rate"].get(), "min": r["min"].get()}
                    for r in self._debt_rows
                ],
            },
            "spiral": {
                "init": self.var_sp_init.get(),
                "rate": self.var_sp_rate.get(),
                "months": self.var_sp_months.get(),
                "pay": self.var_sp_pay.get(),
            },
        }

    def apply_state(self, st):
        """从 dict 恢复 5 个 tab 输入。结构异常则忽略，保持默认。"""
        try:
            a = st["apr"]
            self.var_principal.set(str(a["principal"]))
            self.var_monthly.set(str(a["monthly"]))
            self.var_periods.set(int(a["periods"]))

            c = st["compare"]
            self.var_cmp_p.set(str(c["p"]))
            self.var_cmp_apr.set(str(c["apr"]))
            self.var_cmp_n.set(int(c["n"]))

            f = st["affordable"]
            self.var_aff_surplus.set(str(f["surplus"]))
            self.var_aff_apr.set(str(f["apr"]))
            self.var_aff_n.set(int(f["n"]))
            self.var_aff_income.set(str(f["income"]))

            sn = st["snowball"]
            rows = sn["rows"]
            if rows:
                # 用保存的行重建（覆盖构造时的 2 笔默认样例）
                self._debt_rows = [
                    {k: tk.StringVar(value=str(r.get(k, "")))
                     for k in ("name", "balance", "rate", "min")}
                    for r in rows
                ]
                self._rebuild_debt_rows()
            self.var_snow_strategy.set(str(sn["strategy"]))
            self.var_snow_extra.set(str(sn["extra"]))

            sp = st["spiral"]
            self.var_sp_init.set(str(sp["init"]))
            self.var_sp_rate.set(str(sp["rate"]))
            self.var_sp_months.set(int(sp["months"]))
            self.var_sp_pay.set(str(sp["pay"]))
        except (KeyError, ValueError, TypeError):
            pass   # 状态损坏则保持默认，不崩

    def _state_path(self):
        return os.path.join(P.app_data_dir(), "debt_state.json")

    def save_state(self):
        """把 5 tab 输入存到 data/debt_state.json。失败静默。"""
        try:
            with open(self._state_path(), "w", encoding="utf-8") as f:
                json.dump(self.collect_state(), f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def load_state(self):
        """从 data/debt_state.json 恢复输入。文件缺失/损坏则不动。"""
        path = self._state_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.apply_state(json.load(f))
        except (OSError, ValueError):
            pass
