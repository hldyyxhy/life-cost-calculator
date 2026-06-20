# -*- coding: utf-8 -*-
"""
page_assist.py —— 求助与反诈（Notebook 双标签，仿借贷页）

把「求助渠道」和「反诈骗」合并成一页，用标签页切换，减少侧边栏项目数：
  · 求助渠道 —— 出事了找谁（按钮墙 + 提示词）
  · 反诈骗   —— 怀疑被骗怎么判断/止损（按钮墙 + 特征速查 + 提示词）
两个标签共用从档案同步来的城市。
"""
import tkinter as tk
from tkinter import ttk

from pages.page_help import HelpPage
from pages.page_anti_fraud import AntiFraudPage


class AssistPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.help_page = HelpPage(nb)
        nb.add(self.help_page, text="求助渠道（出事找谁）")
        self.fraud_page = AntiFraudPage(nb)
        nb.add(self.fraud_page, text="反诈骗（怀疑被骗/止损）")

    def apply_profile(self, prof):
        """城市同步到两个标签。"""
        self.help_page.apply_profile(prof)
        self.fraud_page.apply_profile(prof)
