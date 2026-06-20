# -*- coding: utf-8 -*-
"""备用：Checkbutton「蓝底白勾」对勾风格指示符（自绘）

主程序当前用「圆点」风格勾选框（复用 Radiobutton 的 clam 原生圆点，与单选项统一、
选中填实心点）。这套自绘「蓝底白勾」方块方案是上一版实现，用户认可效果但更偏好圆点统一，
故切回圆点，对勾方案在此留作备用——日后想切回方块对勾，按下方集成即可。

------------------------------------------------------------
集成方式（替换 gui_widgets.py 里 apply_style 中的圆点方案）：

1. 把下面的 _make_checkbutton_indicator 函数复制进 gui_widgets.py（模块级）。

2. 在 apply_style 末尾，把「复用 Radiobutton 圆点」那段 try 块替换为：

    try:
        _cb_off, _cb_on = _make_checkbutton_indicator(root)
        root._checkbutton_imgs = (_cb_off, _cb_on)   # 持引用防 GC
        style.element_create("CheckCb.indicator", "image",
                             _cb_off, ("selected", _cb_on))

        def _swap_indicator(nodes):
            out = []
            for name, opts in nodes:
                if name == "Checkbutton.indicator":
                    name = "CheckCb.indicator"
                opts = dict(opts)
                if "children" in opts:
                    opts["children"] = _swap_indicator(opts["children"])
                out.append((name, opts))
            return out

        style.layout("TCheckbutton", _swap_indicator(style.layout("TCheckbutton")))
    except Exception:
        pass

------------------------------------------------------------
验证方式：自绘像素图可写脚本读 img.get(x,y) 打印 ASCII 自检形状
（见记忆 ui-visual-work-needs-reference 的「像素自验证」法）。
"""
import tkinter as tk

COLOR_ACCENT = "#2c5fa8"   # 与主程序配色一致


def _make_checkbutton_indicator(root):
    """自绘 Checkbutton 指示符图像（14×14）。

    选中 = 主色蓝实心方块 + 白色对勾；未选中 = 白底 + 灰边框。
    用纯像素绘制，绕开 clam 主题的对勾渲染——后者在部分 Windows 字体/DPI 下
    容易被误看成「叉/删除」，换成实心方块后语义无歧义（填满=已勾选）。
    返回 (unchecked, checked)，已绑定 root 以防被回收。
    """
    sz = 14
    unchecked = tk.PhotoImage(width=sz, height=sz, master=root)
    checked = tk.PhotoImage(width=sz, height=sz, master=root)
    # 未选中：白底 + 1px 灰边框
    unchecked.put("#ffffff", (0, 0, sz, sz))
    border = "#9aa3ad"
    for i in range(sz):
        unchecked.put(border, (i, 0))
        unchecked.put(border, (i, sz - 1))
        unchecked.put(border, (0, i))
        unchecked.put(border, (sz - 1, i))
    # 选中：主色蓝实心底
    checked.put(COLOR_ACCENT, (0, 0, sz, sz))
    # 白色对勾（约 2px 粗，坐标手工排布形成勾形）
    white = "#ffffff"
    for x, y in [(4, 8), (5, 9), (6, 10), (4, 9), (5, 10),
                 (7, 9), (8, 8), (9, 7), (10, 5), (11, 4),
                 (7, 10), (8, 9), (9, 8), (10, 6), (11, 5)]:
        checked.put(white, (x, y))
    return unchecked, checked
