# -*- coding: utf-8 -*-
"""
page_anti_fraud.py —— 反诈骗（按钮墙）

把"我怀疑被骗了"做成一排按骗局类型的按钮：点最像的那种，弹窗生成提示词，
把对方的话术/链接贴进去复制给任意 AI，它会判断是不是骗局、怎么紧急止损、去哪报警。
另附「特征速查」（不依赖 AI 也能快速识别）+ 兜底：96110 / 110 / 国家反诈中心 APP / 12321。
"""
import tkinter as tk
from tkinter import ttk

import calc_engine as E
import gui_widgets as W


class AntiFraudPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._profile_city = ""
        sf = W.ScrollableFrame(self)
        sf.pack(fill="both", expand=True)
        c = sf.inner

        # 顶部说明
        ttk.Label(c, text="怀疑被骗？点最像的那种", style="Header.TLabel").pack(
            anchor="w", padx=8, pady=(8, 4))
        ttk.Label(c,
                  text="点按钮 → 把对方的话术/链接贴进提示词 → 复制去问任意 AI，"
                       "它会判断是不是骗局、立刻怎么止损、去哪报警。拿不准就点「其他」。",
                  style="Sub.TLabel", wraplength=620, justify="left").pack(
            anchor="w", padx=8, pady=(0, 10))

        # 按钮墙（2 列）
        grid = ttk.Frame(c)
        grid.pack(fill="x", padx=8, pady=4)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        for i, (key, info) in enumerate(E.FRAUD_TYPES.items()):
            r, col = divmod(i, 2)
            ttk.Button(grid, text=info["title"], style="AskAI.TButton",
                       command=self._make_cmd(key, info["title"])).grid(
                row=r, column=col, sticky="ew", padx=5, pady=5)

        # 特征速查（不问 AI 也能快速识别）
        cheat = W.CardFrame(c, title="常见骗局特征速查（先看这个）", padding=10)
        cheat.pack(fill="x", padx=8, pady=(10, 4))
        for info in E.FRAUD_TYPES.values():
            ttk.Label(cheat, text=f"● {info['title']}", style="Sub.TLabel",
                      foreground="#c0392b").pack(anchor="w", pady=(4, 0))
            ttk.Label(cheat, text=info["features"], style="Sub.TLabel",
                      wraplength=600, justify="left").pack(anchor="w", padx=(14, 0))

        # 兜底提示
        ttk.Label(c,
                  text="⚠️ 钱还没转：立刻停止一切操作——别转账、别给验证码、别开屏幕共享、别按对方说的做。\n"
                       "已经转账 / 给了验证码：马上打 96110（全国反诈专线）或 110 报警，同时联系银行冻结账户。\n"
                       "举报骚扰电话短信：12321。核实与举报装「国家反诈中心」APP。",
                  style="Sub.TLabel", wraplength=620, justify="left").pack(
            anchor="w", padx=8, pady=(12, 8))

    # ---------- 档案载入（从档案页「确定」同步接收城市）----------
    def apply_profile(self, prof):
        self._profile_city = prof.get("city", "")

    def _make_cmd(self, key, title):
        """生成按钮回调：点击打开该骗局类型的提示词弹窗。"""
        def cmd():
            W.open_prompt_dialog(
                self, f"问 AI（{title}）", with_city=True,
                initial_city=self._profile_city,
                build_fn=lambda city: E.build_antifraud_prompt(key, city),
                intro="把对方的话术/链接贴到提示词里，复制去问任意 AI，"
                      "它会判断是不是骗局、怎么紧急止损。")
        return cmd
