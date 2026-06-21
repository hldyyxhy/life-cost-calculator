# -*- coding: utf-8 -*-
"""
page_rights.py —— 劳动权益：补「该拿的没拿、该维权的没维」的信息差

底层劳动者最常吃的亏之一，就是劳动权益被侵害却不知道。本页放**无需各地数据**的法定计算：
  ① 加班费依法反算：月薪 + 各类加班时长 → 依法应得加班费（《劳动法》150%/200%/300%）
  ② 最低工资对照：月薪 → 当地最低工资，低于即违法

失业金 / 灵活就业社保补贴 / 工伤等需各地数据的，见 ../调研数据/07_待补数据清单.md，
数据补齐后再接入对应计算（沿用本页模式）。
"""
import tkinter as tk
from tkinter import ttk

import calc_engine as E
import cost_data as D
import gui_widgets as W
import rights_data as R


class RightsPage(ttk.Frame):
    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self._profile_city = ""  # 从档案同步的城市名
        self._profile_tier = ""  # 从档案同步的城市等级
        self._profile = {}       # 缓存整个档案，供「问 AI」提示词补 age/gender/wage 等
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=8, pady=8)

        def new_tab(title):
            tab = ttk.Frame(self._nb)
            self._nb.add(tab, text=title)
            sf = W.ScrollableFrame(tab)
            sf.pack(fill="both", expand=True)
            return sf.inner

        c1 = new_tab("① 加班费")
        self._build_overtime(c1)
        self._build_ask_ai(c1)
        self._build_min_wage(new_tab("② 最低工资"))
        self._build_unemployment(new_tab("③ 失业金"))
        self._build_subsidy(new_tab("④ 4050 补贴"))
        self._build_injury(new_tab("⑤ 工伤"))
        self._build_tax(new_tab("⑥ 个税优化"))
        self._build_assistance(new_tab("⑦ 本地救助"))
        self._nb.select(0)

    # ---------- 档案载入（从档案页「确定」同步接收）----------
    def apply_profile(self, prof):
        """把档案中的城市信息同步到各tab的城市输入框。"""
        self._profile = prof
        self._profile_city = prof.get("city", "")
        self._profile_tier = prof.get("tier", "")
        # 填充各tab的城市组合框
        city = self._profile_city
        if city:
            # 最低工资tab的城市等级
            if hasattr(self, "var_mw_tier") and self._profile_tier:
                self.var_mw_tier.set(self._profile_tier)
            # 失业金tab
            if hasattr(self, "var_un_city") and city in R.CITY_TO_PROVINCE:
                self.var_un_city.set(city)
            # 4050补贴tab
            if hasattr(self, "var_sub_city") and city in R.CITY_TO_PROVINCE:
                self.var_sub_city.set(city)
            # 工伤tab
            if hasattr(self, "var_inj_city") and city in R.CITY_TO_PROVINCE:
                self.var_inj_city.set(city)
            if hasattr(self, "var_assist_city"):
                self.var_assist_city.set(city)

    # ---------- 通用：只读解读 Text ----------
    def _make_note(self, parent, height=6, grid=None):
        return W.readonly_note(parent, height=height, grid=grid)

    def _set_note(self, tw, text):
        tw.set_smart_text(text)

    # ============================================================
    # 加班费依法反算
    # ============================================================
    def _build_overtime(self, c):
        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=4)
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="加班费依法反算", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Label(form,
                  text="按《劳动法》第44条：工作日延时加班 1.5 倍、休息日加班 2 倍、"
                       "法定节假日加班 3 倍。时薪 = 月工资 ÷ 21.75 ÷ 8。",
                  style="Sub.TLabel", wraplength=560, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(form, text="月工资（元）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_ot_wage = tk.StringVar(value="6000")
        ttk.Entry(form, textvariable=self.var_ot_wage, width=14).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="工作日加班（小时/月）：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_ot_weekday = tk.IntVar(value=40)
        ttk.Spinbox(form, from_=0, to=400, textvariable=self.var_ot_weekday,
                    width=10).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="休息日加班（小时/月）：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_ot_weekend = tk.IntVar(value=16)
        ttk.Spinbox(form, from_=0, to=400, textvariable=self.var_ot_weekend,
                    width=10).grid(row=4, column=1, sticky="w")
        ttk.Label(form, text="法定节假日加班（小时/月）：").grid(row=5, column=0, sticky="w", pady=3)
        self.var_ot_holiday = tk.IntVar(value=8)
        ttk.Spinbox(form, from_=0, to=400, textvariable=self.var_ot_holiday,
                    width=10).grid(row=5, column=1, sticky="w")
        ttk.Separator(form, orient="horizontal").grid(row=6, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(form, text="维权现实评估（算算值不值得去争）", style="Header.TLabel").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Label(form, text="每月实际拿到的加班费（元）：").grid(row=8, column=0, sticky="w", pady=3)
        self.var_ot_actual = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.var_ot_actual, width=14).grid(row=8, column=1, sticky="w")
        ttk.Label(form, text="这种情况持续了几个月：").grid(row=9, column=0, sticky="w", pady=3)
        self.var_ot_months = tk.IntVar(value=1)
        ttk.Spinbox(form, from_=1, to=60, textvariable=self.var_ot_months, width=10).grid(
            row=9, column=1, sticky="w")
        ttk.Label(form, text="是否还在职：").grid(row=10, column=0, sticky="w", pady=3)
        emp = ttk.Frame(form)
        emp.grid(row=10, column=1, sticky="w")
        self.var_ot_employed = tk.StringVar(value="在职")
        ttk.Radiobutton(emp, text="在职", value="在职", variable=self.var_ot_employed).pack(side="left")
        ttk.Radiobutton(emp, text="已离职", value="已离职", variable=self.var_ot_employed).pack(side="left", padx=8)
        ttk.Label(form, text="你的证据情况：").grid(row=11, column=0, sticky="w", pady=3)
        self.var_ot_evidence = tk.StringVar(value="部分")
        ttk.Combobox(form, textvariable=self.var_ot_evidence,
                     values=["充分", "部分", "几乎没有"], state="readonly", width=12).grid(
            row=11, column=1, sticky="w")
        ttk.Button(form, text="反算加班费 + 维权评估", command=self.on_overtime_compute).grid(
            row=12, column=0, columnspan=2, sticky="ew", pady=(12, 2))

        res = W.CardFrame(c, padding=10)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        res.columnconfigure(0, weight=1)
        self.lbl_ot_total = ttk.Label(res, text="—", font=W.FONT_BIG, foreground=W.COLOR_ACCENT)
        self.lbl_ot_total.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.lbl_ot_hourly = ttk.Label(res, text="", font=W.FONT_RESULT)
        self.lbl_ot_hourly.grid(row=1, column=0, sticky="w")
        self.ot_tree = W.ResultTreeview(
            res,
            columns=[("type", "类型", "w"), ("hours", "小时", "e"),
                     ("rate", "倍数", "center"), ("pay", "金额(元)", "e")],
            col_widths={"type": 140, "hours": 90, "rate": 90, "pay": 140}, height=5)
        self.ot_tree.grid(row=2, column=0, sticky="ew", pady=(8, 8))
        ttk.Label(res, text="说明", style="Header.TLabel").grid(
            row=3, column=0, sticky="w", pady=(4, 4))
        self.txt_ot = self._make_note(res, height=4, grid=dict(row=4, column=0, sticky="ew"))

        ttk.Separator(res, orient="horizontal").grid(row=5, column=0, sticky="ew", pady=8)
        ttk.Label(res, text="维权现实评估", style="Header.TLabel").grid(
            row=6, column=0, sticky="w", pady=(0, 4))
        self.lbl_ot_verdict = ttk.Label(res, text="", font=W.FONT_BIG)
        self.lbl_ot_verdict.grid(row=7, column=0, sticky="w", pady=(0, 4))
        self.lbl_ot_claim_summary = ttk.Label(res, text="", font=W.FONT_RESULT, justify="left")
        self.lbl_ot_claim_summary.grid(row=8, column=0, sticky="w")
        self.txt_ot_claim = self._make_note(res, height=6, grid=dict(row=9, column=0, sticky="ew"))

    def on_overtime_compute(self):
        try:
            wage = float(self.var_ot_wage.get())
            wd = int(self.var_ot_weekday.get())
            we = int(self.var_ot_weekend.get())
            ho = int(self.var_ot_holiday.get())
            actual = float(self.var_ot_actual.get())
            months = int(self.var_ot_months.get())
        except ValueError:
            self._set_note(self.txt_ot, "请输入有效的数字。")
            return
        r = E.compute_overtime_pay(wage, wd, we, ho)
        if "error" in r:
            self.lbl_ot_total.config(text="—", foreground=W.COLOR_DEFICIT)
            self.lbl_ot_hourly.config(text="")
            self.ot_tree.clear()
            self._set_note(self.txt_ot, r["error"])
            self.lbl_ot_verdict.config(text="")
            self.lbl_ot_claim_summary.config(text="")
            self._set_note(self.txt_ot_claim, "")
            return
        self.lbl_ot_total.config(
            text=f"依法应得加班费 {r['total_overtime']:,.0f} 元/月",
            foreground=(W.COLOR_SURPLUS if r["total_overtime"] > 0 else W.COLOR_ACCENT))
        self.lbl_ot_hourly.config(text=f"你的法定时薪：{r['hourly_wage']:.2f} 元/小时")
        self.ot_tree.clear()
        for d in r["detail"]:
            self.ot_tree.add_row([d["type"], f"{d['hours']}", f"{d['rate']} 倍", f"{d['pay']:,.0f}"])
        self._set_note(self.txt_ot, r["note"])

        # 维权现实评估：被欠总额 = 每月被欠 × 月数
        months = max(1, months)
        owed_monthly = max(0.0, r["total_overtime"] - actual)
        owed = owed_monthly * months
        self.lbl_ot_claim_summary.config(
            text=(f"每月被欠 {owed_monthly:,.0f} 元 × {months} 月 ≈ 被欠总额 {owed:,.0f} 元"))
        if owed <= 0:
            self.lbl_ot_verdict.config(text="没有被欠的加班费", foreground=W.COLOR_SURPLUS)
            self._set_note(self.txt_ot_claim,
                           "你实际拿到的加班费已达到依法应得，没有被欠部分，无需维权。")
            return
        employed = self.var_ot_employed.get() == "在职"
        evidence = self.var_ot_evidence.get()
        claim = E.assess_overtime_claim(owed, employed=employed, evidence=evidence)
        if "error" in claim:
            self.lbl_ot_verdict.config(text="—", foreground=W.COLOR_DEFICIT)
            self._set_note(self.txt_ot_claim, claim["error"])
            return
        color = {"good": W.COLOR_SURPLUS, "caution": "#e67e22",
                 "warn": W.COLOR_DEFICIT}.get(claim["verdict_level"], "#222")
        self.lbl_ot_verdict.config(text=claim["verdict"], foreground=color)
        self._set_note(self.txt_ot_claim, claim["note"])

    # ============================================================
    # 问 AI：点按钮弹窗显示提示词（主界面只留一个小按钮，复用通用弹窗）
    # ============================================================
    def _build_ask_ai(self, c):
        bar = ttk.Frame(c)
        bar.pack(side="top", fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="生成「问 AI」的提示词（拿更详细的建议）",
                   style="AskAI.TButton",
                   command=self._open_overtime_prompt).pack(side="left")

    def _current_overtime_prompt(self, city):
        """用当前加班费输入组装提示词；数字无效时返回提示语。"""
        try:
            wage = float(self.var_ot_wage.get())
            wd = int(self.var_ot_weekday.get())
            we = int(self.var_ot_weekend.get())
            ho = int(self.var_ot_holiday.get())
            actual = float(self.var_ot_actual.get())
            months = int(self.var_ot_months.get())
        except ValueError:
            return "请先把上方「加班费依法反算」里的数字填有效，再生成提示词。"
        employed = self.var_ot_employed.get() == "在职"
        evidence = self.var_ot_evidence.get()
        return E.build_overtime_prompt(wage, wd, we, ho, actual, max(1, months),
                                       employed, evidence, city)

    def _open_overtime_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI 的提示词（加班费维权）",
            build_fn=self._current_overtime_prompt, with_city=True,
            initial_city=self._profile_city,
            intro="工具算的是「死数」。把下面这段复制到任意 AI（豆包/Kimi/DeepSeek 等）去问，"
                  "它会结合最新政策给你详细得多的回答。")

    # ============================================================
    # 失业金对照（用 rights_data 本地算）
    # ============================================================
    def _build_unemployment(self, c):
        box = W.CardFrame(c, title="失业金对照（被裁能领多少）", padding=10)
        box.pack(side="top", fill="x", padx=8, pady=4)
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="你参保的城市：").grid(row=0, column=0, sticky="w", pady=3)
        self.var_un_city = tk.StringVar(value="北京")
        ttk.Combobox(box, textvariable=self.var_un_city,
                     values=R.CITY_NAMES, width=12).grid(
            row=0, column=1, sticky="w")
        ttk.Label(box, text="累计缴费年限（年）：").grid(row=1, column=0, sticky="w", pady=3)
        self.var_un_years = tk.IntVar(value=6)
        ttk.Spinbox(box, from_=1, to=30, textvariable=self.var_un_years,
                    width=10).grid(row=1, column=1, sticky="w")
        ttk.Button(box, text="算我能领多少失业金",
                   command=self.on_unemployment_compute).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        self.lbl_un_result = ttk.Label(box, text="—", font=W.FONT_BIG,
                                       foreground=W.COLOR_SURPLUS)
        self.lbl_un_result.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.lbl_un_detail = ttk.Label(box, text="", font=W.FONT_RESULT, justify="left")
        self.lbl_un_detail.grid(row=4, column=0, columnspan=2, sticky="w")
        self.txt_un = self._make_note(
            box, height=4, grid=dict(row=5, column=0, columnspan=2, sticky="ew"))
        ttk.Button(box, text="生成「问 AI」的提示词（让 AI 说清怎么领）",
                   style="AskAI.TButton",
                   command=self._open_unemployment_prompt).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    def on_unemployment_compute(self):
        city = self.var_un_city.get().strip()
        try:
            years = int(self.var_un_years.get())
        except ValueError:
            self._set_note(self.txt_un, "缴费年限请填数字。")
            return
        amt, note = R.estimate_unemployment_pay(city)
        months = R.unemploy_duration(years)
        if amt:
            total = amt * months
            self.lbl_un_result.config(
                text=f"每月约 {amt:,} 元 × 最长 {months} 个月 ≈ {total:,} 元",
                foreground=W.COLOR_SURPLUS)
            self.lbl_un_detail.config(text=f"标准来源：{note}")
            cond = "；".join(f"{k}：{v}" for k, v in list(R.UNEMPLOYMENT_CONDITIONS.items())[:3])
            self._set_note(
                self.txt_un,
                f"申领条件：{cond}\n常用渠道：{'、'.join(R.UNEMPLOYMENT_CHANNELS[:3])} 等。"
                f"具体以当地社保局最新公告为准。")
        else:
            self.lbl_un_result.config(text="暂无精确数据", foreground=W.COLOR_DEFICIT)
            self.lbl_un_detail.config(text="")
            self._set_note(
                self.txt_un,
                f"暂无 {city} 的精确数据。{note}可以用下方「问 AI」让 AI 帮你查最新标准。")

    # ============================================================
    # 4050 灵活就业社保补贴对照（用 rights_data 本地查）
    # ============================================================
    def _lookup_subsidy(self, city):
        """城市 → (匹配键, 补贴数据dict)；查不到数据时 dict 为 None。"""
        if city in R.FLEXIBLE_SUBSIDY_PROVINCE:
            return city, R.FLEXIBLE_SUBSIDY_PROVINCE[city]
        prov = R.CITY_TO_PROVINCE.get(city, city)
        if prov in R.FLEXIBLE_SUBSIDY_PROVINCE:
            return prov, R.FLEXIBLE_SUBSIDY_PROVINCE[prov]
        for key in R.FLEXIBLE_SUBSIDY_PROVINCE:
            if key.startswith(prov + "（") or key.startswith(prov + "("):
                return key, R.FLEXIBLE_SUBSIDY_PROVINCE[key]
        return prov, None

    def _build_subsidy(self, c):
        box = W.CardFrame(c, title="灵活就业社保补贴（4050）对照", padding=10)
        box.pack(side="top", fill="x", padx=8, pady=4)
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="你所在的城市：").grid(row=0, column=0, sticky="w", pady=3)
        self.var_sub_city = tk.StringVar(value="北京")
        ttk.Combobox(box, textvariable=self.var_sub_city,
                     values=R.CITY_NAMES, width=12).grid(
            row=0, column=1, sticky="w")
        ttk.Button(box, text="查我所在地的补贴标准",
                   command=self.on_subsidy_compute).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        self.lbl_sub_result = ttk.Label(box, text="—", font=W.FONT_BIG,
                                        foreground=W.COLOR_SURPLUS)
        self.lbl_sub_result.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.lbl_sub_detail = ttk.Label(box, text="", font=W.FONT_RESULT, justify="left")
        self.lbl_sub_detail.grid(row=3, column=0, columnspan=2, sticky="w")
        self.txt_sub = self._make_note(
            box, height=5, grid=dict(row=4, column=0, columnspan=2, sticky="ew"))
        ttk.Button(box, text="生成「问 AI」的提示词（让 AI 说清怎么办）",
                   style="AskAI.TButton", command=self._open_subsidy_prompt).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    def on_subsidy_compute(self):
        city = self.var_sub_city.get().strip()
        key, data = self._lookup_subsidy(city)
        rules = R.FLEXIBLE_SUBSIDY_RULES
        if data:
            amt = data.get("amount_est")
            t = data.get("type", "")
            note = data.get("note", "")
            amt_txt = f"约 {amt:,} 元/月" if amt else "见说明"
            self.lbl_sub_result.config(text=f"{key}：{amt_txt}（{t}）",
                                       foreground=W.COLOR_SURPLUS)
            self.lbl_sub_detail.config(text=note or "—")
            cond = "；".join(rules["对象条件"])
            self._set_note(
                self.txt_sub,
                f"适用条件：{cond}\n补贴原则：{rules['补贴原则']}；期限：{rules['补贴期限']}\n"
                f"常见被拒：只缴居民社保、有单位缴社保、名下有营业执照、正在领失业金、"
                f"已领过一次等。可在 {rules['线上渠道']} 申请，咨询 {rules['咨询热线']}。")
        else:
            self.lbl_sub_result.config(text=f"{key}：暂未收录精确标准",
                                       foreground=W.COLOR_DEFICIT)
            self.lbl_sub_detail.config(text="")
            self._set_note(
                self.txt_sub,
                f"暂无 {city}（{key}）的精确数据，可用下方「问 AI」查最新标准。\n"
                f"通用规则：{rules['对象条件'][0]}等，{rules['补贴原则']}。")

    # ============================================================
    # 工伤赔偿估算（用 rights_data 本地算）
    # ============================================================
    def _build_injury(self, c):
        box = W.CardFrame(c, title="工伤赔偿估算", padding=10)
        box.pack(side="top", fill="x", padx=8, pady=4)
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="你所在的城市：").grid(row=0, column=0, sticky="w", pady=3)
        self.var_inj_city = tk.StringVar(value="广州")
        ttk.Combobox(box, textvariable=self.var_inj_city,
                     values=R.CITY_NAMES, width=12).grid(
            row=0, column=1, sticky="w")
        ttk.Label(box, text="伤残等级（1=最重 ~ 10=最轻）：").grid(row=1, column=0, sticky="w", pady=3)
        self.var_inj_grade = tk.IntVar(value=7)
        ttk.Spinbox(box, from_=1, to=10, textvariable=self.var_inj_grade,
                    width=8).grid(row=1, column=1, sticky="w")
        ttk.Label(box, text="受伤前月平均工资（元）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_inj_wage = tk.StringVar(value="6000")
        ttk.Entry(box, textvariable=self.var_inj_wage, width=12).grid(row=2, column=1, sticky="w")
        ttk.Button(box, text="估算工伤赔偿",
                   command=self.on_injury_compute).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        self.lbl_inj_result = ttk.Label(box, text="—", font=W.FONT_BIG,
                                        foreground=W.COLOR_DEFICIT)
        self.lbl_inj_result.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.txt_inj = self._make_note(
            box, height=5, grid=dict(row=5, column=0, columnspan=2, sticky="ew"))
        ttk.Button(box, text="生成「问 AI」的提示词（让 AI 讲认定流程）",
                   style="AskAI.TButton", command=self._open_injury_prompt).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    def on_injury_compute(self):
        city = self.var_inj_city.get().strip()
        try:
            grade = int(self.var_inj_grade.get())
            wage = float(self.var_inj_wage.get())
        except ValueError:
            self._set_note(self.txt_inj, "伤残等级和工资请填数字。")
            return
        if not (1 <= grade <= 10):
            self._set_note(self.txt_inj, "伤残等级应为 1-10 级。")
            return
        months, one_time = R.calc_injury_one_time(grade, wage)
        ratio, pension, payer = R.calc_injury_pension(grade, wage)
        prov = R.CITY_TO_PROVINCE.get(city, city)
        med, emp, base_note = R.get_province_injury_extra(prov, grade)
        self.lbl_inj_result.config(
            text=f"一次性伤残补助金：{months} 个月 × {wage:,.0f} = {one_time:,.0f} 元",
            foreground=W.COLOR_DEFICIT)
        lines = [f"· 一次性伤残补助金：{one_time:,.0f} 元（{months} 个月本人工资，工伤保险基金支付）"]
        if ratio:
            lines.append(f"· 伤残津贴：{pension:,.0f} 元/月（本人工资的 {ratio*100:.0f}%，{payer}支付）")
        else:
            lines.append("· 伤残津贴：7-10 级不享受按月伤残津贴")
        if med is not None:
            med_txt = f"{med} 个月" if med else "未收录"
            emp_txt = f"{emp} 个月" if emp else "未收录"
            lines.append(f"· 一次性医疗/就业补助金（{prov}）：医疗 {med_txt}、就业 {emp_txt}（基数：{base_note}，需解除劳动关系）")
        lines.append(f"· 工亡补助金（全国统一）：{R.WORK_INJURY_DEATH_COMPENSATION:,} 元")
        self._set_note(
            self.txt_inj,
            "\n".join(lines) +
            "\n\n说明：以上为法定基准估算，各省另有差异；停工留薪期工资由单位按原工资发放。"
            "具体以《工伤保险条例》和当地细则为准。")

    def _open_injury_prompt(self):
        def build(city):
            try:
                grade = int(self.var_inj_grade.get())
                wage = float(self.var_inj_wage.get())
            except ValueError:
                grade, wage = 7, 6000
            use_city = city or self.var_inj_city.get().strip()
            return E.build_injury_prompt(use_city, grade, wage, profile=self._profile)
        W.open_prompt_dialog(
            self, "问 AI 的提示词（工伤赔偿）", with_city=True,
            build_fn=build, initial_city=self._profile_city,
            intro="把下面这段复制到任意 AI，它会确认赔偿项目、讲清工伤认定和鉴定流程。")

    def _open_minwage_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI 的提示词（最低工资对照）", with_city=True,
            initial_city=self._profile_city,
            build_fn=lambda city: E.build_min_wage_prompt(
                float(self.var_mw_wage.get()), self.var_mw_tier.get(), city,
                profile=self._profile))

    def _open_unemployment_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI 的提示词（失业金）", with_city=True,
            initial_city=self._profile_city,
            build_fn=lambda city: E.build_unemployment_prompt(
                city, years=self.var_un_years.get(),
                wage=self._profile.get("wage", ""), profile=self._profile),
            intro="把下面这段复制到任意 AI，它会先问你必要的信息（缴费年限、工资、离职原因等），"
                  "再结合你所在城市查最新规定，告诉你能领多少、怎么领。")

    def _open_subsidy_prompt(self):
        W.open_prompt_dialog(
            self, "问 AI 的提示词（灵活就业社保补贴 / 4050）", with_city=True,
            initial_city=self._profile_city,
            build_fn=lambda city: E.build_subsidy_prompt(
                city, profile=self._profile),
            intro="把下面这段复制到任意 AI，它会先问你必要的信息（年龄、是否自缴社保等），"
                  "再结合你所在城市查最新规定，告诉你能不能领、领多少、怎么申请。")

    # ============================================================
    # 个税优化（年终奖单独 vs 合并 / 专项附加扣除）
    # ============================================================
    def _build_tax(self, c):
        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="年终奖怎么交税更省？专项扣除用足了吗？",
                  style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(form, text="月薪（元）：").grid(row=1, column=0, sticky="w", pady=3)
        self.var_tax_wage = tk.StringVar(value="8000")
        ttk.Entry(form, textvariable=self.var_tax_wage, width=12).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="年终奖（元）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_tax_bonus = tk.StringVar(value="30000")
        ttk.Entry(form, textvariable=self.var_tax_bonus, width=12).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="月专项扣除合计（元）：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_tax_special = tk.StringVar(value="3000")
        ttk.Entry(form, textvariable=self.var_tax_special, width=12).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="月社保个人部分（元）：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_tax_social = tk.StringVar(value="1500")
        ttk.Entry(form, textvariable=self.var_tax_social, width=12).grid(row=4, column=1, sticky="w")
        ttk.Label(form, text="家庭情况：").grid(row=5, column=0, sticky="w", pady=3)
        fam = ttk.Frame(form)
        fam.grid(row=5, column=1, sticky="w")
        self.var_tax_kids = tk.IntVar(value=0)
        self.var_tax_elderly = tk.BooleanVar(value=False)
        self.var_tax_loan = tk.BooleanVar(value=False)
        self.var_tax_edu = tk.BooleanVar(value=False)
        ttk.Label(fam, text="子女").pack(side="left")
        ttk.Spinbox(fam, from_=0, to=6, textvariable=self.var_tax_kids,
                    width=3).pack(side="left", padx=2)
        ttk.Checkbutton(fam, text="赡养老人", variable=self.var_tax_elderly).pack(side="left", padx=4)
        ttk.Checkbutton(fam, text="有房贷", variable=self.var_tax_loan).pack(side="left", padx=2)
        ttk.Checkbutton(fam, text="继续教育", variable=self.var_tax_edu).pack(side="left", padx=2)
        ttk.Button(form, text="▶ 算一算",
                   command=self.on_tax).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 2))

        res = W.CardFrame(c, padding=8)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        ttk.Label(res, text="结果", style="Header.TLabel").pack(anchor="w", pady=(0, 4))
        self.txt_tax = W.readonly_note(res, height=12, bg="#f0f7f0")
        ttk.Button(res, text="生成「问 AI」的提示词（结合最新个税政策）",
                   style="AskAI.TButton",
                   command=self._open_tax_prompt).pack(anchor="w", pady=(8, 0))

    def on_tax(self):
        try:
            wage = float(self.var_tax_wage.get() or 0)
            bonus = float(self.var_tax_bonus.get() or 0)
            special_m = float(self.var_tax_special.get() or 0)
            social_m = float(self.var_tax_social.get() or 0)
        except ValueError:
            self._set_note(self.txt_tax, "请输入有效的数字。")
            return
        r = E.bonus_tax_compare(wage * 12, bonus,
                                annual_special=special_m * 12, annual_social=social_m * 12)
        if "error" in r:
            self._set_note(self.txt_tax, r["error"])
            return
        hints = E.special_deduction_hints(
            has_children=int(self.var_tax_kids.get()),
            support_elderly=self.var_tax_elderly.get(),
            has_loan=self.var_tax_loan.get(),
            continuing_edu=self.var_tax_edu.get())
        text = r["note"] + "\n\n【专项附加扣除提醒】\n" + \
            "\n".join("· " + h for h in hints)
        self._set_note(self.txt_tax, text)

    def _open_tax_prompt(self):
        wage = float(self.var_tax_wage.get() or 0)
        bonus = float(self.var_tax_bonus.get() or 0)
        special = float(self.var_tax_special.get() or 0)
        social = float(self.var_tax_social.get() or 0)
        W.open_prompt_dialog(
            self, "问 AI（个税优化）", with_city=True,
            build_fn=lambda city: E.build_tax_prompt(
                wage * 12, bonus, city, special=special, social=social,
                kids=int(self.var_tax_kids.get()),
                elderly=self.var_tax_elderly.get(),
                loan=self.var_tax_loan.get(),
                edu=self.var_tax_edu.get(), profile=self._profile),
            initial_city=self._profile_city,
            intro="把这段复制给 AI，它会算年终奖单独vs合并、专项扣除、全年税额，给在个税APP操作的建议。")

    # ============================================================
    # 本地救助对照（低保 / 边缘 / 特困）
    # ============================================================
    def _build_assistance(self, c):
        box = W.CardFrame(c, title="本地救助对照（我符合低保 / 边缘吗）", padding=10)
        box.pack(side="top", fill="x", padx=8, pady=4)
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="你所在的城市：").grid(row=0, column=0, sticky="w", pady=3)
        self.var_assist_city = tk.StringVar(value="北京")
        ttk.Combobox(box, textvariable=self.var_assist_city,
                     values=R.CITY_NAMES, width=12).grid(row=0, column=1, sticky="w")
        ttk.Label(box, text="家庭人均月收入（元）：").grid(row=1, column=0, sticky="w", pady=3)
        self.var_assist_income = tk.StringVar(value="1500")
        ttk.Entry(box, textvariable=self.var_assist_income, width=12).grid(row=1, column=1, sticky="w")
        ttk.Label(box, text="家庭人数：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_assist_size = tk.IntVar(value=3)
        ttk.Spinbox(box, from_=1, to=10, textvariable=self.var_assist_size,
                    width=8).grid(row=2, column=1, sticky="w")
        ttk.Label(box, text="人均金融资产（元，可选）：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_assist_asset = tk.StringVar(value="")
        ttk.Entry(box, textvariable=self.var_assist_asset, width=12).grid(row=3, column=1, sticky="w")
        ttk.Button(box, text="对照本地救助标准",
                   command=self.on_assistance_compute).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        self.lbl_assist_result = ttk.Label(box, text="—", font=W.FONT_BIG,
                                           foreground=W.COLOR_ACCENT)
        self.lbl_assist_result.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.txt_assist = self._make_note(
            box, height=7, grid=dict(row=6, column=0, columnspan=2, sticky="ew"))
        ttk.Button(box, text="生成「问 AI」的提示词（查当地最新救助政策）",
                   style="AskAI.TButton",
                   command=self._open_assistance_prompt).grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    def on_assistance_compute(self):
        city = self.var_assist_city.get().strip()
        try:
            income = float(self.var_assist_income.get() or 0)
        except ValueError:
            self._set_note(self.txt_assist, "人均月收入请填数字。")
            return
        size = int(self.var_assist_size.get() or 1)
        asset_s = self.var_assist_asset.get().strip()
        asset = float(asset_s) if asset_s else None
        r = E.check_relief(city, income, family_size=size, asset=asset)
        if "error" in r:
            self.lbl_assist_result.config(text="⚠️ 该城市数据未收录", foreground=W.COLOR_DEFICIT)
            self._set_note(self.txt_assist,
                f"数据库未收录「{city}」的低保标准，无法对照。建议用下方「问 AI」查当地最新救助政策。")
            return
        color = {"surplus": W.COLOR_SURPLUS, "accent": W.COLOR_ACCENT,
                 "neutral": "#888", "deficit": W.COLOR_DEFICIT}.get(r["color"], W.COLOR_ACCENT)
        self.lbl_assist_result.config(text=r["head"], foreground=color)
        if r.get("estimated"):
            self._set_note(self.txt_assist,
                f"⚠️【{city}】无精确数据，以下按城市等级估算，建议用「问 AI」查精确。\n\n" + r["note"])
        else:
            self._set_note(self.txt_assist, r["note"])

    def _open_assistance_prompt(self):
        city = self.var_assist_city.get().strip()
        try:
            income = float(self.var_assist_income.get() or 0)
        except ValueError:
            income = 0
        asset_s = self.var_assist_asset.get().strip()
        asset = float(asset_s) if asset_s else None
        W.open_prompt_dialog(
            self, "问 AI（本地救助）",
            build_fn=lambda c: E.build_assistance_prompt(
                city or self._profile_city or "（请填城市）", income,
                f"{int(self.var_assist_size.get() or 1)} 人家庭", asset=asset,
                profile=self._profile),
            intro="把这段复制给 AI，填你的城市，它会判断你符合哪档、能领多少、怎么申请。")

    # ============================================================
    # 最低工资对照
    # ============================================================
    def _build_min_wage(self, c):
        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=4)
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="最低工资对照", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Label(form,
                  text="《劳动法》第48条：用人单位支付工资不得低于当地最低工资标准。"
                       "低于就是违法——即便试用期、学徒期也不行。",
                  style="Sub.TLabel", wraplength=560, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(form, text="你的月薪（元）：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_mw_wage = tk.StringVar(value="3500")
        ttk.Entry(form, textvariable=self.var_mw_wage, width=14).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="所在城市等级：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_mw_tier = tk.StringVar(value="三线")
        ttk.Combobox(form, textvariable=self.var_mw_tier, values=D.TIER_KEYS,
                     state="readonly", width=12).grid(row=3, column=1, sticky="w")
        ttk.Button(form, text="对照最低工资", command=self.on_minwage_compute).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(12, 2))

        res = W.CardFrame(c, padding=10)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        res.columnconfigure(0, weight=1)
        self.lbl_mw_verdict = ttk.Label(res, text="—", font=W.FONT_BIG, foreground=W.COLOR_ACCENT)
        self.lbl_mw_verdict.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.lbl_mw_detail = ttk.Label(res, text="", font=W.FONT_RESULT, justify="left")
        self.lbl_mw_detail.grid(row=1, column=0, sticky="w")
        ttk.Label(res, text="白话解读与维权", style="Header.TLabel").grid(
            row=2, column=0, sticky="w", pady=(10, 4))
        self.txt_mw = self._make_note(res, height=5, grid=dict(row=3, column=0, sticky="ew"))
        ttk.Button(res, text="生成「问 AI」的提示词", style="AskAI.TButton",
                   command=self._open_minwage_prompt).grid(row=4, column=0, sticky="w", pady=(8, 0))

    def on_minwage_compute(self):
        try:
            wage = float(self.var_mw_wage.get())
        except ValueError:
            self._set_note(self.txt_mw, "请输入有效的月薪数字。")
            return
        tier = self.var_mw_tier.get()
        r = E.compute_min_wage_check(wage, tier)
        if "error" in r:
            self.lbl_mw_verdict.config(text="—", foreground=W.COLOR_DEFICIT)
            self.lbl_mw_detail.config(text="")
            self._set_note(self.txt_mw, r["error"])
            return
        if r["below"]:
            gap = r["min_wage"] - r["monthly_wage"]
            self.lbl_mw_verdict.config(
                text=f"低于当地最低工资 {gap:,.0f} 元，违法！", foreground=W.COLOR_DEFICIT)
        else:
            self.lbl_mw_verdict.config(text="高于最低工资线，合法", foreground=W.COLOR_SURPLUS)
        self.lbl_mw_detail.config(
            text=(f"当地最低工资（{r['tier']}城市）：{r['min_wage']:,.0f} 元/月\n"
                  f"你的月薪：{r['monthly_wage']:,.0f} 元（是最低工资的 {r['ratio']:.1%}）"))
        self._set_note(self.txt_mw, r["note"])
