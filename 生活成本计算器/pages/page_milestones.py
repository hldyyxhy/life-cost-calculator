# -*- coding: utf-8 -*-
"""
page_milestones.py —— 人生三座山

三个独立模块：结婚、养娃、养老。
每个模块独立计算，不需要一次性填完所有选项。
"""

import tkinter as tk
from tkinter import ttk

import cost_data as D
import calc_engine as E
import gui_widgets as W


class MilestonesPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._computed = {"marriage": False, "child": False, "retire": False}
        self._scroll = W.ScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True)
        self._content = self._scroll.inner
        self._build_all()

    def get_report_section(self):
        """返回三座山的报告文本 {marriage, child, retire}，未计算的为 None。"""
        out = {}
        if self._computed["marriage"]:
            out["marriage"] = (
                f"合计 {self._marriage_total.cget('text')}。"
                f"{self._marriage_years.cget('text')}")
        if self._computed["child"]:
            out["child"] = (
                f"0-22岁累计 {self._child_total.cget('text')}，"
                f"{self._child_monthly.cget('text')}。"
                f"{self._child_ratio.cget('text')}")
        if self._computed["retire"]:
            out["retire"] = (
                f"退休金 {self._retire_pension.cget('text')}，"
                f"支出 {self._retire_cost.cget('text')}，"
                f"{self._retire_gap.cget('text')}。"
                + (self._retire_tip.cget('text') or ""))
        return out

    def apply_profile(self, prof):
        """从档案同步：城市 + 月薪（三座山共享字段）。"""
        if prof.get("tier"):
            self.var_tier.set(prof["tier"])
        wage = prof.get("wage", "")
        if wage == "":
            wage = str(D.TYPICAL_WAGE.get(prof.get("tier", "三线"), 5000))
        self.var_wage.set(wage)

    def _build_all(self):
        # 公共输入：城市 + 月薪（供三座山共享）
        top = W.CardFrame(self._content, padding=10)
        top.pack(side="top", fill="x", padx=8, pady=(8, 4))
        for i in range(4):
            top.columnconfigure(i, weight=1 if i % 2 else 0)

        ttk.Label(top, text="你的基本信息", style="Header.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        ttk.Label(top, text="城市等级：").grid(row=1, column=0, sticky="w", pady=3)
        self.var_tier = tk.StringVar(value="三线")
        ttk.Combobox(top, textvariable=self.var_tier, values=D.TIER_KEYS,
                     state="readonly", width=10).grid(row=1, column=1, sticky="w", padx=4)

        ttk.Label(top, text="月薪（税前，元）：").grid(row=1, column=2, sticky="w", pady=3, padx=(20, 0))
        self.var_wage = tk.StringVar(value="5000")
        ttk.Entry(top, textvariable=self.var_wage, width=12).grid(row=1, column=3, sticky="w", padx=4)

        ttk.Label(top, text="下面三座山各自独立，互不影响。",
                  style="Sub.TLabel").grid(row=2, column=0, columnspan=4, sticky="w", pady=4)

        # ─── 第一座山：结婚 ───
        self._build_marriage()
        # ─── 第二座山：养娃 ───
        self._build_child()
        # ─── 第三座山：养老 ───
        self._build_retirement()

    # ============================================================
    # 第一座山：结婚
    # ============================================================
    def _build_marriage(self):
        box = W.CardFrame(self._content, title="第一座山：结婚要花多少钱", padding=10)
        box.pack(side="top", fill="x", padx=8, pady=4)
        box.columnconfigure(1, weight=1)

        # 自动读取当前城市的结婚数据
        self._marriage_labels = {}
        row = 0
        for key in ("彩礼", "婚礼婚宴", "婚房首付"):
            ttk.Label(box, text=f"· {key}：").grid(
                row=row, column=0, sticky="w", pady=2)
            lbl = ttk.Label(box, text="（选择城市后自动计算）", style="Sub.TLabel")
            lbl.grid(row=row, column=1, sticky="w")
            self._marriage_labels[key] = lbl
            row += 1

        ttk.Separator(box, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=6)
        row += 1

        ttk.Label(box, text="合计：", font=W.FONT_BOLD).grid(
            row=row, column=0, sticky="w", pady=2)
        self._marriage_total = ttk.Label(box, text="—", font=W.FONT_RESULT,
                                          foreground=W.COLOR_ACCENT)
        self._marriage_total.grid(row=row, column=1, sticky="w")
        row += 1

        self._marriage_years = ttk.Label(box, text="", style="Sub.TLabel")
        self._marriage_years.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
        row += 1

        # 购房方式选项
        self._marriage_purchase = tk.StringVar(value="贷款（首付）")
        ttk.Radiobutton(box, text="贷款（只算首付）",
                        variable=self._marriage_purchase,
                        value="贷款（首付）",
                        command=self._update_marriage).grid(row=row, column=0, sticky="w")
        ttk.Radiobutton(box, text="全款",
                        variable=self._marriage_purchase,
                        value="全款",
                        command=self._update_marriage).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Button(box, text="计算结婚成本",
                   command=self._update_marriage).grid(row=row, column=0, columnspan=2,
                                                       sticky="ew", pady=6)

    def _wage(self):
        """统一解析月薪，非法则回退 5000"""
        try:
            return float(self.var_wage.get())
        except ValueError:
            return 5000

    def _monthly_surplus(self):
        """按本页公共输入算月结余（轻量，不构建完整解读）"""
        return E.compute_surplus(self._wage(), self.var_tier.get())

    def _afford_years_label(self, total_cost):
        """按月结余算攒够某总额所需年数的提示文本"""
        ms = self._monthly_surplus()
        if ms <= 0:
            return "⚠️ 你目前入不敷出，暂时不具备这个经济条件。"
        yrs = total_cost / (ms * 12)
        if yrs >= 100:
            return "按当前结余，几乎不可能攒够。"
        return f"按你现在的月结余 {ms:,.0f} 元，需要攒约 {yrs:.0f} 年。"

    def _update_marriage(self):
        tier = self.var_tier.get()
        cf = D.city_factor(tier)

        # 计算各项
        bride_price = D.MARRIAGE_COST["彩礼"][tier]
        wedding = D.MARRIAGE_COST["婚礼"]["base"] * cf

        hp = D.HOUSE_PURCHASE[tier]
        if self._marriage_purchase.get() == "全款":
            house = hp["total"]
        else:
            house = hp["downpayment"]

        total = bride_price + wedding + house

        self._marriage_labels["彩礼"].config(text=f"{bride_price:,.0f} 元")
        self._marriage_labels["婚礼婚宴"].config(text=f"{wedding:,.0f} 元")
        self._marriage_labels["婚房首付"].config(
            text=f"{house:,.0f} 元"
                 + (f"（月供约 {hp['monthly_loan']:,.0f} 元/月×30年）" if "贷款" in self._marriage_purchase.get() else ""))

        self._marriage_total.config(text=D.fmt_money(total))
        self._marriage_years.config(text=self._afford_years_label(total))
        self._computed["marriage"] = True

    # ============================================================
    # 第二座山：养娃
    # ============================================================
    def _build_child(self):
        box = W.CardFrame(self._content, title="第二座山：养一个孩子要多少钱", padding=10)
        box.pack(side="top", fill="x", padx=8, pady=4)
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="养育路线：").grid(row=0, column=0, sticky="w", pady=4)
        # make_radio_group 内部新建并绑定 StringVar，必须接住它返回的 var，
        # 否则 Radiobutton 改的是被丢弃的 var，self._child_level 永不更新。
        f, self._child_level = W.make_radio_group(
            box, "", options=["普惠", "中产", "高端"],
            default="普惠", columns=3,
            descriptions={
                "普惠": "公办学校+基础养育",
                "中产": "部分民办+课外班",
                "高端": "国际学校+精英路线",
            },
            command=self._update_child)
        f.grid(row=0, column=1, sticky="w", pady=4)

        ttk.Label(box, text="大学类型：").grid(row=1, column=0, sticky="w", pady=3)
        self._child_uni = tk.StringVar(value="公办")
        ttk.Combobox(box, textvariable=self._child_uni, width=8,
                     values=["公办", "民办"], state="readonly").grid(row=1, column=1, sticky="w")
        self._child_uni.trace_add("write", lambda *_: self._update_child())

        ttk.Separator(box, orient="horizontal").grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=6)

        ttk.Label(box, text="0-22岁累计：").grid(row=3, column=0, sticky="w")
        self._child_total = ttk.Label(box, text="—", font=W.FONT_RESULT,
                                       foreground=W.COLOR_ACCENT)
        self._child_total.grid(row=3, column=1, sticky="w")

        ttk.Label(box, text="年均成本：").grid(row=4, column=0, sticky="w")
        self._child_annual = ttk.Label(box, text="", style="Sub.TLabel")
        self._child_annual.grid(row=4, column=1, sticky="w")

        # 使用计算器1的部分结果
        ttk.Label(box, text="你每月需多支出：").grid(row=5, column=0, sticky="w", pady=4)
        self._child_monthly = ttk.Label(box, text="", font=W.FONT_RESULT,
                                         foreground="#c0392b")
        self._child_monthly.grid(row=5, column=1, sticky="w")

        self._child_ratio = ttk.Label(box, text="")
        self._child_ratio.grid(row=6, column=0, columnspan=2, sticky="w", pady=(2, 4))

        ttk.Button(box, text="计算养娃成本",
                   command=self._update_child).grid(row=7, column=0, columnspan=2,
                                                     sticky="ew", pady=6)

    def _update_child(self):
        tier = self.var_tier.get()
        level = self._child_level.get()
        uni = self._child_uni.get()

        # 复用生命周期计算的部分结果
        result = E.compute_life_cost(tier, level, uni_type=uni, graduate=False)
        edu_total = next((s["amount"] for s in result["stage_subtotals"]
                          if "养育" in s["stage"]), 0)

        self._child_total.config(text=D.fmt_money(edu_total))
        self._child_annual.config(text=f"平均每年约 {edu_total/22:,.0f} 元"
                                       f"（0-22岁共22年）")

        monthly = edu_total / (22 * 12)
        self._child_monthly.config(text=f"折合每月 {monthly:,.0f} 元")
        self._computed["child"] = True
        ms = self._monthly_surplus()
        if ms > 0:
            ratio = monthly / ms * 100
            if ratio > 100:
                self._child_ratio.config(
                    text=f"⚠️ 占你月结余的 {ratio:.0f}%，将耗尽你的全部结余！",
                    foreground="#c0392b", font=(W.FONT_FAMILY, 12, "bold"))
            elif ratio >= 50:
                self._child_ratio.config(
                    text=f"⚠️ 占你月结余的 {ratio:.0f}%，压力较大",
                    foreground="#e67e22", font=(W.FONT_FAMILY, 11, "bold"))
            else:
                self._child_ratio.config(
                    text=f"✅ 占你月结余的 {ratio:.0f}%，在你承受范围内",
                    foreground="#1a7d3a", font=(W.FONT_FAMILY, 11, "bold"))
        else:
            self._child_ratio.config(
                text="⚠️ 你目前没有结余，养娃需要另寻经济来源！",
                foreground="#c0392b", font=(W.FONT_FAMILY, 12, "bold"))

    def _get_common_inputs(self):
        """获取公共输入：tier, wage, insurance_type"""
        return self.var_tier.get(), self._wage(), "在职（单位缴）"

    # ============================================================
    # 第三座山：养老
    # ============================================================
    def _build_retirement(self):
        box = W.CardFrame(self._content, title="第三座山：养老需要多少钱", padding=10)
        box.pack(side="top", fill="x", padx=8, pady=4)
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="养老方式：").grid(row=0, column=0, sticky="w", pady=4)
        # 接住 make_radio_group 返回的 var，确保选项切换能更新 self._retire_mode
        f, self._retire_mode = W.make_radio_group(
            box, "", options=["居家养老", "普惠养老机构", "中高端养老机构"],
            default="居家养老", columns=3,
            command=self._update_retirement)
        f.grid(row=0, column=1, sticky="w", pady=4)

        ttk.Label(box, text="退休年龄：").grid(row=1, column=0, sticky="w", pady=3)
        self._retire_age = tk.IntVar(value=60)
        ttk.Spinbox(box, from_=55, to=65, textvariable=self._retire_age,
                    width=8, command=self._update_retirement).grid(row=1, column=1, sticky="w")

        ttk.Separator(box, orient="horizontal").grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=6)

        ttk.Label(box, text="退休后每月养老金：").grid(row=3, column=0, sticky="w")
        self._retire_pension = ttk.Label(box, text="—", font=W.FONT_RESULT)
        self._retire_pension.grid(row=3, column=1, sticky="w")

        ttk.Label(box, text="退休后每月支出：").grid(row=4, column=0, sticky="w")
        self._retire_cost = ttk.Label(box, text="—", font=W.FONT_RESULT,
                                       foreground=W.COLOR_DEFICIT)
        self._retire_cost.grid(row=4, column=1, sticky="w")

        ttk.Label(box, text="每月缺口：").grid(row=5, column=0, sticky="w")
        self._retire_gap = ttk.Label(box, text="", font=W.FONT_RESULT)
        self._retire_gap.grid(row=5, column=1, sticky="w")

        self._retire_tip = ttk.Label(box, text="", style="Sub.TLabel", wraplength=500)
        self._retire_tip.grid(row=6, column=0, columnspan=2, sticky="w", pady=4)

        ttk.Button(box, text="计算养老缺口",
                   command=self._update_retirement).grid(row=7, column=0, columnspan=2,
                                                         sticky="ew", pady=6)

    def _update_retirement(self):
        tier = self.var_tier.get()
        mode = self._retire_mode.get()
        retire_age = self._retire_age.get()
        years = D.LIFE_EXPECTANCY - retire_age
        self._computed["retire"] = True

        pension = D.RETIREMENT["pension_monthly"][tier]
        care = D.RETIREMENT["care_monthly"][E.CARE_MODE_MAP[mode]][tier]

        gap = pension - care  # 负数=不够

        self._retire_pension.config(text=f"{pension:,} 元/月")
        self._retire_cost.config(text=f"{care:,} 元/月")
        if gap >= 0:
            self._retire_gap.config(text=f"无缺口 ✅（每月多出 {gap:,} 元）",
                                     foreground=W.COLOR_SURPLUS)
        else:
            self._retire_gap.config(text=f"每月缺口 {-gap:,} 元 ⚠️",
                                     foreground=W.COLOR_DEFICIT)
            total_gap = -gap * 12 * years
            tip = (f"退休后 {years} 年（{retire_age}~{D.LIFE_EXPECTANCY}岁），"
                   f"总缺口约 {total_gap:,.0f} 元。"
                   f"如果从现在起每月多存 {-gap:,} 元，可填补缺口。")
            self._retire_tip.config(text=tip)
