# -*- coding: utf-8 -*-
"""
gui_widgets.py —— 可复用 GUI 组件与统一样式

抽取两个计算器页面都要用的模式，避免重复代码：
    apply_style(root)          全局统一样式（字体、主题、配色）
    make_radio_group(...)      生成 LabelFrame + 横排 Radiobutton 组
    CardFrame(...)             统一"卡片/区块"容器
    ResultTreeview(...)        统一样式的明细表格（小计/总计/缺口行配色 + 滚动条）
    ProportionBars(...)        自绘横向比例条（Canvas，零依赖）
    BigNumberLabel(...)        大字号数字（结余绿/缺口红）
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
import webbrowser


def export_text(default_name, content):
    """
    弹出保存对话框，把 content 写入用户选择的 txt 文件。
    成功返回文件路径，取消返回 None。
    """
    path = filedialog.asksaveasfilename(
        title="保存结果",
        defaultextension=".txt",
        initialfile=default_name,
        filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
    if not path:
        return None
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("已保存", f"结果已保存到：\n{path}")
        return path
    except OSError as e:
        messagebox.showerror("保存失败", str(e))
        return None

# 统一字体（Windows 中文渲染最清晰）
FONT_FAMILY = "Microsoft YaHei"
FONT = (FONT_FAMILY, 11)
FONT_BOLD = (FONT_FAMILY, 11, "bold")
FONT_SMALL = (FONT_FAMILY, 10)
FONT_HEADER = (FONT_FAMILY, 16, "bold")
FONT_BIG = (FONT_FAMILY, 22, "bold")
FONT_RESULT = (FONT_FAMILY, 13, "bold")

# 语义色
COLOR_SURPLUS = "#1a7d3a"   # 结余 绿
COLOR_DEFICIT = "#c0392b"   # 缺口 红
COLOR_SUBTOTAL = "#eef3fb"  # 小计行 浅蓝灰
COLOR_TOTAL = "#fff4d6"     # 总计行 浅黄
COLOR_ACCENT = "#2c5fa8"    # 主色 蓝


def apply_style(root):
    """应用全局统一样式"""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("TLabel", font=FONT)
    style.configure("TButton", font=FONT, padding=6)
    style.configure("Header.TLabel", font=FONT_HEADER, foreground=COLOR_ACCENT)
    style.configure("Sub.TLabel", font=(FONT_FAMILY, 9), foreground="#666")
    style.configure("Big.TLabel", font=FONT_BIG)
    style.configure("Result.TLabel", font=FONT_RESULT)
    style.configure("TLabelframe.Label", font=FONT_BOLD, foreground=COLOR_ACCENT)
    style.configure("TRadiobutton", font=FONT)
    style.configure("TCheckbutton", font=FONT)
    style.configure("Treeview", font=FONT_SMALL, rowheight=26)
    style.configure("Treeview.Heading", font=(FONT_FAMILY, 10, "bold"))
    # 导航按钮样式
    style.configure("Nav.TButton", font=(FONT_FAMILY, 12, "bold"), padding=12)
    # 标签页（Notebook）样式：学习侧边栏——选中态更深（深铁灰底白字），未选中浅铁灰底深字
    style.configure("TNotebook", tabmargins=(6, 6, 2, 0))
    style.configure("TNotebook.Tab", font=(FONT_FAMILY, 11, "bold"),
                    padding=(14, 8), foreground="#555")
    style.map("TNotebook.Tab",
              background=[("selected", "#5a616b"), ("!selected", "#d4d8de")],
              foreground=[("selected", "#ffffff"), ("!selected", "#555")],
              expand=[("selected", (1, 1, 1, 0))])
    # 「问 AI」提示词按钮：醒目（主色蓝底白字加粗），鼓励使用
    style.configure("AskAI.TButton", font=(FONT_FAMILY, 11, "bold"),
                    foreground="#ffffff", background=COLOR_ACCENT, padding=(14, 8))
    style.map("AskAI.TButton",
              background=[("active", "#1f4a8a"), ("pressed", "#163a6e")],
              foreground=[("active", "#ffffff")])

    # —— Checkbutton 指示符：复用 Radiobutton 的圆点（clam 原生）——
    # 与单选项统一、选中填实心点，避免默认对勾在部分 Windows 渲染下被误看成「叉」。
    # 自绘的「蓝底白勾」方块方案留作备用，见 备用_Checkbutton对勾风格/。
    try:
        def _use_radio_indicator(nodes):
            out = []
            for name, opts in nodes:
                if name == "Checkbutton.indicator":
                    name = "Radiobutton.indicator"
                opts = dict(opts)
                if "children" in opts:
                    opts["children"] = _use_radio_indicator(opts["children"])
                out.append((name, opts))
            return out

        style.layout("TCheckbutton",
                    _use_radio_indicator(style.layout("TCheckbutton")))
    except Exception:
        pass   # 失败则退回 clam 默认外观，不影响功能


# 「复制并打开」支持的 AI 平台（默认 DeepSeek）；可按需增删
AI_PLATFORMS = {
    "DeepSeek": "https://chat.deepseek.com",
    "豆包": "https://www.doubao.com/chat",
    "Kimi": "https://kimi.moonshot.cn",
}
DEFAULT_AI = "DeepSeek"


def open_prompt_dialog(parent, title, build_fn, with_city=False, intro="",
                       city_label="城市（可选，让 AI 结合本地规定）：",
                       initial_city=""):
    """打开「问 AI 提示词」弹窗（各功能复用，主界面只留一个小按钮即可）。

    parent:   父控件（用于剪贴板与 transient）
    title:    弹窗标题
    build_fn: callable(city_str) -> 提示词文本；每次「重新生成」都调用它实时读界面数据
    with_city: 是否显示城市输入框（让 AI 结合本地规定）
    intro:    顶部说明文字（可选）
    initial_city: 城市输入框的初始值（从档案同步时自动填入）
    """
    win = tk.Toplevel(parent)
    win.title(title)
    w, h = 660, 580
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
    win.transient(parent)

    top = ttk.Frame(win, padding=8)
    top.pack(fill="x")
    if intro:
        ttk.Label(top, text=intro, style="Sub.TLabel",
                  wraplength=600, justify="left").pack(fill="x", pady=(0, 6))
    city_var = tk.StringVar(value=initial_city)
    row = None
    if with_city:
        row = ttk.Frame(top)
        row.pack(fill="x")
        ttk.Label(row, text=city_label).pack(side="left")
        ttk.Entry(row, textvariable=city_var, width=14).pack(side="left", padx=6)

    # 提示词文本（可滚动）
    txt_frame = ttk.Frame(win)
    txt_frame.pack(fill="both", expand=True, padx=8, pady=4)
    txt_frame.columnconfigure(0, weight=1)
    txt_frame.rowconfigure(0, weight=1)
    txt = tk.Text(txt_frame, wrap="word", font=(FONT_FAMILY, 10),
                  relief="solid", borderwidth=1, padx=8, pady=6)
    txt.grid(row=0, column=0, sticky="nsew")
    _sb = ttk.Scrollbar(txt_frame, orient="vertical", command=txt.yview)
    txt.configure(yscrollcommand=_sb.set)
    _sb.grid(row=0, column=1, sticky="ns")

    bot = ttk.Frame(win, padding=8)
    bot.pack(fill="x")

    def regen():
        try:
            text = build_fn(city_var.get().strip())
        except Exception as e:
            text = f"生成提示词时出错。请回到对应页面，检查输入框是否都填了有效数字，再点「重新生成」。"
        txt.delete("1.0", "end")
        txt.insert("1.0", text)
        hint.config(text="")

    def do_copy():
        parent.clipboard_clear()
        parent.clipboard_append(txt.get("1.0", "end-1c"))
        hint.config(text="已复制！去 AI 对话框粘贴即可（Ctrl+V）")

    try:
        txt.insert("1.0", build_fn(city_var.get().strip()))
    except Exception as e:  # 读界面数据出错时给出友好提示，不崩
        txt.insert("1.0", f"生成提示词时出错。请回到对应页面，检查输入框是否都填了有效数字，再点「重新生成」。")

    # 操作行：一键复制 / 选 AI 平台后「复制并打开」其网页（默认 DeepSeek）
    action_row = ttk.Frame(top)
    action_row.pack(fill="x", pady=(6, 0))
    ttk.Button(action_row, text="一键复制到剪贴板", style="AskAI.TButton",
               command=do_copy).pack(side="left")

    ai_var = tk.StringVar(value=DEFAULT_AI)

    def do_copy_and_open():
        do_copy()   # 先把提示词放进剪贴板
        url = AI_PLATFORMS.get(ai_var.get(), AI_PLATFORMS[DEFAULT_AI])
        try:
            webbrowser.open(url)
            hint.config(text=f"已复制，并打开「{ai_var.get()}」网页，粘贴（Ctrl+V）即可提问")
        except Exception:
            hint.config(text=f"已复制。打不开网页时手动访问：{url}")

    open_box = ttk.Frame(action_row)
    open_box.pack(side="left", padx=(12, 0))
    ttk.Combobox(open_box, textvariable=ai_var, values=list(AI_PLATFORMS),
                 state="readonly", width=9).pack(side="left")
    ttk.Button(open_box, text="复制并打开", style="AskAI.TButton",
               command=do_copy_and_open).pack(side="left", padx=4)

    hint = ttk.Label(action_row, text="", style="Sub.TLabel")
    hint.pack(side="left", padx=8)
    if row is not None:
        ttk.Button(row, text="重新生成", command=regen).pack(side="left", padx=6)
    ttk.Button(bot, text="关闭", command=win.destroy).pack(side="right")


def readonly_note(parent, height=6, grid=None, bg="#f7f9fc"):
    """带垂直滚动条的只读解读框（现为富文本 RichNote，支持 set_smart_text 智能着色）。
    各页复用，消除 _make_note 重复。grid 为 dict 时用 grid，否则 pack(fill="x")。"""
    return RichNote(parent, height=height, bg=bg, grid=grid)


class RichNote(ttk.Frame):
    """带语义样式的只读结果框（Text + 滚动条），渲染富文本段落。

    住房等页用它替代纯文本 readonly_note：把"月供 / 利息 / 租金 / 差额 / 警示"
    等关键数字用颜色、字号、加粗区分层次（买橙 / 租蓝 / 结论大号绿红 / 警示红小字），
    而不是整段同字体同颜色。

    用法：
        rn = RichNote(parent, height=12); rn.pack(...)
        rn.set_rich([{"t": "买房成本\\n", "tag": "h"},
                     {"t": "月供 3,969\\n", "tag": "buy"}, ...])
        rn.set_text("纯文本回落")   # 输入错误等用普通文本
    """

    # tag → (字体, 前景色)；复用全局语义色常量，保持与 BigNumberLabel 等一致
    _STYLES = {
        "h":      dict(font=(FONT_FAMILY, 12, "bold"), foreground=COLOR_ACCENT),   # 块小标题 蓝
        "buy":    dict(font=(FONT_FAMILY, 12, "bold"), foreground="#d97706"),      # 买房块关键金额 橙
        "rent":   dict(font=(FONT_FAMILY, 12, "bold"), foreground="#2563eb"),      # 租房块关键金额 蓝
        "big":    dict(font=(FONT_FAMILY, 16, "bold"), foreground=COLOR_SURPLUS),  # 结论-利好 大号绿
        "bigbad": dict(font=(FONT_FAMILY, 16, "bold"), foreground=COLOR_DEFICIT),  # 结论-不利 大号红
        "warn":   dict(font=(FONT_FAMILY, 10), foreground=COLOR_DEFICIT),          # 警示 红小字
        "emph":   dict(font=(FONT_FAMILY, 13, "bold"), foreground="#222222"),     # 中性强调（结论行）
        "muted":  dict(font=(FONT_FAMILY, 10), foreground="#888888"),             # 次要说明 灰小字
        "num":    dict(font=(FONT_FAMILY, 11, "bold"), foreground="#1a1a1a"),     # 行内数字加粗
        "bad":    dict(font=(FONT_FAMILY, 11, "bold"), foreground=COLOR_DEFICIT), # 行内负面评级词（红）
        "normal": dict(font=FONT, foreground="#222222"),                          # 正文
    }

    def __init__(self, parent, height=12, bg="#f0f7f0", grid=None):
        super().__init__(parent)
        if grid:
            self.grid(**grid)
        else:
            self.pack(fill="x")
        self.columnconfigure(0, weight=1)
        self.text = tk.Text(self, height=height, wrap="word", relief="flat",
                            bg=bg, font=FONT, padx=8, pady=6)
        self.text.grid(row=0, column=0, sticky="nsew")
        for tag, cfg in self._STYLES.items():
            self.text.tag_configure(tag, **cfg)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")
        self.text.config(state="disabled")

    def _fill(self, put):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        put()
        self.text.config(state="disabled")

    def set_rich(self, segments):
        """segments: [{"t": 文本, "tag": 语义}, ...]；未知 tag 回落 normal。"""
        def _put():
            for seg in segments:
                t = seg.get("t", "")
                tag = seg.get("tag", "normal")
                if tag not in self._STYLES:
                    tag = "normal"
                self.text.insert("end", t, tag)
        self._fill(_put)

    def set_text(self, plain):
        """纯字符串按 normal 渲染（错误提示等回落，兼容旧 _set_note 用法）。"""
        self._fill(lambda: self.text.insert("1.0", plain))

    # 智能着色用的关键词（决定结论行/正文行内如何着色）
    _POS_KEYS = ("省", "更划算", "更优", "更省", "健康", "合法", "增加", "更低",
                 "✅", "推荐", "值得", "符合")
    _NEG_KEYS = ("亏", "违法", "危险", "高利贷", "失控", "减少", "⚠", "更高",
                 "偏高", "不建议", "盖不住", "越还越多", "不符合")
    # 正文行内的负面评级词（标红，让"偏高/违法/失控"这类重点跳出来）
    _NEG_WORDS = ("偏高", "高利贷", "极高", "违法", "危险", "失控", "吃紧",
                  "盖不住", "越还越多", "不符合", "警戒", "不建议", "红线", "超额", "偏贵")
    # 匹配"数字"或"负面评级词"，用于正文行内细分着色
    _TOKEN_RE = re.compile(r"\d[\d,]*\.?\d*|" + "|".join(re.escape(w) for w in _NEG_WORDS))

    def set_smart_text(self, plain):
        """纯文本智能着色，不改变文字内容：
        - 【开头 → 小节标题（蓝加粗）
        - →/✅/✓/▶ 开头 → 结论行（大号：正绿/负红/中性深）
        - ⚠ 开头 → 警示（红小字）
        - 其余正文行：行内【数字加粗】、【负面评级词标红】，其余正常
        这样"月供 2,068""真实年化 22%""偏高/失控"等重点能从同字体里跳出来，
        又不会整片花花绿绿。"""
        pos, neg = self._POS_KEYS, self._NEG_KEYS

        def _put():
            for line in plain.split("\n"):
                s = line.strip()
                if not s:
                    self.text.insert("end", "\n")
                    continue
                if s.startswith("【"):
                    self.text.insert("end", line + "\n", "h")
                elif s.startswith("⚠"):
                    self.text.insert("end", line + "\n", "warn")
                elif s.startswith(("→", "✅", "✓", "✗", "▶")):
                    if any(k in s for k in pos):
                        tag = "big"
                    elif any(k in s for k in neg):
                        tag = "bigbad"
                    else:
                        tag = "emph"
                    self.text.insert("end", line + "\n", tag)
                else:
                    self._insert_line_tokens(line)
        self._fill(_put)

    def _insert_line_tokens(self, line):
        """正文行内：数字加粗(num)、负面评级词标红(bad)，其余正文(normal)。"""
        p = 0
        for m in self._TOKEN_RE.finditer(line):
            if m.start() > p:
                self.text.insert("end", line[p:m.start()], "normal")
            tok = m.group()
            self.text.insert("end", tok, "bad" if tok in self._NEG_WORDS else "num")
            p = m.end()
        if p < len(line):
            self.text.insert("end", line[p:], "normal")
        self.text.insert("end", "\n", "normal")


def make_radio_group(parent, title, options, default, descriptions=None,
                     columns=3, command=None):
    """
    生成一个 LabelFrame + 横排 Radiobutton 组。
    返回 (frame, var)：var 是 tk.StringVar，取值即当前选中。
    options: [选项值]; descriptions: 可选 {值: 说明}，显示在选项下方小字。
    """
    frame = ttk.LabelFrame(parent, text=title, padding=10)
    var = tk.StringVar(value=default)
    descriptions = descriptions or {}
    for i, opt in enumerate(options):
        r = i // columns
        c = i % columns
        cell = ttk.Frame(frame)
        cell.grid(row=r, column=c, sticky="w", padx=8, pady=4)
        rb = ttk.Radiobutton(cell, text=opt, value=opt, variable=var,
                             command=command)
        rb.pack(anchor="w")
        if opt in descriptions:
            ttk.Label(cell, text=descriptions[opt], style="Sub.TLabel").pack(anchor="w")
    return frame, var


def CardFrame(parent, title=None, padding=12):
    """统一的卡片/区块容器"""
    if title:
        f = ttk.LabelFrame(parent, text=title, padding=padding)
    else:
        f = ttk.Frame(parent, padding=padding)
    return f


class ResultTreeview(ttk.Frame):
    """统一明细表格：表头加粗、隔行变色、小计/总计/缺口行配色、自带滚动条"""

    def __init__(self, parent, columns, col_widths=None, height=14):
        """
        columns: [(key, 标题, 对齐), ...]
        col_widths: {key: 宽度}
        """
        super().__init__(parent)
        col_ids = ["#0"] + [c[0] for c in columns]
        # Treeview
        self.tree = ttk.Treeview(self, columns=[c[0] for c in columns],
                                 show="headings", height=height)
        col_widths = col_widths or {}
        for key, title, anchor in columns:
            self.tree.heading(key, text=title)
            self.tree.column(key, anchor=anchor, width=col_widths.get(key, 120),
                             stretch=True)
        # 滚动条
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        # 行样式 tag
        self.tree.tag_configure("subtotal", background=COLOR_SUBTOTAL)
        self.tree.tag_configure("total", background=COLOR_TOTAL)
        self.tree.tag_configure("deficit", background="#fbe3e0")
        self.tree.tag_configure("surplus", background="#e3f2e6")
        self.tree.tag_configure("income", background="#e3f2e6")
        # 偶数行浅灰
        self.tree.tag_configure("odd", background="#fafafa")

    def clear(self):
        self.tree.delete(*self.tree.get_children())

    def add_row(self, values, tag=""):
        return self.tree.insert("", "end", values=values, tags=(tag,) if tag else ())

    def add_subtotal(self, values):
        return self.add_row(values, tag="subtotal")

    def add_total(self, values):
        return self.add_row(values, tag="total")


class ProportionBars(tk.Canvas):
    """
    自绘横向比例条。输入 [(label, value, color), ...]，按金额比例画条。
    """

    def __init__(self, parent, data=None, height=200, **kw):
        super().__init__(parent, height=height, bg="white", highlightthickness=0, **kw)
        self._data = data or []
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, data):
        """data: [(label, value), ...]"""
        self._data = data
        self._draw()

    def _draw(self):
        self.delete("all")
        if not self._data:
            return
        w = max(self.winfo_width(), 200)
        total = sum(v for _, v in self._data) or 1
        row_h = 34
        pad_x = 8
        label_w = 150          # 左侧标签宽度
        bar_x = pad_x + label_w
        bar_max_w = w - bar_x - 120   # 右侧留给金额文字
        colors = ["#2c5fa8", "#3a7ca5", "#5aa9c7", "#7fc4d6",
                  "#a5d8c9", "#c9e3b0", "#e3d9a0", "#e3b0a0"]
        for i, (label, value) in enumerate(self._data):
            y = i * row_h + 6
            # 标签
            self.create_text(pad_x, y + 9, anchor="w", text=label,
                             font=(FONT_FAMILY, 10), fill="#333", width=label_w - 6)
            # 比例条
            frac = max(value / total, 0) if total else 0
            bw = max(int(bar_max_w * frac), 1)
            color = colors[i % len(colors)]
            self.create_rectangle(bar_x, y, bar_x + bw, y + 20,
                                  fill=color, outline="")
            pct = frac * 100
            # 金额 + 占比
            txt = f"{value/10000:.1f}万  {pct:.0f}%"
            self.create_text(bar_x + bw + 6, y + 10, anchor="w", text=txt,
                             font=(FONT_FAMILY, 9), fill="#555")


class BigNumberLabel(ttk.Frame):
    """大字号数字 label，支持 set_value(amount, kind) 自动配色"""

    def __init__(self, parent, kind="neutral"):
        super().__init__(parent)
        self.label = tk.Label(self, font=FONT_BIG, fg="#222")
        self.label.pack()
        self.set_value(0, kind)

    def set_value(self, amount, kind="neutral"):
        color = {"surplus": COLOR_SURPLUS, "deficit": COLOR_DEFICIT,
                 "income": COLOR_ACCENT, "neutral": "#222"}.get(kind, "#222")
        sign = ""
        if kind == "deficit":
            sign = "−"  # 负号用全角减号更醒目
        elif kind == "surplus":
            sign = "+"
        text = f"{sign}{amount:,.0f} 元/月"
        self.label.config(text=text, fg=color)


class ScrollableFrame(ttk.Frame):
    """可垂直滚动的容器：内容超出可见高度时可上下滚动，宽度随窗口自适应。

    用法：
        sf = ScrollableFrame(parent); sf.pack(fill="both", expand=True)
        往 sf.inner 里 pack/grid 子控件即可。
    鼠标进入区域时响应滚轮，离开时释放，避免多个滚动区互相干扰。
    """

    def __init__(self, parent, bg="#ffffff", **kw):
        super().__init__(parent, **kw)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg=bg)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        # 滚动条默认隐藏，内容超高时由 _update_vsb 自动显示
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        self._inner_win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_content)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Enter>", self._enter)
        self.canvas.bind("<Leave>", self._leave)

    def _on_content(self, _):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_vsb()

    def _on_resize(self, event):
        # 内部宽度跟随画布，避免出现水平滚动条
        self.canvas.itemconfig(self._inner_win, width=event.width)
        self._update_vsb()

    def _update_vsb(self):
        """内容不超高时隐藏滚动条，超高时才显示（自动隐藏）。"""
        self.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox is None:
            return
        if (bbox[3] - bbox[1]) > self.canvas.winfo_height():
            if not self.vsb.winfo_ismapped():
                self.vsb.pack(side="right", fill="y", before=self.canvas)
        else:
            if self.vsb.winfo_ismapped():
                self.vsb.pack_forget()

    def _enter(self, _):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _leave(self, _):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def format_money_short(x):
    """纯万元简写：87.3 万"""
    if x >= 10000:
        return f"{x/10000:.1f} 万"
    return f"{x:,.0f}"


def format_money_full(x):
    """万元 + 元 双单位：87.3 万元（873,000 元）"""
    if x >= 10000:
        return f"{x/10000:.2f} 万元（{x:,.0f} 元）"
    return f"{x:,.0f} 元"


class SalaryBreakdownBar(tk.Canvas):
    """
    工资去向堆叠条（横向100%条）。
    输入 [(label, amount, color_hex), ...]，按百分比画堆叠条。
    """

    def __init__(self, parent, data=None, title="你的工资去哪儿了", **kw):
        super().__init__(parent, height=120, bg="white", highlightthickness=0, **kw)
        self._data = data or []
        self._title = title
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, data):
        """data: [(label, amount, color), ...]"""
        self._data = data
        self._draw()

    def _draw(self):
        self.delete("all")
        if not self._data:
            return
        w = max(self.winfo_width(), 300)
        total = sum(v for _, v, _ in self._data) or 1
        bar_y = 36
        bar_h = 32
        pad_x = 12

        # 标题
        self.create_text(pad_x, 8, anchor="w", text=self._title,
                         font=(FONT_FAMILY, 11, "bold"), fill=COLOR_ACCENT)

        avail = w - pad_x * 2 - 8 * (len(self._data) - 1)
        x = pad_x
        for label, value, color in self._data:
            frac = max(value / total, 0)
            sw = max(int(avail * frac), 4)
            self.create_rectangle(x, bar_y, x + sw, bar_y + bar_h,
                                  fill=color, outline="white", width=1)
            if sw > 60:
                self.create_text(x + sw // 2, bar_y + bar_h // 2,
                                 text=f"{frac*100:.0f}%",
                                 font=(FONT_FAMILY, 9, "bold"), fill="white")
            x += sw + 8

        # 图例：每项固定宽度，超出宽度则换行
        legend_y = bar_y + bar_h + 10
        lx = pad_x
        LEGEND_W = 150
        for label, value, color in self._data:
            if lx + LEGEND_W > w - pad_x:
                lx = pad_x
                legend_y += 18
            self.create_rectangle(lx, legend_y, lx + 14, legend_y + 14,
                                  fill=color, outline="")
            self.create_text(lx + 18, legend_y + 7, anchor="w", text=f"{label} {value:,.0f}",
                             font=(FONT_FAMILY, 9), fill="#555")
            lx += LEGEND_W


class TrendLineChart(tk.Canvas):
    """多系列折线趋势图（双 y 轴：左=金额，右=百分比）。

    用于长期跟踪：把多次快照的指标画成折线，看结余/存款/成本等随时间的变化。
    用法：
        chart = TrendLineChart(parent, height=320); chart.pack(fill="both", expand=True)
        chart.set_data(
            labels=["6/21", "7/05", "7/20"],
            series=[("月结余",  [4612, 5200, 6100],   COLOR_SURPLUS, "left"),
                    ("存款",    [50000, 55000, 62000], COLOR_ACCENT,  "left"),
                    ("月度成本",[2910, 2850, 2800],   "#d97706",     "left"),
                    ("月负债",  [2000, 2000, 1500],   COLOR_DEFICIT, "left"),
                    ("结余率%", [60, 65, 72],         "#8e44ad",     "right")])
    series: [(名称, [值...], 颜色, "left"/"right"), ...]，长度需与 labels 一致。
    """

    def __init__(self, parent, height=320, **kw):
        super().__init__(parent, height=height, bg="white", highlightthickness=0, **kw)
        self._labels = []
        self._series = []
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, labels, series):
        self._labels = list(labels or [])
        self._series = list(series or [])
        self._draw()

    def _draw(self):
        self.delete("all")
        w = max(self.winfo_width(), 360)
        h = max(self.winfo_height(), 220)
        labels, series = self._labels, self._series
        left_m, right_m, top_m, bot_m = 64, 52, 16, 64
        x0, x1, y0, y1 = left_m, w - right_m, top_m, h - bot_m
        chart_w, chart_h = x1 - x0, y1 - y0

        if not labels or not series:
            self.create_text(w // 2, h // 2, anchor="center",
                             text="（暂无数据：关闭程序时存一份跟踪快照后，这里显示变化趋势）",
                             font=(FONT_FAMILY, 10), fill="#999", width=w - 80)
            return

        n = len(labels)
        # 左轴量纲（金额）：有负值则下探，全正则从 0 起
        left_vals = [v for _, vals, _, axis in series if axis == "left" for v in vals]
        if left_vals:
            rmin, rmax = min(left_vals), max(left_vals)
            if rmin == rmax:
                rmin, rmax = rmin - 1, rmax + 1
            pad = (rmax - rmin) * 0.1
            lmax = rmax + pad
            lmin = (rmin - pad) if rmin < 0 else 0
        else:
            lmin, lmax = 0, 1

        def xl(i):
            return (x0 + x1) / 2 if n == 1 else x0 + chart_w * i / (n - 1)

        def yl(v):
            return y0 + (1 - (v - lmin) / (lmax - lmin)) * chart_h

        def yr(v):  # 右轴 0~100%
            return y0 + (1 - max(0, min(100, v)) / 100) * chart_h

        # 网格 + 左轴刻度
        for k in range(5):
            gy = y0 + chart_h * k / 4
            self.create_line(x0, gy, x1, gy, fill="#eeeeee")
            val = lmax - (lmax - lmin) * k / 4
            self.create_text(x0 - 6, gy, anchor="e", text=format_money_short(val),
                             font=(FONT_FAMILY, 8), fill="#888888")
        # 右轴刻度
        for v in (0, 25, 50, 75, 100):
            self.create_text(x1 + 6, yr(v), anchor="w", text=f"{v}%",
                             font=(FONT_FAMILY, 8), fill="#8e44ad")
        self.create_text(x0 - 6, y0 - 6, anchor="se", text="元",
                         font=(FONT_FAMILY, 8), fill="#888888")

        # 折线 + 点
        for name, vals, color, axis in series:
            if len(vals) != n:
                continue
            ys = [yl(v) if axis == "left" else yr(v) for v in vals]
            pts = [(xl(i), ys[i]) for i in range(n)]
            if n >= 2:
                flat = [c for p in pts for c in p]
                self.create_line(flat, fill=color, width=2)
            for px, py in pts:
                self.create_oval(px - 3, py - 3, px + 3, py + 3, fill=color, outline="white")

        # x 轴标签（多则抽稀）
        step = max(1, (n + 4) // 5)
        for i in range(0, n, step):
            self.create_text(xl(i), y1 + 8, anchor="n", text=labels[i],
                             font=(FONT_FAMILY, 8), fill="#666666")

        # 图例（底部，自动换行）
        lx, ly, leg_w = x0, h - 28, 96
        for name, vals, color, axis in series:
            if lx + leg_w > x1:
                lx, ly = x0, ly + 16
            self.create_rectangle(lx, ly - 7, lx + 12, ly + 5, fill=color, outline="")
            self.create_text(lx + 16, ly - 1, anchor="w", text=name,
                             font=(FONT_FAMILY, 9), fill="#444444")
            lx += leg_w


class ComparisonTable(ttk.Frame):
    """
    并排对比表格：左右两列指标对比，中间显示变化率/差值。
    用于城市对比页面。
    """

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)

    def build(self, data, left_label, right_label, diff_label="差额"):
        """
        data: [(label, left_val, right_val, diff_val, unit), ...]
        其中 val 可以是 None 表示"N/A"
        """
        for w in self.winfo_children():
            w.destroy()

        # 表头
        hdr = ttk.Frame(self)
        hdr.pack(fill="x", pady=(0, 4))
        ttk.Label(hdr, text="指标", width=18, font=FONT_BOLD).pack(side="left", padx=4)
        ttk.Label(hdr, text=left_label, width=16, font=FONT_BOLD,
                  foreground=COLOR_ACCENT).pack(side="left", padx=4)
        ttk.Label(hdr, text=diff_label, width=10, font=FONT_BOLD).pack(side="left", padx=4)
        ttk.Label(hdr, text=right_label, width=16, font=FONT_BOLD,
                  foreground="#3a7ca5").pack(side="left", padx=4)

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=2)

        # 数据行
        for label, lv, rv, dv, unit in data:
            row = ttk.Frame(self)
            row.pack(fill="x", pady=3)

            ttk.Label(row, text=label, width=18, font=FONT).pack(side="left", padx=4)

            # 左值
            ltxt = f"{lv:,.0f}" if lv is not None else "—"
            ttk.Label(row, text=ltxt, width=16, font=FONT,
                      foreground=COLOR_ACCENT).pack(side="left", padx=4)

            # 差额
            if dv is not None:
                color = COLOR_SURPLUS if dv > 0 else (COLOR_DEFICIT if dv < 0 else "#888")
                sign = "+" if dv > 0 else ""
                ttk.Label(row, text=f"{sign}{dv:,.0f}{unit}", width=10, font=FONT,
                          foreground=color).pack(side="left", padx=4)
            else:
                ttk.Label(row, text="—", width=10, font=FONT).pack(side="left", padx=4)

            # 右值
            rtxt = f"{rv:,.0f}" if rv is not None else "—"
            ttk.Label(row, text=rtxt, width=16, font=FONT,
                      foreground="#3a7ca5").pack(side="left", padx=4)

            # 分隔线
            ttk.Separator(self, orient="horizontal").pack(fill="x", pady=1)
