# -*- coding: utf-8 -*-
"""
page_medical.py —— 医保就医（独立页，Notebook）

① 住院报销估算：参保城市 + 职工/居民 + 费用 + 异地/退休 → 基本医保+大病报销、自付
② 医保速查与慢病：药品目录/门诊慢特病/异地备案/DRG 规则 + 问 AI

数据来自 medical_data.py（31 省职工住院 + 居民 + 大病 + 规则）。
"""
import tkinter as tk
from tkinter import ttk

import calc_engine as E
import rights_data as R
import medical_data as M
import gui_widgets as W

_REMOTE_MAP = {"本地就医": "none", "异地已备案": "filed", "异地未备案": "unfiled"}


class MedicalPage(ttk.Frame):
    def __init__(self, parent, app=None):
        super().__init__(parent)
        self._profile_city = ""
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=8, pady=8)
        self._build_inpatient(self._new_tab("① 住院报销估算"))
        self._build_guide(self._new_tab("② 医保速查与慢病"))
        self._nb.select(0)

    def _new_tab(self, title):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text=title)
        sf = W.ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        return sf.inner

    def apply_profile(self, prof):
        self._profile_city = prof.get("city", "")
        if hasattr(self, "var_med_city") and self._profile_city:
            self.var_med_city.set(self._profile_city)

    def _set_note(self, tw, text):
        tw.config(state="normal")
        tw.delete("1.0", "end")
        tw.insert("1.0", text)
        tw.config(state="disabled")

    # ============================================================
    # ① 住院报销估算
    # ============================================================
    def _build_inpatient(self, c):
        form = W.CardFrame(c, padding=10)
        form.pack(side="top", fill="x", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="住院能报多少？自付多少？",
                  style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(form, text="参保城市：").grid(row=1, column=0, sticky="w", pady=3)
        self.var_med_city = tk.StringVar(value="北京")
        ttk.Combobox(form, textvariable=self.var_med_city, values=R.CITY_NAMES,
                     width=12).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="医保类型：").grid(row=2, column=0, sticky="w", pady=3)
        self.var_med_id = tk.StringVar(value="职工")
        ttk.Combobox(form, textvariable=self.var_med_id, values=["职工", "居民"],
                     state="readonly", width=8).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="住院费用（元）：").grid(row=3, column=0, sticky="w", pady=3)
        self.var_med_cost = tk.StringVar(value="50000")
        ttk.Entry(form, textvariable=self.var_med_cost, width=12).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="就医地：").grid(row=4, column=0, sticky="w", pady=3)
        self.var_med_remote = tk.StringVar(value="本地就医")
        ttk.Combobox(form, textvariable=self.var_med_remote,
                     values=list(_REMOTE_MAP.keys()), state="readonly",
                     width=12).grid(row=4, column=1, sticky="w")
        self.var_med_retired = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="退休人员", variable=self.var_med_retired).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Button(form, text="▶ 估算报销",
                   command=self.on_medical_compute).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(8, 2))

        res = W.CardFrame(c, padding=8)
        res.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        ttk.Label(res, text="结果", style="Header.TLabel").pack(anchor="w", pady=(0, 4))
        self.txt_med = W.readonly_note(res, height=12, bg="#f0f7f0")
        ttk.Button(res, text="生成「问 AI」的提示词（按当地最新医保政策算）",
                   style="AskAI.TButton",
                   command=self._open_medical_prompt).pack(anchor="w", pady=(8, 0))

    def on_medical_compute(self):
        city = self.var_med_city.get().strip()
        try:
            cost = float(self.var_med_cost.get() or 0)
        except ValueError:
            self._set_note(self.txt_med, "住院费用请填数字。")
            return
        identity = self.var_med_id.get()
        remote = _REMOTE_MAP.get(self.var_med_remote.get(), "none")
        retired = self.var_med_retired.get()
        r = E.estimate_medical_cost(city, identity, cost, remote, retired)
        if "error" in r:
            self._set_note(self.txt_med,
                f"⚠️ 数据库未收录「{city}」的医保数据，无法估算。建议用下方「问 AI」查当地医保政策。")
            return
        note = r["note"]
        if r.get("estimated"):
            note = f"⚠️【{city}】无精确数据，以下按城市等级估算，建议用「问 AI」查精确：\n\n" + note
        self._set_note(self.txt_med, note)

    def _open_medical_prompt(self):
        city = self.var_med_city.get().strip()
        try:
            cost = float(self.var_med_cost.get() or 0)
        except ValueError:
            cost = 0
        W.open_prompt_dialog(
            self, "问 AI（医保报销）", with_city=False,
            build_fn=lambda c: E.build_medical_prompt(
                city or self._profile_city or "（请填城市）",
                self.var_med_id.get(), cost, self.var_med_retired.get()),
            intro="把这段复制给 AI，填参保城市，它会按当地医保政策算基本+大病报销、自付，给操作步骤。")

    # ============================================================
    # ② 医保速查与慢病
    # ============================================================
    def _build_guide(self, c):
        # 药品目录
        drug = W.CardFrame(c, title="药品目录（决定能不能报、先自付多少）", padding=10)
        drug.pack(side="top", fill="x", padx=8, pady=(8, 4))
        for name, info in M.DRUG_CATEGORY.items():
            sp = info["自付"]
            sp_txt = f"{sp[0]*100:.0f}~{sp[1]*100:.0f}%" if isinstance(sp, tuple) else f"{sp*100:.0f}%"
            ttk.Label(drug, text=f"● {name}：先自付 {sp_txt}（{info['规则']}）",
                      style="Sub.TLabel", wraplength=600, justify="left").pack(anchor="w", pady=2)
        ttk.Label(drug, text="不报：" + "、".join(M.DRUG_NOT_COVERED),
                  style="Sub.TLabel", wraplength=600, justify="left").pack(anchor="w", pady=(4, 0))

        # 门诊慢特病
        chronic = W.CardFrame(c, title="门诊慢特病（慢性病/特殊病能多报）", padding=10)
        chronic.pack(side="top", fill="x", padx=8, pady=4)
        cd = M.CHRONIC_DISEASE_RATIO
        ratio = cd["门诊慢性病"]["比例"]
        ttk.Label(chronic,
                  text=f"● 门诊慢性病：报销 {ratio[0]*100:.0f}~{ratio[1]*100:.0f}%，"
                       "按病种设年度限额。常见：" + "、".join(cd["门诊慢性病"]["常见病"]),
                  style="Sub.TLabel", wraplength=600, justify="left").pack(anchor="w", pady=2)
        ttk.Label(chronic,
                  text="● 门诊特殊病：" + cd["门诊特殊病"]["比例"] + "。常见："
                       + "、".join(cd["门诊特殊病"]["常见病"]),
                  style="Sub.TLabel", wraplength=600, justify="left").pack(anchor="w", pady=2)
        ttk.Label(chronic,
                  text=f"⚠️ 高血压、糖尿病全国必含——有的话去当地医保局认定门诊慢特病，"
                       f"认定后门诊能多报，别漏。",
                  foreground="#c0392b", style="Sub.TLabel",
                  wraplength=600, justify="left").pack(anchor="w", pady=2)

        # 异地就医
        remote = W.CardFrame(c, title="异地就医（备案能少亏）", padding=10)
        remote.pack(side="top", fill="x", padx=8, pady=4)
        ttk.Label(remote,
                  text=f"● 原则：{M.REMOTE_PRINCIPLE}（能报哪些看就医地目录，报多少看参保地标准）。\n"
                       f"● 已备案/转诊：报销比降 ≤10 个百分点；未备案降 ≤20 个百分点。\n"
                       f"● 临时外出就医可线上自助备案（国家医保服务平台 APP / 异地就医小程序），半年有效。",
                  style="Sub.TLabel", wraplength=600, justify="left").pack(anchor="w")

        # DRG
        drg = W.CardFrame(c, title="DRG/DIP 改革影响", padding=10)
        drg.pack(side="top", fill="x", padx=8, pady=4)
        ttk.Label(drg, text=M.DRG_NOTE, style="Sub.TLabel",
                  wraplength=600, justify="left").pack(anchor="w")

        # 问 AI
        ttk.Button(c, text="生成「问 AI」的提示词（慢病认定 / 异地备案 / 药品查询）",
                   style="AskAI.TButton",
                   command=self._open_guide_prompt).pack(anchor="w", padx=8, pady=(8, 8))

    def _open_guide_prompt(self):
        city = self._profile_city or "（请填城市）"
        prompt = (
            f"请以医保政策专家口吻帮我。我所在城市：{city}。\n"
            "【请帮我】\n"
            "1. 我有高血压/糖尿病，怎么认定门诊慢特病？认定后门诊多报多少？\n"
            "2. 我要去外地看病，怎么线上办异地备案？不办会少报多少？\n"
            "3. 怎么查我用的药在不在医保目录、是甲类还是乙类、要先自付多少？\n"
            "4. 当地医保报销的最新政策（起付线/报销比/封顶线）。"
        )
        W.open_prompt_dialog(
            self, "问 AI（医保速查）", with_city=False,
            build_fn=lambda c: prompt,
            intro="把这段复制给 AI，填你的城市，它帮你查慢病认定、异地备案、药品目录。")
