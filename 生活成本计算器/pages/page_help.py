# -*- coding: utf-8 -*-
"""
page_help.py —— 求助渠道（按钮墙）

把"出事找谁"做成一排场景按钮：点最贴近你情况的那个，弹窗生成一段提示词，
复制去问任意 AI，它会告诉你该找哪个部门、打什么电话、具体怎么操作。
（纯静态的号码清单不如让 AI 结合具体情况指路，所以改成按钮 + 提示词。）
"""
import tkinter as tk
from tkinter import ttk

import calc_engine as E
import gui_widgets as W


class HelpPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._profile_city = ""  # 从档案同步的城市名
        sf = W.ScrollableFrame(self)
        sf.pack(fill="both", expand=True)
        c = sf.inner

        # 顶部说明
        ttk.Label(c, text="遇到事了？点最贴近你情况的按钮", style="Header.TLabel").pack(
            anchor="w", padx=8, pady=(8, 4))
        ttk.Label(c,
                  text="每个按钮会生成一段提示词，复制去问任意 AI（豆包 / Kimi / DeepSeek 等），"
                       "它会结合你的城市和具体情况，告诉你该找谁、打什么电话、分步骤怎么操作。",
                  style="Sub.TLabel", wraplength=620, justify="left").pack(
            anchor="w", padx=8, pady=(0, 10))

        # 场景按钮墙（2 列）
        grid = ttk.Frame(c)
        grid.pack(fill="x", padx=8, pady=4)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        for i, (key, info) in enumerate(E.HELP_SCENARIOS.items()):
            r, col = divmod(i, 2)
            ttk.Button(grid, text=info["title"], style="AskAI.TButton",
                       command=self._make_cmd(key, info["title"])).grid(
                row=r, column=col, sticky="ew", padx=5, pady=5)

        # 兜底提示
        ttk.Label(c,
                  text="找不到对应的？记住：12345 是万能转接，不知道找谁就先打它。"
                       "人身边安全受威胁直接 110，急救打 120。",
                  style="Sub.TLabel", wraplength=620, justify="left").pack(
            anchor="w", padx=8, pady=(12, 8))

    # ---------- 档案载入（从档案页「确定」同步接收）----------
    def apply_profile(self, prof):
        """把档案中的城市信息存下来，供「问 AI」提示词使用。"""
        self._profile_city = prof.get("city", "")

    def _make_cmd(self, key, title):
        """生成按钮回调：点击打开该场景的提示词弹窗。"""
        def cmd():
            W.open_prompt_dialog(
                self, f"问 AI（{title}）", with_city=True,
                initial_city=self._profile_city,
                build_fn=lambda city: E.build_help_prompt(key, city),
                intro="把下面这段复制到任意 AI，它会先问你必要细节，再结合你的城市告诉你"
                      "该找谁、怎么操作。")
        return cmd
