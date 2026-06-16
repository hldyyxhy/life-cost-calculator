# -*- coding: utf-8 -*-
"""
main.py —— 生活成本计算器入口

运行方式（任选其一）：
    双击运行：            main.py
    命令行：              python main.py
    命令行（全路径）：    python.exe main.py

依赖：仅 Python 标准库（tkinter），无需安装第三方包。
"""

import os
import sys

# 确保能找到同目录下的模块（双击运行时有时 CWD 不正确）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gui_app


if __name__ == "__main__":
    gui_app.main()
