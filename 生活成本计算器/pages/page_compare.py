# -*- coding: utf-8 -*-
"""
page_compare.py —— 城市与住房（Notebook 四标签：对比/决策）

① 城市对比 —— 换个城市生活会轻松吗（原「城市加减法」）
② 买 vs 租 —— 买房还是租房，N 年总成本对比
③ 公积金额度 —— 按余额/缴存估可贷额 + 月供
④ 利率压力测试 —— 利率涨 1% 月供多多少

⚠️ 房价波动剧烈，结果均为粗算估算，重要决策请用各页「问 AI」结合最新行情。
"""
import tkinter as tk
from tkinter import ttk

import cost_data as D
import calc_engine as E
import gui_widgets as W

_WARN = ("⚠️ 当前房价波动剧烈，以下为粗算估算（房价/租金涨幅是假设、未含税费维修空置），"
         "重要决策请用各页「问 AI」结合你关注的具体小区和最新行情再判断。")


class ComparePage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._profile_city = ""  # 从档案同步的城市名，用于提示词
        # 顶部红字警示（跨 tab 可见）
        warn = ttk.Frame(self, padding=(10, 8, 10, 0))
        warn.pack(fill="x")
        ttk.Label(warn, text=_WARN, foreground="#c0392b",
                  style="Sub.TLabel", wraplength=880, justify="left").pack(anchor="w")

        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self._build_compare()
        self._build_buy_rent()
        self._build_fund()
        self._build_rate_stress()
        self._nb.select(0)

    # ---------- 档案载入 ----------
    def apply_profile(self, prof):
        """从档案同步：工资/城市/生活方式到 tab1；城市等级同步到 tab②③。"""
        self._profile_city = prof.get("city", "")
        wage = prof.get("wage", "")
        if wage == "":
            wage = str(D.TYPICAL_WAGE.get(prof.get("tier", "一线"), 8000))
        if hasattr(self, "var_wage"):
            self.var_wage.set(wage)
        if prof.get("tier"):
            tier = prof["tier"]
            if hasattr(self, "var_tier_a"):
                self.var_tier_a.set(tier)
            if hasattr(self, "var_br_tier"):
                self.var_br_tier.set(tier)
            if hasattr(self, "var_fund_tier"):
                self.var_fund_tier.set(tier)
        for pk, vk in (("housing", "var_housing"), ("food", "var_food"),
                       ("insurance", "var_ins")):
            if prof.get(pk) and hasattr(self, vk):
                getattr(self, vk).set(prof[pk])
        if hasattr(self, "var_car"):
            self.var_car.set(bool(prof.get("has_car", False)))

    # ============================================================
    # ① 城市对比（原城市加减法，逻辑不变）
    # ============================================================
    def _build_compare(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text="① 城市对比")
        sf = W.ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        self._content = sf.inner
        self._build_form()
        self._build_result()

    def _build_form(self):
        form = W.CardFrame(self._content, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        ttk.Label(form, text="对比两个城市的生活成本",
                  style="Header.TLabel").grid(row=0, column=0, columnspan=4,
                                              sticky="w", pady=(0, 8))

        ttk.Label(form, text="你的月薪（税前）：").grid(
            row=1, column=0, sticky="w", pady=3)
        self.var_wage = tk.StringVar(value="8000")
        ttk.Entry(form, textvariable=self.var_wage, width=12).grid(
            row=1, column=1, sticky="w", padx=4)

        ttk.Label(form, text="住房方式：").grid(row=1, column=2, sticky="w", pady=3)
        self.var_housing = tk.StringVar(value="合租单间")
        ttk.Combobox(form, textvariable=self.var_housing, width=14,
                     values=["合租单间", "一居室整租", "已购房（还月供）", "与父母同住（免租）"],
                     state="readonly").grid(row=1, column=3, sticky="w", padx=4)

        ttk.Label(form, text="方案A（当前城市）：").grid(
            row=2, column=0, sticky="w", pady=6)
        self.var_tier_a = tk.StringVar(value="一线")
        ttk.Combobox(form, textvariable=self.var_tier_a, values=D.TIER_KEYS,
                     state="readonly", width=12).grid(row=2, column=1, sticky="w", padx=4)

        ttk.Label(form, text="方案B（目标城市）：").grid(
            row=2, column=2, sticky="w", pady=6)
        self.var_tier_b = tk.StringVar(value="新一线")
        ttk.Combobox(form, textvariable=self.var_tier_b, values=D.TIER_KEYS,
                     state="readonly", width=12).grid(row=2, column=3, sticky="w", padx=4)

        ttk.Label(form, text="饮食档次：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_food = tk.StringVar(value="普通")
        ttk.Combobox(form, textvariable=self.var_food, width=10,
                     values=["节俭", "普通", "宽裕"],
                     state="readonly").grid(row=3, column=1, sticky="w", padx=4)

        self.var_car = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="有车", variable=self.var_car).grid(
            row=3, column=2, sticky="w", pady=3)

        ttk.Label(form, text="社保：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_ins = tk.StringVar(value="在职（单位缴）")
        ttk.Combobox(form, textvariable=self.var_ins, width=14,
                     values=["在职（单位缴）", "灵活就业（全自缴）", "不缴社保"],
                     state="readonly").grid(row=4, column=1, sticky="w", padx=4)

        ttk.Button(form, text="▶  开始对比",
                   command=self.on_compare).grid(row=4, column=0, columnspan=4,
                                                 sticky="ew", pady=(8, 4))

    def _build_result(self):
        res = W.CardFrame(self._content, padding=8)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        res.columnconfigure(0, weight=1)

        self._compare_frame = ttk.Frame(res)
        self._compare_frame.grid(row=0, column=0, sticky="ew", pady=4)

        ttk.Label(res, text="分项对比明细", style="Header.TLabel").grid(
            row=1, column=0, sticky="w", pady=(8, 2))
        self.table = W.ResultTreeview(
            res,
            columns=[("item", "项目", "w"), ("a", "方案A", "e"),
                     ("diff", "变化", "e"), ("b", "方案B", "e")],
            col_widths={"item": 200, "a": 120, "diff": 100, "b": 120},
            height=10)
        self.table.grid(row=2, column=0, sticky="nsew", pady=4)
        res.rowconfigure(2, weight=1)

        ttk.Label(res, text="结论", style="Header.TLabel").grid(
            row=3, column=0, sticky="w", pady=(8, 2))
        self.txt_conclusion = W.readonly_note(
            res, height=5, grid=dict(row=4, column=0, sticky="ew", pady=2), bg="#f0f7f0")
        ttk.Button(res, text="生成「问 AI」的提示词（让 AI 帮你判断换城市值不值）",
                   style="AskAI.TButton",
                   command=self._open_compare_prompt).grid(
            row=5, column=0, sticky="ew", pady=(8, 2))

    def on_compare(self):
        try:
            wage = float(self.var_wage.get())
        except ValueError:
            self._set_text("⚠️ 请输入有效的月薪数字。")
            return

        tier_a = self.var_tier_a.get()
        tier_b = self.var_tier_b.get()
        if tier_a == tier_b:
            self._set_text("⚠️ 两个城市相同，没有对比意义。请选择不同的城市等级。")
            return

        housing = self.var_housing.get()
        food = self.var_food.get()
        has_car = self.var_car.get()
        ins = self.var_ins.get()

        result = E.compare_cities(wage, tier_a, tier_b,
                                  insurance_mode=ins,
                                  housing=housing, food_level=food,
                                  has_car=has_car)
        self._last_compare = result   # 供综合报告读取

        cur = result["current"]
        tgt = result["target"]

        for w in self._compare_frame.winfo_children():
            w.destroy()

        ct = W.ComparisonTable(self._compare_frame)
        ct.build(
            data=[
                ("到手月薪", cur["income_net"], tgt["income_net"],
                 tgt["income_net"] - cur["income_net"], ""),
                ("生存成本", cur["cost_total"], tgt["cost_total"],
                 tgt["cost_total"] - cur["cost_total"], ""),
                ("月结余", cur["surplus"], tgt["surplus"],
                 tgt["surplus"] - cur["surplus"], ""),
                ("结余率", cur["surplus_rate"], tgt["surplus_rate"],
                 tgt["surplus_rate"] - cur["surplus_rate"], "%"),
                ("社保月缴", cur["social_ins"], tgt["social_ins"],
                 tgt["social_ins"] - cur["social_ins"], ""),
                ("个税", cur["tax"], tgt["tax"],
                 tgt["tax"] - cur["tax"], ""),
                ("攒首付年限", cur["house_saving_years"], tgt["house_saving_years"],
                 None, "年"),
            ],
            left_label=tier_a,
            right_label=tier_b,
            diff_label="变化"
        )
        ct.pack(fill="x")

        self.table.clear()
        for cr in cur["cost_rows"]:
            b_amt = next((x["amount"] for x in tgt["cost_rows"] if x["item"] == cr["item"]), 0)
            diff = b_amt - cr["amount"]
            sign = "+" if diff > 0 else ""
            diff_str = f"{sign}{diff:,}" if diff != 0 else "—"
            self.table.add_row(
                [cr["item"], f"{cr['amount']:,}",
                 diff_str, f"{b_amt:,}"])

        est = result["estimated_wage"]
        text = result["comparison_text"]
        text += f"\n（预设目标城市工资：按比例估算约 {est:,} 元/月）"
        self._set_text(text)

    def _set_text(self, text):
        self._set_note(self.txt_conclusion, text)

    def _set_note(self, tw, text):
        tw.config(state="normal")
        tw.delete("1.0", "end")
        tw.insert("1.0", text)
        tw.config(state="disabled")

    def _open_compare_prompt(self):
        def build(city):
            return E.build_compare_prompt(
                self.var_tier_a.get(), self.var_tier_b.get(),
                float(self.var_wage.get()), city)
        W.open_prompt_dialog(
            self, "问 AI 的提示词（换城市值不值）", with_city=True,
            build_fn=build, initial_city=self._profile_city,
            city_label="你想去的目标城市（具体名称）：",
            intro="把下面这段复制到任意 AI。记得填你想去的【具体城市名】，AI 会对比两座城市"
                  "的真实情况，给你值不值的判断。")

    # ============================================================
    # ② 买 vs 租
    # ============================================================
    def _build_buy_rent(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text="② 买 vs 租")
        sf = W.ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        c = sf.inner

        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="买房还是租房？N 年总成本对比",
                  style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        ttk.Label(form, text="城市等级：").grid(row=1, column=0, sticky="w", pady=3)
        self.var_br_tier = tk.StringVar(value="三线")
        ttk.Combobox(form, textvariable=self.var_br_tier, values=D.TIER_KEYS,
                     state="readonly", width=10).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="对比年限（年）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_br_years = tk.IntVar(value=10)
        ttk.Spinbox(form, from_=1, to=30, textvariable=self.var_br_years,
                    width=8).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="面积（㎡）：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_br_area = tk.IntVar(value=90)
        ttk.Spinbox(form, from_=30, to=200, textvariable=self.var_br_area,
                    width=8).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="首付比例：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_br_down = tk.StringVar(value="30%")
        ttk.Combobox(form, textvariable=self.var_br_down,
                     values=["20%", "30%", "50%"], state="readonly",
                     width=8).grid(row=4, column=1, sticky="w")
        ttk.Button(form, text="▶ 开始对比",
                   command=self.on_buy_rent).grid(row=5, column=0, columnspan=2,
                                                  sticky="ew", pady=(8, 2))

        res = W.CardFrame(c, padding=8)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        ttk.Label(res, text="结果", style="Header.TLabel").pack(anchor="w", pady=(0, 4))
        self.txt_br = W.readonly_note(res, height=12, bg="#f0f7f0")
        ttk.Button(res, text="生成「问 AI」的提示词（结合最新房价/利率帮你判断）",
                   style="AskAI.TButton",
                   command=self._open_buy_rent_prompt).pack(anchor="w", pady=(8, 0))

    def on_buy_rent(self):
        try:
            tier = self.var_br_tier.get()
            years = int(self.var_br_years.get())
            area = int(self.var_br_area.get())
            down_ratio = float(self.var_br_down.get().rstrip("%")) / 100
        except (ValueError, tk.TclError):
            self._set_note(self.txt_br, "请输入有效的数字。")
            return
        r = E.compare_buy_rent(tier, years=years, house_area=area, down_ratio=down_ratio)
        self._set_note(self.txt_br, r["note"])

    def _open_buy_rent_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI（买房还是租房）", with_city=True,
            build_fn=lambda city: E.build_buy_rent_prompt(
                self.var_br_tier.get(), int(self.var_br_years.get()), city),
            initial_city=self._profile_city,
            intro="把这段复制给 AI，填你关注的具体城市，它会结合最新房价/租金/利率帮你算买还是租。")

    # ============================================================
    # ③ 公积金额度
    # ============================================================
    def _build_fund(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text="③ 公积金额度")
        sf = W.ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        c = sf.inner

        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="我能贷多少公积金？",
                  style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        ttk.Label(form, text="城市等级：").grid(row=1, column=0, sticky="w", pady=3)
        self.var_fund_tier = tk.StringVar(value="三线")
        ttk.Combobox(form, textvariable=self.var_fund_tier, values=D.TIER_KEYS,
                     state="readonly", width=10).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="公积金余额（元）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_fund_balance = tk.StringVar(value="50000")
        ttk.Entry(form, textvariable=self.var_fund_balance, width=12).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="月缴存（元，可选）：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_fund_contrib = tk.StringVar(value="")
        ttk.Entry(form, textvariable=self.var_fund_contrib, width=12).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="贷款年限：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_fund_years = tk.IntVar(value=30)
        ttk.Spinbox(form, from_=5, to=30, textvariable=self.var_fund_years,
                    width=8).grid(row=4, column=1, sticky="w")
        ttk.Button(form, text="▶ 算一算",
                   command=self.on_fund).grid(row=5, column=0, columnspan=2,
                                              sticky="ew", pady=(8, 2))

        res = W.CardFrame(c, padding=8)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        ttk.Label(res, text="结果", style="Header.TLabel").pack(anchor="w", pady=(0, 4))
        self.txt_fund = W.readonly_note(res, height=10, bg="#f0f7f0")
        ttk.Button(res, text="生成「问 AI」的提示词（查当地最新公积金政策）",
                   style="AskAI.TButton",
                   command=self._open_fund_prompt).pack(anchor="w", pady=(8, 0))

    def on_fund(self):
        try:
            tier = self.var_fund_tier.get()
            balance = float(self.var_fund_balance.get() or 0)
            contrib_s = self.var_fund_contrib.get().strip()
            contrib = float(contrib_s) if contrib_s else 0
            years = int(self.var_fund_years.get())
        except (ValueError, tk.TclError):
            self._set_note(self.txt_fund, "请输入有效的数字。")
            return
        r = E.housing_fund_loan(tier, balance=balance, monthly_contribution=contrib, years=years)
        self._set_note(self.txt_fund, r["note"])

    def _open_fund_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI（公积金贷款）", with_city=True,
            build_fn=lambda city: E.build_fund_prompt(
                self.var_fund_tier.get(), float(self.var_fund_balance.get() or 0), city),
            initial_city=self._profile_city,
            intro="把这段复制给 AI，填你的城市，它会查当地最新公积金政策帮你算可贷额和月供。")

    # ============================================================
    # ④ 利率压力测试
    # ============================================================
    def _build_rate_stress(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text="④ 利率压力测试")
        sf = W.ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        c = sf.inner

        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="利率涨一点，月供多多少？",
                  style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        ttk.Label(form, text="贷款总额（元）：").grid(row=1, column=0, sticky="w", pady=3)
        self.var_rs_principal = tk.StringVar(value="1000000")
        ttk.Entry(form, textvariable=self.var_rs_principal, width=12).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="参考年利率（%）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_rs_rate = tk.StringVar(value="3.45")
        ttk.Entry(form, textvariable=self.var_rs_rate, width=12).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="贷款年限：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_rs_years = tk.IntVar(value=30)
        ttk.Spinbox(form, from_=5, to=30, textvariable=self.var_rs_years,
                    width=8).grid(row=3, column=1, sticky="w")
        ttk.Button(form, text="▶ 开始测试",
                   command=self.on_rate_stress).grid(row=4, column=0, columnspan=2,
                                                     sticky="ew", pady=(8, 2))

        res = W.CardFrame(c, padding=8)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        ttk.Label(res, text="结果", style="Header.TLabel").pack(anchor="w", pady=(0, 4))
        self.txt_rs = W.readonly_note(res, height=10, bg="#f0f7f0")
        ttk.Button(res, text="生成「问 AI」的提示词（结合当前 LPR 分析）",
                   style="AskAI.TButton",
                   command=self._open_rate_stress_prompt).pack(anchor="w", pady=(8, 0))

    def on_rate_stress(self):
        try:
            principal = float(self.var_rs_principal.get() or 0)
            base_rate = float(self.var_rs_rate.get()) / 100
            years = int(self.var_rs_years.get())
        except (ValueError, tk.TclError):
            self._set_note(self.txt_rs, "请输入有效的数字。")
            return
        r = E.rate_stress_test(principal, base_rate=base_rate, years=years)
        self._set_note(self.txt_rs, r["note"])

    def _open_rate_stress_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI（利率压力测试）",
            build_fn=lambda city: E.build_rate_stress_prompt(
                float(self.var_rs_principal.get() or 0), float(self.var_rs_rate.get()) / 100),
            intro="把这段复制给 AI，它会结合当前 LPR 走势帮你分析利率风险、选固定还是浮动。")
