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
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        self._inner_win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_content)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Enter>", self._enter)
        self.canvas.bind("<Leave>", self._leave)

    def _on_content(self, _):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_resize(self, event):
        # 内部宽度跟随画布，避免出现水平滚动条
        self.canvas.itemconfig(self._inner_win, width=event.width)

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
