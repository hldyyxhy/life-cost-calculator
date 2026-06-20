# -*- coding: utf-8 -*-
"""
page_profile.py —— 我的档案

把"我是谁、挣多少、怎么活、养谁、欠多少"集中成一份档案：
    - 按 6 组细致字段渲染表单（控件类型见 profile.FIELD_DEFS）
    - 保存档案：导出为 JSON 文件（可选落盘）
    - 加载档案：从 JSON 文件导入
    - 新建：清空回默认值

本轮档案先独立存在；处境/对比/三座山如何读取后续再接。
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import profile as P
import cost_data as D
import gui_widgets as W
import report as R


class ProfilePage(ttk.Frame):
    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app   # 用于把档案同步到其他模块
        self._vars = {}   # 字段名 -> tk 变量
        self._scroll = W.ScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True)
        self._content = self._scroll.inner
        self._build_toolbar()
        self._build_form()
        self._after_build_city_trigger()  # 给城市输入加自动识别
        self._build_apply_bar()

    # ---------- 顶部操作栏 ----------
    def _build_toolbar(self):
        bar = W.CardFrame(self._content, padding=8)
        bar.pack(side="top", fill="x", padx=8, pady=(8, 4))

        ttk.Label(bar, text="我的档案", style="Header.TLabel").pack(side="left")
        ttk.Label(bar,
                  text="（先独立填写保存；各计算模块后续会读取这份档案）",
                  style="Sub.TLabel").pack(side="left", padx=10)

        btns = ttk.Frame(bar)
        btns.pack(side="right")
        ttk.Button(btns, text="💾 保存档案", command=self.on_save).pack(side="left", padx=3)
        ttk.Button(btns, text="📂 加载档案", command=self.on_load).pack(side="left", padx=3)
        ttk.Button(btns, text="✚ 新建（清空）", command=self.on_reset).pack(side="left", padx=3)

    # ---------- 表单 ----------
    def _build_form(self):
        for group, fields in P.FIELD_DEFS.items():
            box = W.CardFrame(self._content, title=P.GROUP_TITLES[group], padding=10)
            box.pack(side="top", fill="x", padx=8, pady=4)
            box.columnconfigure(1, weight=1)
            for row, (key, default, label, ctype, meta) in enumerate(fields):
                self._render_field(box, row, key, default, label, ctype, meta)

    # ---------- 底部确定栏：同步到其他模块 ----------
    def _build_apply_bar(self):
        bar = W.CardFrame(self._content, padding=10)
        bar.pack(side="top", fill="x", padx=8, pady=(4, 6))
        ttk.Label(bar, text="填完后点「确定」，自动同步到处境页、对比页、三座山，无需重复输入。",
                  style="Sub.TLabel").pack(side="left")
        ttk.Button(bar, text="✓  确定（同步到各模块）",
                   command=self.on_apply).pack(side="right")

        # 保存综合计算结果
        bar2 = W.CardFrame(self._content, padding=10)
        bar2.pack(side="top", fill="x", padx=8, pady=(0, 12))
        ttk.Label(bar2, text="各模块都算完后，可生成一份含档案数据与分析建议的综合报告。",
                  style="Sub.TLabel").pack(side="left")
        ttk.Button(bar2, text="📄  保存个人计算结果",
                   command=self.on_export_report).pack(side="right")

    def on_apply(self, silent=False):
        """把档案推送到处境页、对比页、三座山页、劳动权益页（各页 apply_profile 自取所需字段）。

        silent=True 时不弹窗、同步失败也吞掉——供启动时自动载入使用，避免打扰用户。
        """
        prof = self.collect()
        # 若填了城市但等级是默认值，先自动识别
        if prof.get("city") and D.city_to_tier(prof["city"]):
            P.auto_map_tier(prof)
            # 回填到控件
            self._vars["tier"].set(prof["tier"])

        synced = self._push_to_pages(prof, silent=silent)
        P.save_last_profile(prof)   # 确认档案即存为「上次」，下次启动自动载入

        if synced and not silent:
            msg = (f"档案已同步到：{'、'.join(synced)} 页。\n"
                   f"城市「{prof.get('city', '未填')}」→ {prof.get('tier', '?')}")
            if prof.get("city"):
                msg += "\n\n生成「问AI」提示词时会自动带入城市信息。"
            messagebox.showinfo("已同步", msg)
        return prof

    def _push_to_pages(self, prof, silent=False):
        """把档案同步到处境/对比/三座山/权益页。成功返回已同步标签列表，失败返回 None。"""
        pages = self.app.pages if self.app else {}
        targets = [("处境", "current"), ("对比", "compare"),
                   ("三座山", "milestones"), ("权益", "rights"),
                   ("求助与反诈", "assist"), ("医保就医", "medical")]
        synced = []
        for label, key in targets:
            pg = pages.get(key)
            if pg is not None and hasattr(pg, "apply_profile"):
                try:
                    pg.apply_profile(prof)
                    synced.append(label)
                except Exception as e:
                    if not silent:   # 启动时静默，不打扰
                        messagebox.showerror("同步失败", f"同步到【{label}】时出错：\n{e}")
                    return None      # 失败即停
        return synced

    def on_export_report(self):
        """各模块都算完后，询问并保存一份含档案数据 + 各模块分析 + 综合建议的报告。"""
        from tkinter import messagebox, filedialog
        if not messagebox.askyesno(
                "保存计算结果",
                "是否保存个人计算结果？\n\n报告将包含：基本档案数据 + 各模块分析 + 综合建议。\n"
                "（请先在各模块点过「算一算/开始对比」，否则对应段落会显示「未计算」）"):
            return

        prof = self.collect()
        pages = self.app.pages if self.app else {}
        cur = getattr(pages.get("current"), "_last_result", None)
        cmp = getattr(pages.get("compare"), "_last_compare", None)
        ms_page = pages.get("milestones")
        ms = ms_page.get_report_section() if ms_page and hasattr(ms_page, "get_report_section") else {}

        text = R.build_full_report(prof, cur, cmp, ms)

        path = filedialog.asksaveasfilename(
            title="保存个人计算结果",
            defaultextension=".txt",
            initialfile="个人计算结果.txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("已保存", f"个人计算结果已保存到：\n{path}")
        except OSError as e:
            messagebox.showerror("保存失败", str(e))

    def _render_field(self, box, row, key, default, label, ctype, meta):
        ttk.Label(box, text=f"{label}：").grid(
            row=row, column=0, sticky="w", pady=3)

        if ctype == "spin":
            lo, hi = meta
            var = tk.IntVar(value=default)
            ttk.Spinbox(box, from_=lo, to=hi, textvariable=var,
                        width=8).grid(row=row, column=1, sticky="w")
        elif ctype == "entry":
            if key == "city":
                # 城市字段：宽输入框 + 自动识别按钮
                var = tk.StringVar(value=default)
                entry_w = ttk.Entry(box, textvariable=var, width=16)
                entry_w.grid(row=row, column=1, sticky="w")
                self._city_entry = entry_w  # 保存引用供绑定用
                btn = ttk.Button(box, text="🔍 识别等级",
                                 command=self._on_city_recognize)
                btn.grid(row=row, column=2, sticky="w", padx=(4, 8))
                ttk.Label(box, text=meta, style="Sub.TLabel").grid(
                    row=row, column=3, sticky="w")
            else:
                var = tk.StringVar(value=default)
                ttk.Entry(box, textvariable=var, width=14).grid(
                    row=row, column=1, sticky="w")
                if meta:  # 提示文字
                    ttk.Label(box, text=meta, style="Sub.TLabel").grid(
                        row=row, column=2, sticky="w", padx=8)
        elif ctype == "combo":
            var = tk.StringVar(value=default)
            ttk.Combobox(box, textvariable=var, values=meta,
                         state="readonly", width=16).grid(
                row=row, column=1, sticky="w")
        elif ctype == "check":
            var = tk.BooleanVar(value=default)
            ttk.Checkbutton(box, variable=var).grid(
                row=row, column=1, sticky="w")
        else:
            var = None
        self._vars[key] = var

    # ---------- 城市自动识别 ----------
    def _after_build_city_trigger(self):
        """给城市输入框绑定键盘事件：聚焦离开时自动识别城市等级。"""
        city_var = self._vars.get("city")
        if city_var is None:
            return
        # 绑定 <FocusOut>（输入框失去焦点时触发）
        entry = getattr(self, "_city_entry", None)
        if entry:
            entry.bind("<FocusOut>", lambda e: self._on_city_recognize())
            entry.bind("<Return>", lambda e: self._on_city_recognize())

    def _on_city_recognize(self):
        """根据输入的城市名自动匹配城市等级。未检索到时弹窗提示。"""
        city = self._vars["city"].get().strip()
        if not city:
            return
        tier = D.city_to_tier(city)
        if tier:
            self._vars["tier"].set(tier)
        else:
            # 查不到 → 弹窗提示，但城市名仍保留用于同步到 AI 提示词
            from tkinter import messagebox
            messagebox.showinfo(
                "未检索到对应城市",
                f"未在数据库中检索到「{city}」的等级信息。\n\n"
                "请确认输入的是官方城市名（如「石家庄」而非「石家庄市」），\n"
                "或自行在上方「城市等级」下拉框中手动选择对应等级。\n\n"
                "你填写的城市名仍会同步到各模块和「问AI」提示词中。"
            )

    # ---------- 收集 / 回填 ----------
    def collect(self):
        """从控件收集成档案 dict（entry 的空串保留为 ''，表示未填）"""
        profile = {}
        for key, var in self._vars.items():
            if var is None:
                continue
            if isinstance(var, tk.BooleanVar):
                profile[key] = var.get()
            elif isinstance(var, tk.IntVar):
                try:
                    profile[key] = int(var.get())
                except (tk.TclError, ValueError):
                    profile[key] = 0
            else:  # StringVar
                profile[key] = var.get()
        return P.validate_profile(profile)

    def apply_profile(self, profile):
        """把档案 dict 回填到控件"""
        profile = P.validate_profile(profile)
        # 若填了城市，自动识别城市等级
        if profile.get("city") and D.city_to_tier(profile["city"]):
            P.auto_map_tier(profile)
        for key, var in self._vars.items():
            if var is None or key not in profile:
                continue
            try:
                var.set(profile[key])
            except tk.TclError:
                pass

    # ---------- 操作 ----------
    def on_save(self):
        profile = self.collect()
        path = filedialog.asksaveasfilename(
            title="保存档案",
            defaultextension=".json",
            initialfile="我的档案.json",
            filetypes=[("JSON 档案", "*.json"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            P.save_to_file(profile, path)
            P.save_last_profile(profile)   # 导出的即最近档案，同步为「上次」
            messagebox.showinfo("已保存", f"档案已保存到：\n{path}")
        except OSError as e:
            messagebox.showerror("保存失败", str(e))

    def on_load(self):
        path = filedialog.askopenfilename(
            title="加载档案",
            filetypes=[("JSON 档案", "*.json"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            profile = P.load_from_file(path)
            self.apply_profile(profile)
            messagebox.showinfo("已加载", f"已加载档案：\n{path}")
        except (OSError, ValueError) as e:
            messagebox.showerror("加载失败", f"文件无法解析或不存在：\n{e}")

    def on_reset(self):
        if messagebox.askyesno("确认", "清空所有字段回到默认值？未保存的改动会丢失。"):
            self.apply_profile(P.default_profile())
