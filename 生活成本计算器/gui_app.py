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
from tkinter import ttk, messagebox

import gui_widgets as W
import tracking as TR
import profile as P
from pages.page_profile import ProfilePage
from pages.page_current import CurrentSituationPage
from pages.page_compare import ComparePage
from pages.page_milestones import MilestonesPage
from pages.page_about import AboutPage
from pages.page_debt import DebtPage
from pages.page_rights import RightsPage
from pages.page_assist import AssistPage
from pages.page_medical import MedicalPage
from pages.page_tracking import TrackingPage
from pages.page_wizard import open_profile_wizard


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

        # 左导航栏（项目较多，内容超高时可垂直滚动，避免矮窗口下底部按钮被截断）
        nav = W.ScrollableFrame(body, bg="#e8e8e8")
        nav.pack(side="left", fill="y")
        nav.configure(width=200)
        nav.pack_propagate(False)
        c = nav.inner

        self.nav_buttons = []
        self.pages = {}
        page_specs = [
            ("① 我的档案\n（填写个人情况）", "profile"),
            ("② 我现在的处境\n（输入月薪算结余）", "current"),
            ("③ 城市与住房\n（换城市/买房决策）", "compare"),
            ("④ 人生三座山\n（结婚/养娃/养老）", "milestones"),
            ("⑤ 借贷真相\n（反算真实年化）", "debt"),
            ("⑥ 劳动权益\n（加班费/失业金/工伤等）", "rights"),
            ("⑦ 求助与反诈\n（出事找谁/防骗）", "assist"),
            ("⑧ 医保就医\n（住院报销/慢病）", "medical"),
            ("⑨ 长期跟踪\n（趋势变化）", "tracking"),
            ("⑩ 关于与数据说明", "about"),
        ]
        for text, key in page_specs:
            btn = ttk.Button(c, text=text, style="Nav.TButton",
                             command=lambda k=key: self.show_page(k))
            btn.pack(fill="x", pady=6)
            self.nav_buttons.append((key, btn))

        # 分隔
        ttk.Separator(c, orient="horizontal").pack(fill="x", pady=8)
        ttk.Label(c, text="数据为公开来源估算\n仅供参考",
                  style="Sub.TLabel", justify="left").pack(anchor="w", pady=(0, 8))

        # 右内容区
        self.content = ttk.Frame(body)
        self.content.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        # 创建八个页面，叠在同一格
        self.pages["profile"] = ProfilePage(self.content, app=self)
        self.pages["current"] = CurrentSituationPage(self.content, app=self)
        self.pages["compare"] = ComparePage(self.content)
        self.pages["milestones"] = MilestonesPage(self.content)
        self.pages["about"] = AboutPage(self.content)
        self.pages["debt"] = DebtPage(self.content)
        self.pages["rights"] = RightsPage(self.content)
        self.pages["assist"] = AssistPage(self.content)
        self.pages["medical"] = MedicalPage(self.content, app=self)
        self.pages["tracking"] = TrackingPage(self.content, app=self)
        for p in self.pages.values():
            p.grid(row=0, column=0, sticky="nsew")

        # 默认显示档案页（入口）
        self.show_page("profile")

        # 启动时自动载入上次档案 + 债务页输入（静默，不弹窗）
        self._auto_restore()

        # 首次启动（无上次档案）弹分步填写向导；延后到主窗口显示后再弹
        self.root.after(120, self._maybe_show_wizard)

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

    def _auto_restore(self):
        """启动时载入上次档案 + 债务页输入，档案自动同步到各页（静默，不弹窗）。"""
        prof = P.load_last_profile()
        if prof:
            pg = self.pages.get("profile")
            if pg is not None:
                pg.apply_profile(prof)        # 回填档案控件
                pg.on_apply(silent=True)       # 同步到处境/对比/三座山/权益 + 存 last
        debt = self.pages.get("debt")
        if debt is not None and hasattr(debt, "load_state"):
            debt.load_state()

    def _on_close(self, root):
        """关闭窗口前兜底保存档案 + 债务页输入，弹窗问是否存跟踪快照，再销毁。"""
        prof = None
        try:
            pg = self.pages.get("profile")
            if pg is not None:
                prof = pg.collect()
                P.save_last_profile(prof)
            debt = self.pages.get("debt")
            if debt is not None and hasattr(debt, "save_state"):
                debt.save_state()
        except Exception:
            pass
        self._ask_save_snapshot(prof)   # 模态弹窗，操作完才继续
        root.destroy()

    def _ask_save_snapshot(self, prof):
        """模态弹窗：是否把本次存为长期跟踪快照（可填姓名，同名累积）。"""
        win = tk.Toplevel(self.root)
        win.title("保存跟踪快照？")
        w, h = 440, 240
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        win.transient(self.root)
        win.grab_set()

        top = ttk.Frame(win, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="是否把本次情况存为长期跟踪快照？",
                  font=W.FONT_BOLD).pack(anchor="w")
        ttk.Label(top, text="存了能在「⑨ 长期跟踪」页看结余、存款等的变化趋势。",
                  style="Sub.TLabel", wraplength=400, justify="left").pack(anchor="w", pady=(4, 8))

        row = ttk.Frame(win, padding=12)
        row.pack(fill="x")
        ttk.Label(row, text="档案姓名：").pack(side="left")
        var_name = tk.StringVar(value=(prof or {}).get("name", ""))
        ttk.Entry(row, textvariable=var_name, width=18).pack(side="left", padx=6)
        ttk.Label(row, text="（同名会累积到同一档案）", style="Sub.TLabel").pack(side="left")

        bot = ttk.Frame(win, padding=12)
        bot.pack(fill="x", side="bottom")

        def do_save():
            name = var_name.get().strip()
            if prof is not None:
                try:
                    last = getattr(self.pages.get("current"), "_last_result", None)
                    TR.save_snapshot(name, prof, TR.metrics_from(prof, last))
                    messagebox.showinfo(
                        "已保存",
                        "跟踪快照已存到 data/tracking/ 目录。\n下次在「⑨ 长期跟踪」页查看。",
                        parent=win)
                except Exception as e:
                    messagebox.showwarning("保存失败", str(e), parent=win)
            win.destroy()

        ttk.Button(bot, text="保存并关闭", style="AskAI.TButton",
                   command=do_save).pack(side="left")
        ttk.Button(bot, text="直接关闭（不存）",
                   command=win.destroy).pack(side="left", padx=6)

        self.root.wait_window(win)

    # ---------- 首次填写向导 ----------
    def _maybe_show_wizard(self):
        """首次启动（无上次档案）弹分步填写向导；老用户有档案则跳过。"""
        try:
            if P.load_last_profile() is None:
                open_profile_wizard(self.root, self)
        except Exception:
            # 向导出错也别反复弹：存一份默认档案占位
            try:
                P.save_last_profile(P.default_profile())
            except Exception:
                pass


def main():
    root = tk.Tk()
    app = App(root)
    # 点窗口「×」关闭时，先保存再销毁（此时控件/变量仍在，可读取）
    root.protocol("WM_DELETE_WINDOW", lambda: app._on_close(root))
    root.mainloop()


if __name__ == "__main__":
    main()
