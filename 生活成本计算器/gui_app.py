# -*- coding: utf-8 -*-
"""
gui_app.py —— 主窗口：左侧导航 + 右侧内容区 + 页面切换

架构：
    主窗口
    ├── 顶部 Header（标题 + 副标题）
    ├── 主体（左导航栏 + 右内容区 PanedWindow）
    └── 底部状态栏（声明数据为估算）

右侧内容区放三个子页面，用 grid 叠在同一格 + tkraise() 切换。
"""

import tkinter as tk
from tkinter import ttk

import gui_widgets as W
from pages.page_profile import ProfilePage
from pages.page_current import CurrentSituationPage
from pages.page_compare import ComparePage
from pages.page_milestones import MilestonesPage
from pages.page_about import AboutPage


class App:
    def __init__(self, root):
        self.root = root
        root.title("生活成本计算器 —— 钱花到哪去了")
        # 初始尺寸适配屏幕分辨率，避免在低分辨率笔记本上超出屏幕
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w = min(1180, int(sw * 0.92))
        h = min(800, int(sh * 0.90))
        root.geometry(f"{w}x{h}")
        # 最小尺寸配合滚动：小窗口下内容可上下滚动查看
        root.minsize(860, 540)

        # 全局样式
        W.apply_style(root)

        # 顶部 Header
        header = ttk.Frame(root, padding=(16, 12, 16, 4))
        header.pack(fill="x")
        ttk.Label(header, text="生活成本计算器", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="  帮助劳动者看清生活成本、明确努力方向",
                  style="Sub.TLabel").pack(side="left", padx=8)

        # 主体：左导航 + 右内容
        body = ttk.Frame(root)
        body.pack(fill="both", expand=True, padx=12, pady=6)

        # 左导航栏
        nav = ttk.Frame(body, width=190, padding=8)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)

        self.nav_buttons = []
        self.pages = {}
        page_specs = [
            ("① 我的档案\n（填写个人情况）", "profile"),
            ("② 我现在的处境\n（输入月薪算结余）", "current"),
            ("③ 城市加减法\n（换城市值不值）", "compare"),
            ("④ 人生三座山\n（结婚/养娃/养老）", "milestones"),
            ("⑤ 关于与数据说明", "about"),
        ]
        for text, key in page_specs:
            btn = ttk.Button(nav, text=text, style="Nav.TButton",
                             command=lambda k=key: self.show_page(k))
            btn.pack(fill="x", pady=6)
            self.nav_buttons.append((key, btn))

        # 分隔
        ttk.Separator(nav, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(nav, text="数据为公开来源\n估算，仅供参考",
                  style="Sub.TLabel", justify="left").pack(anchor="w")

        # 右内容区
        self.content = ttk.Frame(body)
        self.content.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        # 创建五个页面，叠在同一格
        self.pages["profile"] = ProfilePage(self.content, app=self)
        self.pages["current"] = CurrentSituationPage(self.content, app=self)
        self.pages["compare"] = ComparePage(self.content)
        self.pages["milestones"] = MilestonesPage(self.content)
        self.pages["about"] = AboutPage(self.content)
        for p in self.pages.values():
            p.grid(row=0, column=0, sticky="nsew")

        # 默认显示档案页（入口）
        self.show_page("profile")

        # 底部状态栏
        status = ttk.Frame(root, relief="sunken", padding=(12, 4))
        status.pack(fill="x", side="bottom")
        ttk.Label(status,
                  text="本工具数据来自 2023-2026 年公开调研报告，均为估算中值，仅用于了解大概量级，不作为理财依据。",
                  style="Sub.TLabel").pack(side="left")

    def show_page(self, key):
        for k, btn in self.nav_buttons:
            btn.state(["!pressed"] if k != key else ["pressed"])
        self.pages[key].tkraise()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
