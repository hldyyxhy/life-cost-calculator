# -*- coding: utf-8 -*-
"""
page_current.py —— 核心页面：我现在的处境（增强版）

交互流程：
    左侧输入表单 → 点击"算一算"
    → 结果：工资去向堆叠条 + 3大数字 + 生存底线 + 明细表 + 白话解读
"""

import tkinter as tk
from tkinter import ttk

import cost_data as D
import calc_engine as E
import gui_widgets as W


class CurrentSituationPage(ttk.Frame):
    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app   # 用于跨页读取档案
        self._profile_city = ""  # 从档案同步的城市名，用于提示词
        self._scroll = W.ScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True)
        self._content = self._scroll.inner
        self._build_form()
        self._build_result()

    # ---------- 档案载入 ----------
    def apply_profile(self, prof):
        """把档案 dict 映射填入本页表单（供档案页「确定」推送调用）。"""
        # 先存储城市信息，供「问 AI」提示词使用
        self._profile_city = prof.get("city", "")
        m = {
            "age": self.var_age, "tier": self.var_tier, "wage": self.var_wage,
            "insurance": self.var_ins, "housing": self.var_housing,
            "food": self.var_food, "has_car": self.var_car,
            "num_children": self.var_kids, "child_age_group": self.var_kid_age,
            "support_elderly": self.var_elderly, "support_family": self.var_family,
            "has_housing_deduction": self.var_house_dedu,
            "has_continuing_education": self.var_cont_edu,
            "savings": self.var_savings, "has_partner": self.var_has_partner,
            "partner_wage": self.var_partner_wage,
            "partner_insurance": self.var_partner_ins,
        }
        for k, var in m.items():
            if k not in prof:
                continue
            val = prof[k]
            # entry 类空串 → 用本城市典型工资兜底
            if k == "wage" and val == "":
                val = str(D.TYPICAL_WAGE.get(prof.get("tier", "二线"), 5000))
            if k == "partner_wage" and val == "" and prof.get("has_partner"):
                val = str(D.TYPICAL_WAGE.get(prof.get("tier", "二线"), 5000))
            if k in ("support_family", "savings", "partner_wage") and val == "":
                val = "0"
            try:
                var.set(val)
            except tk.TclError:
                pass

    # ---------- 输入表单 ----------
    def _build_form(self):
        form = W.CardFrame(self._content, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)

        # —— 个人信息 ——
        ttk.Label(form, text="个人信息", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        ttk.Label(form, text="年龄：").grid(row=1, column=0, sticky="w", pady=3)
        self.var_age = tk.IntVar(value=30)
        ttk.Spinbox(form, from_=16, to=80, textvariable=self.var_age,
                    width=8).grid(row=1, column=1, sticky="w")

        ttk.Label(form, text="城市等级：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_tier = tk.StringVar(value="二线")
        ttk.Combobox(form, textvariable=self.var_tier, values=D.TIER_KEYS,
                     state="readonly", width=12).grid(row=2, column=1, sticky="w")
        self.var_tier.trace_add("write", lambda *_: self._sync_wage_default())

        # —— 收入 ——
        ttk.Label(form, text="收入", style="Header.TLabel").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(10, 4))

        ttk.Label(form, text="税前月薪（元）：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_wage = tk.StringVar(value=str(D.TYPICAL_WAGE["二线"]))
        self._wage_entry = ttk.Entry(form, textvariable=self.var_wage, width=12)
        self._wage_entry.grid(row=4, column=1, sticky="w")
        self._wage_hint = ttk.Label(form, style="Sub.TLabel")
        self._wage_hint.grid(row=5, column=1, sticky="w")
        self._sync_wage_default()

        ttk.Label(form, text="社保：").grid(row=6, column=0, sticky="w", pady=3)
        self.var_ins = tk.StringVar(value="在职（单位缴）")
        ttk.Combobox(form, textvariable=self.var_ins, width=14,
                     values=["在职（单位缴）", "灵活就业（全自缴）", "不缴社保"],
                     state="readonly").grid(row=6, column=1, sticky="w")

        # —— 居住与生活方式 ——
        ttk.Label(form, text="居住与生活方式", style="Header.TLabel").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(10, 4))

        ttk.Label(form, text="住房方式：").grid(row=8, column=0, sticky="w", pady=3)
        self.var_housing = tk.StringVar(value="合租单间")
        ttk.Combobox(form, textvariable=self.var_housing, width=16,
                     values=["合租单间", "一居室整租", "已购房（还月供）", "与父母同住（免租）"],
                     state="readonly").grid(row=8, column=1, sticky="w")

        ttk.Label(form, text="饮食档次：").grid(row=9, column=0, sticky="w", pady=3)
        self.var_food = tk.StringVar(value="普通")
        ttk.Combobox(form, textvariable=self.var_food, width=14,
                     values=["节俭", "普通", "宽裕"], state="readonly").grid(
            row=9, column=1, sticky="w")

        self.var_car = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="我有车（按养车成本计）",
                        variable=self.var_car).grid(row=10, column=0, columnspan=2,
                                                    sticky="w", pady=3)

        # —— 家庭负担 ——
        ttk.Label(form, text="家庭负担", style="Header.TLabel").grid(
            row=11, column=0, columnspan=2, sticky="w", pady=(10, 4))

        ttk.Label(form, text="子女数量：").grid(row=12, column=0, sticky="w", pady=3)
        self.var_kids = tk.IntVar(value=0)
        ttk.Spinbox(form, from_=0, to=6, textvariable=self.var_kids,
                    width=8).grid(row=12, column=1, sticky="w")

        ttk.Label(form, text="子女年龄段：").grid(row=13, column=0, sticky="w", pady=3)
        self.var_kid_age = tk.StringVar(value="中小学（6-18岁）")
        ttk.Combobox(form, textvariable=self.var_kid_age, width=16,
                     values=list(D.CHILD_CARE_MONTHLY_BASE.keys()),
                     state="readonly").grid(row=13, column=1, sticky="w")

        self.var_elderly = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="赡养老人（+3000元/月扣除）",
                        variable=self.var_elderly).grid(
            row=14, column=0, columnspan=2, sticky="w", pady=3)

        # 给老家生活费（新增：外出务工者关键支出）
        ttk.Label(form, text="给老家生活费（元/月）：").grid(row=15, column=0, sticky="w", pady=3)
        self.var_family = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.var_family, width=10).grid(
            row=15, column=1, sticky="w")
        ttk.Label(form, text="在外务工给父母的生活费（0 = 不填）",
                  style="Sub.TLabel").grid(row=16, column=1, sticky="w")

        self.var_house_dedu = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="有住房租金/房贷利息扣除",
                        variable=self.var_house_dedu).grid(
            row=17, column=0, columnspan=2, sticky="w", pady=3)

        self.var_cont_edu = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="本人继续教育（+400元/月扣除）",
                        variable=self.var_cont_edu).grid(
            row=18, column=0, columnspan=2, sticky="w", pady=3)

        # —— 伴侣（双收入） ——
        ttk.Label(form, text="伴侣（双收入家庭）", style="Header.TLabel").grid(
            row=19, column=0, columnspan=2, sticky="w", pady=(10, 4))

        self.var_has_partner = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="有伴侣/配偶（按家庭算结余）",
                        variable=self.var_has_partner).grid(
            row=20, column=0, columnspan=2, sticky="w", pady=3)

        ttk.Label(form, text="伴侣税前月薪（元）：").grid(row=21, column=0, sticky="w", pady=3)
        self.var_partner_wage = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.var_partner_wage, width=12).grid(
            row=21, column=1, sticky="w")

        ttk.Label(form, text="伴侣社保：").grid(row=22, column=0, sticky="w", pady=3)
        self.var_partner_ins = tk.StringVar(value="在职（单位缴）")
        ttk.Combobox(form, textvariable=self.var_partner_ins, width=14,
                     values=["在职（单位缴）", "灵活就业（全自缴）", "不缴社保"],
                     state="readonly").grid(row=22, column=1, sticky="w")

        # —— 抗风险 ——
        ttk.Label(form, text="抗风险", style="Header.TLabel").grid(
            row=23, column=0, columnspan=2, sticky="w", pady=(10, 4))

        ttk.Label(form, text="现有存款/应急金（元）：").grid(row=24, column=0, sticky="w", pady=3)
        self.var_savings = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.var_savings, width=12).grid(
            row=24, column=1, sticky="w")

        # 计算按钮
        ttk.Button(form, text="▶  算一算我现在过得怎么样",
                   command=self.on_compute).grid(row=25, column=0, columnspan=2,
                                                 sticky="ew", pady=(12, 4))
        ttk.Button(form, text="💾 导出结果",
                   command=self.export_result).grid(row=26, column=0, columnspan=2,
                                                    sticky="ew", pady=(0, 4))

    def export_result(self):
        if not getattr(self, "_last_result", None):
            from tkinter import messagebox
            messagebox.showinfo("提示", "请先点击「算一算」。")
            return
        r = self._last_result
        L = []
        L.append("＝ 生活成本计算器 · 我现在的境况 ＝")
        L.append("")
        L.append("—— 月度收支 ——")
        L.append(f"到手收入：{r['income_net']:,.0f} 元/月")
        L.append(f"生存成本：{r['cost_total']:,.0f} 元/月")
        L.append(f"月结余/缺口：{r['surplus']:+,.0f} 元/月"
                 f"（{'结余' if r['surplus']>=0 else '缺口'}）")
        L.append(f"结余率：{r['surplus_rate']:.0f}%")
        L.append(f"（五险一金 {r['social_ins']:,}、个税 {r['tax']:,}）")
        if r["house_saving_years"]:
            L.append(f"攒首付约需 {r['house_saving_years']:.0f} 年")
        L.append("")
        L.append("—— 月度生存成本明细 ——")
        for c in r["cost_rows"]:
            L.append(f"{c['item']}：{c['amount']:,} 元/月　{c['note']}")
        L.append("")
        L.append("—— 处境解读 ——")
        L.append(r["interpretation"])
        L.append("")
        L.append("—— 估算说明 ——")
        for a in r["assumptions"]:
            L.append("· " + a)
        L.append("")
        L.append("（本结果为公开调研的估算中值，仅供了解量级，不作为理财依据。）")
        W.export_text("我的境况.txt", "\n".join(L))

    def _sync_wage_default(self):
        tier = self.var_tier.get()
        tip = (f"当地典型月薪约 {D.TYPICAL_WAGE[tier]:,} 元，"
               f"最低工资 {D.MIN_WAGE[tier]:,} 元")
        self._wage_hint.config(text=tip)

    # ---------- 结果区 ----------
    def _build_result(self):
        res = W.CardFrame(self._content, padding=8)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        res.columnconfigure(0, weight=1)

        # 1. 工资去向堆叠条
        self.bar = W.SalaryBreakdownBar(res, title="你的工资去哪儿了")
        self.bar.grid(row=0, column=0, sticky="ew", pady=2)

        # 2. 三个大数字：到手 / 成本 / 结余
        ttk.Label(res, text="月度收支总览", style="Header.TLabel").grid(
            row=1, column=0, sticky="w", pady=(6, 2))
        overview = ttk.Frame(res)
        overview.grid(row=2, column=0, sticky="ew", pady=4)
        for i in range(3):
            overview.columnconfigure(i, weight=1)

        self.lbl_net_title = ttk.Label(overview, text="到手收入")
        self.lbl_net_title.grid(row=0, column=0)
        self.bignumber_net = W.BigNumberLabel(overview, kind="income")
        self.bignumber_net.grid(row=1, column=0, pady=4)
        self._lbl_net_sub = ttk.Label(overview, text="", style="Sub.TLabel")
        self._lbl_net_sub.grid(row=2, column=0)

        ttk.Label(overview, text="生存成本").grid(row=0, column=1)
        self.bignumber_cost = W.BigNumberLabel(overview, kind="neutral")
        self.bignumber_cost.grid(row=1, column=1, pady=4)
        self._lbl_cost_sub = ttk.Label(overview, text="", style="Sub.TLabel")
        self._lbl_cost_sub.grid(row=2, column=1)

        ttk.Label(overview, text="月结余 / 结余率").grid(row=0, column=2)
        self.bignumber_surplus = W.BigNumberLabel(overview, kind="neutral")
        self.bignumber_surplus.grid(row=1, column=2, pady=4)
        self._lbl_surplus_sub = ttk.Label(overview, text="", style="Sub.TLabel")
        self._lbl_surplus_sub.grid(row=2, column=2)

        # 3. 城市生存底线卡片
        self._survival_frame = ttk.Frame(res)
        self._survival_frame.grid(row=3, column=0, sticky="ew", pady=(6, 2))
        self._survival_label = ttk.Label(self._survival_frame, text="",
                                          font=W.FONT, foreground="#555")
        self._survival_label.pack(side="left")

        # 4. 抗风险卡片
        ttk.Label(res, text="█ 抗风险能力", style="Header.TLabel").grid(
            row=4, column=0, sticky="w", pady=(8, 2))
        self._risk_card = ttk.Frame(res)
        self._risk_card.grid(row=5, column=0, sticky="ew", pady=2)
        self._risk_labels = {}
        for i, key in enumerate(("unemp", "fund", "gap", "illness")):
            lbl = ttk.Label(self._risk_card, text="", font=W.FONT)
            lbl.grid(row=i, column=0, sticky="w", pady=2)
            self._risk_labels[key] = lbl

        ttk.Separator(res, orient="horizontal").grid(row=6, column=0, sticky="ew", pady=6)

        # 5. 月度成本明细表
        ttk.Label(res, text="月度生存成本明细", style="Header.TLabel").grid(
            row=7, column=0, sticky="w")
        self.table = W.ResultTreeview(
            res,
            columns=[("item", "项目", "w"), ("amount", "金额(元/月)", "e"),
                     ("note", "说明", "w")],
            col_widths={"item": 180, "amount": 120, "note": 360},
            height=8)
        self.table.grid(row=8, column=0, sticky="nsew", pady=4)
        res.rowconfigure(8, weight=1)

        # 6. 白话解读（带垂直滚动条）
        ttk.Label(res, text="处境解读", style="Header.TLabel").grid(
            row=9, column=0, sticky="w", pady=(8, 2))
        interp_frame = ttk.Frame(res)
        interp_frame.grid(row=10, column=0, sticky="ew", pady=2)
        interp_frame.columnconfigure(0, weight=1)
        self.txt_interp = tk.Text(interp_frame, height=9, wrap="word", relief="flat",
                                  font=(W.FONT_FAMILY, 11), bg="#f7f9fc",
                                  padx=8, pady=6)
        self.txt_interp.grid(row=0, column=0, sticky="ew")
        sb_interp = ttk.Scrollbar(interp_frame, orient="vertical",
                                  command=self.txt_interp.yview)
        self.txt_interp.configure(yscrollcommand=sb_interp.set)
        sb_interp.grid(row=0, column=1, sticky="ns")
        self.txt_interp.config(state="disabled")
        ttk.Button(res, text="生成「问 AI」的提示词（让 AI 详细解读你的处境）",
                   style="AskAI.TButton",
                   command=self._open_current_prompt).grid(
            row=11, column=0, sticky="ew", pady=(8, 2))

    def _open_current_prompt(self):
        def build(city):
            return E.build_current_situation_prompt(
                int(self.var_age.get()), self.var_tier.get(),
                float(self.var_wage.get()), self.var_ins.get(),
                self.var_housing.get(), self.var_food.get(),
                self.var_car.get(), int(self.var_kids.get()),
                self.var_elderly.get(),
                float(self.var_savings.get() or "0"), city)
        W.open_prompt_dialog(
            self, "问 AI 的提示词（我的处境解读）", with_city=True,
            build_fn=build, initial_city=self._profile_city,
            intro="工具算的是「死数」。把下面这段复制到任意 AI，它会详细解读你的处境、"
                  "给可执行的建议。")

    # ---------- 计算 ----------
    def on_compute(self):
        try:
            wage = float(self.var_wage.get())
        except ValueError:
            self._set_interp("⚠️ 请输入有效的月薪数字。")
            return

        try:
            family_support = int(self.var_family.get())
            if family_support < 0:
                family_support = 0
        except ValueError:
            family_support = 0

        result = E.compute_current_situation(
            age=self.var_age.get(),
            wage_pretax=wage,
            tier=self.var_tier.get(),
            housing=self.var_housing.get(),
            food_level=self.var_food.get(),
            has_car=self.var_car.get(),
            insurance_mode=self.var_ins.get(),
            num_children=self.var_kids.get(),
            child_age_group=self.var_kid_age.get(),
            support_elderly=self.var_elderly.get(),
            has_housing_deduction=self.var_house_dedu.get(),
            has_continuing_education=self.var_cont_edu.get(),
            support_family_monthly=family_support,
        )
        self._last_result = result

        # —— 双收入：有伴侣则按家庭结余 ——
        partner_wage = 0
        if self.var_has_partner.get():
            try:
                partner_wage = float(self.var_partner_wage.get())
            except ValueError:
                partner_wage = 0
        family = E.compute_family_situation(
            result, partner_wage, self.var_tier.get(),
            self.var_partner_ins.get())
        is_family = self.var_has_partner.get() and partner_wage > 0
        eff_surplus = family["family_surplus"] if is_family else result["surplus"]
        eff_rate = family["family_surplus_rate"] if is_family else result["surplus_rate"]

        # 大数字
        self.bignumber_net.set_value(result["income_net"], "income")
        self.bignumber_cost.set_value(result["cost_total"], "neutral")
        kind = "surplus" if eff_surplus >= 0 else "deficit"
        self.bignumber_surplus.set_value(eff_surplus, kind)

        # 小字（生存底线直接取自结果，避免重复计算）
        baseline = result["survival_baseline"]
        self._lbl_net_sub.config(text=f"税前 {wage:,.0f}")
        self._lbl_cost_sub.config(text=f"底线 {baseline:,.0f}")
        sr = eff_rate
        sr_text = f"{sr:.0f}%"
        if sr >= 20:
            sr_text += " ✅ 健康"
        elif sr >= 10:
            sr_text += " ⚠️ 偏低"
        else:
            sr_text += " 🔴 危险"
        if is_family:
            sr_text = "家庭结余率 " + sr_text
        self._lbl_surplus_sub.config(text=sr_text)

        # 生存底线
        self._survival_label.config(
            text=f"█ 在【{self.var_tier.get()}】维持基本生存的最低月成本：{baseline:,} 元"
                 + (f"  │  按当前结余可多活 {eff_surplus/baseline:.1f} 个月"
                    if eff_surplus > 0 and baseline > 0 else ""))

        # —— 抗风险区块 ——
        try:
            savings = float(self.var_savings.get())
        except ValueError:
            savings = 0
        risk = E.compute_risk_indicators(savings, baseline)
        self._risk_labels["unemp"].config(
            text=f"· 失业后靠存款可撑 {risk['unemployment_months']:.1f} 个月（底线 {baseline:,}/月）",
            foreground=W.COLOR_DEFICIT if risk["unemployment_months"] < 3 else "#333")
        self._risk_labels["fund"].config(
            text=f"· 建议应急金：{risk['emergency_fund_low']:,} ~ {risk['emergency_fund_high']:,} 元（3~6个月底线）")
        gap = risk["emergency_gap"]
        if gap > 0:
            self._risk_labels["gap"].config(
                text=f"· 应急金缺口 {gap:,} 元（距建议下限还差这么多）",
                foreground=W.COLOR_DEFICIT)
        else:
            self._risk_labels["gap"].config(
                text=f"· 应急金已达标 ✅（超下限 {-gap:,} 元）",
                foreground=W.COLOR_SURPLUS)
        sev = risk["severe_illness_risk"]
        if sev == "high":
            self._risk_labels["illness"].config(
                text="· ⚠️ 大病风险高：一次重病自付约 5~10 万，你的存款不足 5 万！",
                foreground=W.COLOR_DEFICIT)
        elif sev == "medium":
            self._risk_labels["illness"].config(
                text="· 大病风险中等：存款 5~10 万，勉强够一次重病自付",
                foreground="#e67e22")
        else:
            self._risk_labels["illness"].config(
                text="· 大病风险低：存款 >10 万，能扛住一次重病自付 ✅",
                foreground=W.COLOR_SURPLUS)

        # 工资去向堆叠条（直接读结构化 breakdown，不再串匹配）
        bar_data = []
        if result["social_ins"] > 0:
            bar_data.append(("社保公积金", result["social_ins"], "#e74c3c"))
        if result["tax"] > 0:
            bar_data.append(("个税", result["tax"], "#f39c12"))
        for name, color in (("住房", "#3498db"), ("饮食", "#2ecc71"),
                            ("交通", "#9b59b6"), ("通讯日用", "#95a5a6"),
                            ("给老家", "#e67e22")):
            if name in result["breakdown"]:
                bar_data.append((name, result["breakdown"][name], color))
        if result["surplus"] > 0:
            bar_data.append(("结余", result["surplus"], "#1a7d3a"))
        self.bar.set_data(bar_data)

        # 明细表
        self.table.clear()
        for r in result["cost_rows"]:
            self.table.add_row([r["item"], f"{r['amount']:,.0f}", r["note"]])
        self.table.add_total(["合计", f"{result['cost_total']:,.0f}", "月度基本生存成本"])

        # 解读
        full = result["interpretation"] + "\n\n—— 估算说明 ——\n" + \
               "\n".join("· " + a for a in result["assumptions"])
        self._set_interp(full)

    def _set_interp(self, text):
        self.txt_interp.config(state="normal")
        self.txt_interp.delete("1.0", "end")
        self.txt_interp.insert("1.0", text)
        self.txt_interp.config(state="disabled")
