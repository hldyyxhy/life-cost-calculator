# -*- coding: utf-8 -*-
"""
page_life_cost.py —— 计算器1：从生到死的一生成本（按钮选项式）

交互流程：
    选项区（城市/养育/生育/养老 4 组 Radiobutton）
    → 点击"开始计算"
    → 结果区：左侧分阶段比例图 + 右侧逐年明细表（可折叠）
"""

import tkinter as tk
from tkinter import ttk

import cost_data as D
import calc_engine as E
import gui_widgets as W


class LifeCostPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._scroll = W.ScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True)
        self._content = self._scroll.inner
        self._build_options()
        self._build_result_area()

    # ---------- 选项区 ----------
    def _build_options(self):
        opt = ttk.Frame(self._content, padding=(8, 8, 8, 4))
        opt.pack(fill="x")

        # 第①行：城市等级（带说明）
        tier_desc = {t: D.TIER_CITIES[t]["desc"][:18] for t in D.TIER_KEYS}
        f_tier, self.var_tier = W.make_radio_group(
            opt, "① 选择城市等级", D.TIER_KEYS, "三线",
            descriptions=tier_desc, columns=6)
        f_tier.pack(fill="x", pady=(0, 6))

        # 第②行：养育目标 + 养老方式
        row2 = ttk.Frame(opt)
        row2.pack(fill="x")
        level_desc = {lv: d["desc"] for lv, d in D.RAISE_LEVELS.items()}
        f_level, self.var_level = W.make_radio_group(
            row2, "② 养育目标", list(D.RAISE_LEVELS.keys()), "普惠",
            descriptions=level_desc, columns=3)
        f_level.pack(side="left", fill="x", expand=True, padx=(0, 6))
        care_opts = ["居家养老", "普惠养老机构", "中高端养老机构"]
        f_care, self.var_care = W.make_radio_group(
            row2, "③ 养老方式", care_opts, "居家养老", columns=1)
        f_care.pack(side="left", fill="x", expand=True)

        # 第③行：分娩 / 教育 / 退休 / 购房（下拉，节省空间）
        row3 = ttk.Frame(opt)
        row3.pack(fill="x", pady=(6, 0))

        def labeled_combobox(parent, title, var, values, width=14):
            f = ttk.LabelFrame(parent, text=title, padding=8)
            ttk.Combobox(f, textvariable=var, values=values, state="readonly",
                         width=width).pack(anchor="w")
            return f

        self.var_birth = tk.StringVar(value="公立·顺产")
        labeled_combobox(row3, "④ 分娩方式", self.var_birth,
                         list(D.DELIVERY_MODES.keys())).pack(side="left", padx=(0, 6), fill="x", expand=True)

        self.var_uni = tk.StringVar(value="公办")
        f_uni = ttk.LabelFrame(row3, text="⑤ 大学类型", padding=8)
        ttk.Combobox(f_uni, textvariable=self.var_uni, values=["公办", "民办"],
                     state="readonly", width=8).pack(anchor="w")
        self.var_grad = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_uni, text="读研（+2年）", variable=self.var_grad).pack(anchor="w")
        f_uni.pack(side="left", padx=(0, 6), fill="x", expand=True)

        self.var_retire = tk.IntVar(value=60)
        f_ret = ttk.LabelFrame(row3, text="⑥ 退休年龄", padding=8)
        ttk.Combobox(f_ret, textvariable=self.var_retire, values=[55, 60, 65],
                     state="readonly", width=8).pack(anchor="w")
        f_ret.pack(side="left", padx=(0, 6), fill="x", expand=True)

        self.var_purchase = tk.StringVar(value="贷款")
        labeled_combobox(row3, "⑦ 购房方式", self.var_purchase,
                         ["贷款", "全款"]).pack(side="left", fill="x", expand=True)

        # 计算按钮
        btn_frame = ttk.Frame(opt)
        btn_frame.pack(fill="x", pady=8)
        ttk.Button(btn_frame, text="▶  开始计算这一生成本",
                   command=self.on_compute).pack(side="left")
        ttk.Button(btn_frame, text="📊 对比两个场景",
                   command=self.open_compare).pack(side="right")
        ttk.Button(btn_frame, text="💾 导出结果",
                   command=self.export_result).pack(side="right", padx=(0, 6))
        # 折叠逐年明细开关
        self.var_collapse = tk.BooleanVar(value=True)  # 默认仅显示小计
        ttk.Checkbutton(btn_frame, text="展开逐年明细（取消则只看阶段汇总）",
                        variable=self.var_collapse,
                        command=self._refresh_table_only).pack(side="left", padx=20)

    # ---------- 结果区 ----------
    def _build_result_area(self):
        res = ttk.Frame(self._content, padding=(8, 0, 8, 8))
        res.pack(fill="both", expand=True)
        res.columnconfigure(0, weight=1)
        res.columnconfigure(1, weight=2)
        res.rowconfigure(1, weight=1)

        # 总计标题行
        self.lbl_total = ttk.Label(res, text="请点击上方「开始计算」",
                                   style="Result.TLabel", foreground=D_UNDEFINED)
        self.lbl_total.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        # 左：分阶段比例图
        left = W.CardFrame(res, "一生成本分阶段占比")
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self.bars = W.ProportionBars(left, height=240)
        self.bars.pack(fill="both", expand=True, padx=4, pady=4)
        # 假设说明
        self.lbl_assume = ttk.Label(left, text="", style="Sub.TLabel",
                                    justify="left", wraplength=300)
        self.lbl_assume.pack(fill="x", padx=4, pady=(4, 4))

        # 右：逐年明细表
        right = W.CardFrame(res, "逐年明细")
        right.grid(row=1, column=1, sticky="nsew")
        self.table = W.ResultTreeview(
            right,
            columns=[("stage", "阶段", "w"), ("item", "项目", "w"),
                     ("amount", "金额", "e"), ("note", "说明", "w")],
            col_widths={"stage": 120, "item": 200, "amount": 110, "note": 320},
            height=16)
        self.table.pack(fill="both", expand=True)

        self._result = None  # 缓存计算结果

    # ---------- 计算 ----------
    def on_compute(self):
        result = E.compute_life_cost(
            tier=self.var_tier.get(),
            level=self.var_level.get(),
            birth_mode=self.var_birth.get(),
            care_mode=self.var_care.get(),
            uni_type=self.var_uni.get(),
            graduate=self.var_grad.get(),
            retire_age=self.var_retire.get(),
            purchase_mode=self.var_purchase.get(),
        )
        self._result = result
        # 总计：总支出 − 养老金收入 = 净一生成本
        gc = result["gross_cost"]
        po = result["pension_offset"]
        nt = result["grand_total"]
        txt = (f"净一生成本：约 {nt/10000:.1f} 万元（{nt:,.0f} 元）"
               f"   ＝  总支出 {gc/10000:.1f}万  −  养老金收入 {po/10000:.1f}万")
        self.lbl_total.config(text=txt, style="Result.TLabel",
                              foreground=W.COLOR_ACCENT)
        # 比例图
        self.bars.set_data([(s["stage"], s["amount"]) for s in result["stage_subtotals"]])
        # 假设
        self.lbl_assume.config(text="\n".join("· " + a for a in result["assumptions"][:5]))
        # 明细表
        self._render_table()

    def export_result(self):
        """把当前一生成本结果导出为 txt"""
        if not self._result:
            from tkinter import messagebox
            messagebox.showinfo("提示", "请先点击「开始计算」。")
            return
        r = self._result
        L = []
        L.append("＝ 生活成本计算器 · 一生成本明细 ＝")
        L.append(f"城市：{self.var_tier.get()}　养育目标：{self.var_level.get()}")
        L.append(f"分娩：{self.var_birth.get()}　养老：{self.var_care.get()}")
        L.append(f"大学：{self.var_uni.get()}{'(读研)' if self.var_grad.get() else ''}"
                 f"　退休：{self.var_retire.get()}岁　购房：{self.var_purchase.get()}")
        L.append("")
        L.append(f"【总支出】{r['gross_cost']:,.0f} 元（{r['gross_cost']/10000:.1f} 万）")
        L.append(f"【养老金抵减】{r['pension_offset']:,.0f} 元（{r['pension_offset']/10000:.1f} 万）")
        L.append(f"【净一生成本】{r['grand_total']:,.0f} 元（{r['grand_total']/10000:.1f} 万）")
        L.append("")
        L.append("—— 分阶段 ——")
        for s in r["stage_subtotals"]:
            L.append(f"{s['stage']}：{s['amount']:,.0f} 元（{s['pct']}%）")
        L.append("")
        L.append("—— 逐项明细 ——")
        for row in r["rows"]:
            amt = row["amount"]
            amt_txt = (f"+{abs(amt):,.0f}（收入）" if row.get("is_income")
                       else f"{amt:,.0f}")
            L.append(f"[{row['stage']}] {row['item']}：{amt_txt}　{row['note']}")
        L.append("")
        L.append("—— 估算假设 ——")
        for a in r["assumptions"]:
            L.append("· " + a)
        L.append("")
        L.append("（本结果为公开调研的估算中值，仅供了解量级，不作为理财依据。）")
        W.export_text(f"一生成本_{self.var_tier.get()}_{self.var_level.get()}.txt",
                      "\n".join(L))

    def open_compare(self):
        """弹出双场景对比窗口：对比两个(城市,养育档位)的一生成本"""
        win = tk.Toplevel(self)
        win.title("📊 两个场景对比")
        win.geometry("980x640")
        W.apply_style(win)

        top = ttk.Frame(win, padding=10)
        top.pack(fill="x")

        def scenario_frame(parent, title, d_tier, d_level):
            f = ttk.LabelFrame(parent, text=title, padding=8)
            vt = tk.StringVar(value=d_tier)
            vl = tk.StringVar(value=d_level)
            ttk.Label(f, text="城市等级").pack(anchor="w")
            ttk.Combobox(f, textvariable=vt, values=D.TIER_KEYS,
                         state="readonly").pack(anchor="w", fill="x")
            ttk.Label(f, text="养育目标", style="Sub.TLabel").pack(anchor="w", pady=(4, 0))
            ttk.Combobox(f, textvariable=vl, values=list(D.RAISE_LEVELS.keys()),
                         state="readonly").pack(anchor="w", fill="x")
            return f, vt, vl

        fa, va_t, va_l = scenario_frame(top, "场景 A", "三线", "普惠")
        fa.pack(side="left", fill="x", expand=True, padx=(0, 8))
        fb, vb_t, vb_l = scenario_frame(top, "场景 B", "一线", "高端")
        fb.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(top, text="▶\n开始对比", command=lambda: do_compare()).pack(
            side="left", fill="y", padx=4)

        res = ttk.Frame(win, padding=10)
        res.pack(fill="both", expand=True)
        lbl_summary = ttk.Label(res, text="选择两个场景后点击「开始对比」",
                                style="Result.TLabel")
        lbl_summary.pack(anchor="w", pady=(0, 4))
        table = W.ResultTreeview(
            res,
            columns=[("stage", "阶段", "w"), ("a", "场景A(元)", "e"),
                     ("b", "场景B(元)", "e"), ("diff", "差额B-A", "e"),
                     ("ratio", "B/A倍数", "c")],
            col_widths={"stage": 210, "a": 110, "b": 110, "diff": 110, "ratio": 90},
            height=11)
        table.pack(fill="both", expand=True, pady=4)
        interp = tk.Text(res, height=4, wrap="word", relief="flat",
                         font=(W.FONT_FAMILY, 11), bg="#f7f9fc", padx=8, pady=6)
        interp.pack(fill="x")

        def do_compare():
            ra = E.compute_life_cost(va_t.get(), va_l.get())
            rb = E.compute_life_cost(vb_t.get(), vb_l.get())
            table.clear()
            for sa, sb in zip(ra["stage_subtotals"], rb["stage_subtotals"]):
                diff = sb["amount"] - sa["amount"]
                ratio = (sb["amount"] / sa["amount"]) if sa["amount"] else 0
                table.add_row([sa["stage"], f"{sa['amount']:,}",
                               f"{sb['amount']:,}", f"{diff:+,}",
                               f"{ratio:.1f}倍"])
            ta, tb = ra["grand_total"], rb["grand_total"]
            table.add_total(["净一生成本", f"{ta:,}", f"{tb:,}",
                             f"{tb-ta:+,}",
                             f"{tb/ta:.1f}倍" if ta else "-"])
            lbl_summary.config(
                text=f"场景A {ta/10000:.1f}万   vs   场景B {tb/10000:.1f}万"
                     f"   差额 {(tb-ta)/10000:+.1f}万")
            interp.delete("1.0", "end")
            who = "多" if tb > ta else "少"
            interp.insert("1.0",
                f"场景B（{vb_t.get()}·{vb_l.get()}）一生总成本比场景A（{va_t.get()}·{va_l.get()}）"
                f"{who} {abs(tb-ta)/10000:.1f} 万元，约为其 {max(tb,ta)/min(tb,ta):.1f} 倍。"
                f"城市等级与养育选择，是决定一生支出量级的两个最大杠杆。")
        return win

    def _refresh_table_only(self):
        if self._result:
            self._render_table()

    def _render_table(self):
        self.table.clear()
        r = self._result
        collapse = self.var_collapse.get()  # True=只看汇总

        if collapse:
            # 仅显示阶段小计 + 养老金抵减 + 总计
            for s in r["stage_subtotals"]:
                self.table.add_row(
                    [s["stage"], "—", f"{s['amount']:,.0f}", f"占比 {s['pct']}%"])
            # 总支出小计
            self.table.add_subtotal(
                ["总支出", "（各项支出之和）", f"{r['gross_cost']:,.0f}",
                 f"{r['gross_cost']/10000:.1f} 万元"])
            # 养老金作为收入抵减
            if r["pension_offset"] > 0:
                self.table.add_row(
                    ["收入", "养老金收入（抵减）", f"−{r['pension_offset']:,.0f}",
                     "退休后收入，从总支出中扣除"])
            self.table.add_total(["净一生成本", "总支出 − 养老金",
                                  f"{r['grand_total']:,.0f}",
                                  f"{r['grand_total']/10000:.1f} 万元"])
        else:
            # 展开逐行
            current_stage = None
            for row in r["rows"]:
                st = row["stage"]
                if st != current_stage:
                    current_stage = st
                # 收入项（养老金）显示为 +金额（收入）
                if row.get("is_income"):
                    amt_txt = f"+{abs(row['amount']):,.0f}（收入）"
                else:
                    amt_txt = f"{row['amount']:,.0f}"
                self.table.add_row([st, row["item"], amt_txt, row["note"]])
            # 各阶段小计
            for s in r["stage_subtotals"]:
                self.table.add_subtotal(
                    ["小计", s["stage"], f"{s['amount']:,.0f}", f"{s['pct']}%"])
            self.table.add_subtotal(
                ["总支出", "（各项支出之和）", f"{r['gross_cost']:,.0f}",
                 f"{r['gross_cost']/10000:.1f} 万元"])
            if r["pension_offset"] > 0:
                self.table.add_row(
                    ["收入", "养老金收入（抵减）", f"−{r['pension_offset']:,.0f}", ""])
            self.table.add_total(["净一生成本", "总支出 − 养老金",
                                  f"{r['grand_total']:,.0f}",
                                  f"{r['grand_total']/10000:.1f} 万元"])


# 占位颜色（模块级，供初始 lbl_total）
D_UNDEFINED = "#888"
