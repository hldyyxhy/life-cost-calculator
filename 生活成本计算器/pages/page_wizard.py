# -*- coding: utf-8 -*-
"""page_wizard.py —— 首次档案填写向导（分步问答）

把档案页一次性的一大堆字段，拆成几步轻松的问答；填完自动同步到档案页 + 各计算模块。
步骤定义见 profile.WIZARD_STEPS；字段级 show_if 实现"没伴侣就不问伴侣薪资"式的智能跳过。
触发：首次启动（无上次档案）时由 gui_app._maybe_show_wizard 调 open_profile_wizard。
"""
import tkinter as tk
from tkinter import ttk

import profile as P
import cost_data as D

# 控制字段：其值变化会改变同一步里其他字段的显隐，需 trace 重渲染当前步
_CONTROL_KEYS = {"has_partner", "has_car", "has_side_income", "num_children"}


# ---- 字段元信息（从 FIELD_DEFS 反查，避免硬编码）----
def _field_def(key):
    """返回字段定义 (key, default, label, ctype, meta)。"""
    for fields in P.FIELD_DEFS.values():
        for f in fields:
            if f[0] == key:
                return f
    return None


def _ctype(key):
    f = _field_def(key)
    return f[3] if f else "entry"


def _meta(key):
    f = _field_def(key)
    return f[4] if f else None


def _label(key):
    f = _field_def(key)
    return f[2] if f else key


def _default_for(key):
    f = _field_def(key)
    return f[1] if f else ""


def _read(var):
    """安全读取 tk 变量值。"""
    try:
        if isinstance(var, tk.BooleanVar):
            return bool(var.get())
        if isinstance(var, tk.IntVar):
            return int(var.get())
        return var.get()
    except (tk.TclError, ValueError):
        if isinstance(var, tk.BooleanVar):
            return False
        if isinstance(var, tk.IntVar):
            return 0
        return ""


def _city_hint_text(city):
    """返回 (提示文字, 是否识别成功)，用于城市输入框下方的红/绿字提示。"""
    city = (city or "").strip()
    if not city:
        return "", None
    tier = D.city_to_tier(city)
    if tier:
        return f"✓ 已识别：{tier}城市", True
    return (f"未找到「{city}」，请确认是官方城市名（如“石家庄”而非“石家庄市”）",
            False)


def open_profile_wizard(root, app):
    """打开首次填写向导。填完 → 回填档案页 + 同步各模块 + 存为上次档案。"""
    win = tk.Toplevel(root)
    win.title("首次填写 · 几道题帮你快速建档")
    win.transient(root)
    w, h = 560, 440
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
    win.grab_set()

    # 城市识别提示样式（红=未找到 / 绿=已识别）
    _style = ttk.Style(win)
    _style.configure("CityErr.TLabel", foreground="#c0392b", font=("Microsoft YaHei", 9))
    _style.configure("CityOK.TLabel", foreground="#1a7d3a", font=("Microsoft YaHei", 9))

    answers = {}            # key -> tk 变量（跨步复用，保留已答值）
    state = {"idx": 0}
    steps = P.WIZARD_STEPS
    total = len(steps)

    # ---- 顶部：标题 + 进度 ----
    header = ttk.Frame(win, padding=(18, 16, 18, 2))
    header.pack(fill="x")
    title_lbl = ttk.Label(header, text="", style="Header.TLabel")
    title_lbl.pack(anchor="w")
    progress_lbl = ttk.Label(header, text="", style="Sub.TLabel")
    progress_lbl.pack(anchor="w", pady=(2, 0))

    # ---- 内容区（每步重建）----
    body_wrap = ttk.Frame(win, padding=(18, 6, 18, 6))
    body_wrap.pack(fill="both", expand=True)
    body = ttk.Frame(body_wrap)
    body.pack(fill="both", expand=True)

    # ---- 底部：按钮 ----
    bot = ttk.Frame(win, padding=(18, 4, 18, 16))
    bot.pack(fill="x")
    ttk.Button(bot, text="以后再说",
               command=lambda: _skip(win)).pack(side="left")
    nav = ttk.Frame(bot)
    nav.pack(side="right")
    prev_btn = ttk.Button(nav, text="‹ 上一步", command=lambda: _go(-1))
    prev_btn.pack(side="left", padx=(0, 6))
    next_btn = ttk.Button(nav, text="下一步 ›", command=lambda: _go(1))
    next_btn.pack(side="left")

    def _var_for(key):
        """取/建该字段的 tk 变量；控制字段与 city 加 trace。"""
        if key not in answers:
            ctype = _ctype(key)
            default = _default_for(key)
            if ctype == "spin":
                try:
                    val = int(default) if default != "" else 0
                except (TypeError, ValueError):
                    val = 0
                v = tk.IntVar(master=win, value=val)
            elif ctype == "check":
                v = tk.BooleanVar(master=win, value=bool(default))
            else:
                v = tk.StringVar(master=win, value=str(default) if default != "" else "")
            answers[key] = v
            if key in _CONTROL_KEYS:
                v.trace_add("write", lambda *_: render())   # 值变 → 重渲染当前步（更新依赖字段显隐）
            if key == "city":
                v.trace_add("write", lambda *_: _recognize_city())
        return answers[key]

    def _update_city_hint():
        """更新城市识别提示（红字未找到 / 绿字已识别）。"""
        lbl = state.get("city_hint_lbl")
        if lbl is None:
            return
        c = answers.get("city")
        city = c.get().strip() if c else ""
        text, ok = _city_hint_text(city)
        lbl.config(text=text, style="CityOK.TLabel" if ok else "CityErr.TLabel")
        if ok:
            _var_for("tier").set(D.city_to_tier(city))

    def _recognize_city():
        _update_city_hint()

    def render():
        for child in body.winfo_children():
            child.destroy()
        step = steps[state["idx"]]
        title_lbl.config(text=step["title"])
        progress_lbl.config(text=f"第 {state['idx'] + 1} / {total} 步")

        snap = {k: _read(v) for k, v in answers.items()}   # 当前已答快照，供 show_if 判断
        row = 0
        for f in step["fields"]:
            key = f["key"]
            show_if = f.get("show_if")
            if show_if and not show_if(snap):
                continue   # 智能跳过：不显示该字段
            ctype = _ctype(key)
            label = _label(key)
            var = _var_for(key)
            if ctype == "check":
                ttk.Checkbutton(body, text=label, variable=var).grid(
                    row=row, column=0, columnspan=2, sticky="w", pady=6)
            else:
                ttk.Label(body, text=f"{label}：").grid(
                    row=row, column=0, sticky="w", pady=6, padx=(0, 8))
                if ctype == "spin":
                    lo, hi = _meta(key) or (0, 99)
                    ttk.Spinbox(body, from_=lo, to=hi, textvariable=var,
                                width=10).grid(row=row, column=1, sticky="w")
                elif ctype == "combo":
                    ttk.Combobox(body, textvariable=var, values=_meta(key) or [],
                                 state="readonly", width=16).grid(row=row, column=1, sticky="w")
                else:  # entry
                    ttk.Entry(body, textvariable=var, width=22).grid(row=row, column=1, sticky="w")
                    hint = _meta(key)
                    if hint:   # 提示文字放下一行，避免窄窗口下被挤掉
                        ttk.Label(body, text=hint, style="Sub.TLabel").grid(
                            row=row + 1, column=1, columnspan=2, sticky="w", pady=(0, 4))
                        row += 1
                    if key == "city":   # 城市识别红/绿字提示
                        city_lbl = ttk.Label(body, text="", style="CityErr.TLabel")
                        city_lbl.grid(row=row + 1, column=1, columnspan=2, sticky="w", pady=(0, 4))
                        state["city_hint_lbl"] = city_lbl
                        _update_city_hint()
                        row += 1
            row += 1
        body.columnconfigure(1, weight=1)

        prev_btn.state(["!disabled"] if state["idx"] > 0 else ["disabled"])
        is_last = state["idx"] == total - 1
        next_btn.config(text="完成建档 ✓" if is_last else "下一步 ›")

    def _go(delta):
        new_idx = state["idx"] + delta
        if new_idx >= total:
            _finish()
        elif new_idx >= 0:
            state["idx"] = new_idx
            render()

    def _finish():
        snap = {k: _read(v) for k, v in answers.items()}
        prof = P.validate_profile(snap)
        if prof.get("city") and D.city_to_tier(prof["city"]):
            P.auto_map_tier(prof)
        pg = app.pages.get("profile") if app else None
        if pg is not None:
            pg.apply_profile(prof)
            pg.on_apply(silent=True)   # 回填档案页 + 同步处境/对比/三座山/权益 + 存 last
        _close(win)

    def _skip(_win):
        try:
            P.save_last_profile(P.default_profile())   # 存默认档案，下次不再弹
        except Exception:
            pass
        _close(_win)

    def _close(_win):
        try:
            _win.grab_release()
        except Exception:
            pass
        _win.destroy()

    win.protocol("WM_DELETE_WINDOW", lambda: _skip(win))
    render()
    return win
