# -*- coding: utf-8 -*-
"""
page_compare.py —— 城市加减法（对比计算器）

核心问题："换个城市生活会更轻松吗？"
允许用户选择当前城市和目标城市，并排对比生活质量指标。
"""

import tkinter as tk
from tkinter import ttk

import cost_data as D
import calc_engine as E
import gui_widgets as W


class ComparePage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._profile_city = ""  # 从档案同步的城市名，用于提示词
        self._scroll = W.ScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True)
        self._content = self._scroll.inner
        self._build_form()
        self._build_result()

    def apply_profile(self, prof):
        """从档案同步：本人工资→方案A工资、城市→方案A城市，及生活方式。方案B（目标城市）保留用户选择。"""
        # 先存储城市信息，供「问 AI」提示词使用
        self._profile_city = prof.get("city", "")
        wage = prof.get("wage", "")
        if wage == "":
            wage = str(D.TYPICAL_WAGE.get(prof.get("tier", "一线"), 8000))
        self.var_wage.set(wage)
        if prof.get("tier"):
            self.var_tier_a.set(prof["tier"])
        for pk, vk in (("housing", "var_housing"), ("food", "var_food"),
                       ("insurance", "var_ins")):
            if prof.get(pk):
                getattr(self, vk).set(prof[pk])
        self.var_car.set(bool(prof.get("has_car", False)))

    def _build_form(self):
        form = W.CardFrame(self._content, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        # 标题
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

        ttk.Label(form, text="社保：").grid(row=3, column=2, sticky="w", pady=3, padx=(80, 0))
        self.var_ins = tk.StringVar(value="在职（单位缴）")
        ttk.Combobox(form, textvariable=self.var_ins, width=14,
                     values=["在职（单位缴）", "灵活就业（全自缴）", "不缴社保"],
                     state="readonly").grid(row=3, column=3, sticky="w", padx=4)

        ttk.Button(form, text="▶  开始对比",
                   command=self.on_compare).grid(row=4, column=0, columnspan=4,
                                                 sticky="ew", pady=(8, 4))

    def _build_result(self):
        res = W.CardFrame(self._content, padding=8)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        res.columnconfigure(0, weight=1)

        # 对比结果表格
        self._compare_frame = ttk.Frame(res)
        self._compare_frame.grid(row=0, column=0, sticky="ew", pady=4)

        # 分项明细对比
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

        # 结论解读
        ttk.Label(res, text="结论", style="Header.TLabel").grid(
            row=3, column=0, sticky="w", pady=(8, 2))
        self.txt_conclusion = tk.Text(res, height=5, wrap="word", relief="flat",
                                      font=(W.FONT_FAMILY, 11), bg="#f0f7f0",
                                      padx=8, pady=6)
        self.txt_conclusion.grid(row=4, column=0, sticky="ew", pady=2)
        self.txt_conclusion.config(state="disabled")
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

        # 调用对比函数
        result = E.compare_cities(wage, tier_a, tier_b,
                                  insurance_mode=ins,
                                  housing=housing, food_level=food,
                                  has_car=has_car)
        self._last_compare = result   # 供综合报告读取

        cur = result["current"]
        tgt = result["target"]

        # 构建对比表格
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

        # 分项明细
        self.table.clear()
        # 方案A明细
        for cr in cur["cost_rows"]:
            # 找到B中对应项
            b_amt = next((x["amount"] for x in tgt["cost_rows"] if x["item"] == cr["item"]), 0)
            diff = b_amt - cr["amount"]
            sign = "+" if diff > 0 else ""
            diff_str = f"{sign}{diff:,}" if diff != 0 else "—"
            self.table.add_row(
                [cr["item"], f"{cr['amount']:,}",
                 diff_str, f"{b_amt:,}"])

        # 结论
        est = result["estimated_wage"]
        text = result["comparison_text"]
        text += f"\n（预设目标城市工资：按比例估算约 {est:,} 元/月）"
        self._set_text(text)

    def _set_text(self, text):
        self.txt_conclusion.config(state="normal")
        self.txt_conclusion.delete("1.0", "end")
        self.txt_conclusion.insert("1.0", text)
        self.txt_conclusion.config(state="disabled")

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
