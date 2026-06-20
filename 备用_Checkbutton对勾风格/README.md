# 备用：Checkbutton 对勾风格指示符

主程序当前的勾选框用**圆点风格**（复用 Radiobutton 的 clam 原生圆点，与单选项统一、选中填实心点）。

本文件夹保留的是上一版**自绘「蓝底白勾」方块方案**——选中=主色蓝实心方块+白色对勾，未选中=白底灰框。
用户认可这套对勾的效果，但更偏好「圆点统一」，故主程序切回圆点，对勾方案在此留作备用。

## 文件

- `对勾风格指示符.py` —— `_make_checkbutton_indicator` 函数 + 集成步骤（文件顶部注释）。

## 切回对勾风格

按 `对勾风格指示符.py` 顶部注释：把函数复制进 `gui_widgets.py`，并替换 `apply_style` 里
「复用 Radiobutton 圆点」那段 try 块为 `element_create` + layout 替换（代码已给出）。

## 备注

- 自绘像素图可用脚本读 `img.get(x,y)` 打印 ASCII 自检形状（见记忆 `ui-visual-work-needs-reference` 的「像素自验证」法）。
- 当年自绘时发现过一个坑：`PhotoImage.put(color)` 不带 `to=` 只填 1 个像素，底色必须用 `put(color, (0,0,sz,sz))` 填满。
