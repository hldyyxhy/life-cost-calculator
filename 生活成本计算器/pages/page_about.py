# -*- coding: utf-8 -*-
"""
page_about.py —— 关于与数据说明页
"""

import tkinter as tk
from tkinter import ttk
import gui_widgets as W
import cost_data as D


class AboutPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # 滚动文本区
        wrap = ttk.Frame(self, padding=14)
        wrap.pack(fill="both", expand=True)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        txt = tk.Text(wrap, wrap="word", relief="flat", bg="white",
                      font=(W.FONT_FAMILY, 11), padx=16, pady=14,
                      spacing1=3, spacing3=3)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        content = self._content()
        # 用 tag 实现标题加粗
        txt.tag_configure("h", font=(W.FONT_FAMILY, 15, "bold"),
                          foreground=W.COLOR_ACCENT, spacing3=8)
        txt.tag_configure("h2", font=(W.FONT_FAMILY, 12, "bold"),
                          foreground=W.COLOR_ACCENT, spacing1=8, spacing3=4)
        txt.tag_configure("normal", font=(W.FONT_FAMILY, 11), spacing1=2)
        for kind, text in content:
            txt.insert("end", text + "\n", kind)
        txt.configure(state="disabled")

    def _content(self):
        return [
            ("h", "关于这个工具"),
            ("normal",
             "这是一个面向普通劳动者的「生活成本计算器」。资产阶级通常非常了解"
             "资本的运作，而普通人常常缺乏理财能力，甚至不清楚自己的钱花到了哪里、"
             "某个目标究竟需要多少钱。本工具的目的，是帮助无产阶级和广大劳动者，"
             "看清自己的生活成本、明确努力的方向。\n"),
            ("h2", "三个模块"),
            ("normal",
             "① 我现在的处境：输入年龄、工资、城市、生活方式、家庭负担等，算出你每月"
             "的到手收入、生存成本与结余/缺口。新增「工资去向」堆叠条、城市生存底线、"
             "结余率健康评级、攒够婚房首付所需年数等指标，并用白话解读你的处境。\n"),
            ("normal",
             "② 城市加减法：选择当前城市与目标城市，并排对比到手收入、生存成本、"
             "结余率、攒首付年限等指标，并自动预估目标城市工资，回答「换城市值不值」。\n"),
            ("normal",
             "③ 人生三座山：把人生的三座大山拆成独立模块——结婚（彩礼+婚礼+婚房首付）、"
             "养娃（普惠/中产/高端三档到大学毕业）、养老（退休金与支出的缺口）。"
             "三座山各自独立计算，不必一次性填完。\n"),
            ("h2", "城市分级说明（第一财经标准）"),
        ] + self._tier_lines() + [
            ("h2", "数据来源与可靠性"),
            ("normal",
             "本工具所有数据来自 2023-2026 年公开调研报告，包括：育娲人口研究"
             "《中国生育成本报告 2026 版》（0-17岁全国累计约 58 万、城镇 71.3 万）、"
             "国家统计局《2025 年国民经济和社会发展统计公报》（城镇居民人均可支配"
             "收入 56,502 元、人均消费支出八大类细分）、北大 CIEFR 教育支出调查、"
             "国家医保局、人社部 2025 年社保缴费基数与最低工资标准（截至 2025 年 10 月）、"
             "各市统计局、贝壳/中指/麟评居住大数据研究院（2025 百城房价与租金）、"
             "中规院《2025 城市通勤监测报告》等。详见上级目录「调研数据」文件夹"
             "（含 6 份详细文档）。\n"),
            ("normal",
             "近期重要更新：2025 年殡葬行业整治后人均治丧费用下降约 33%，经营性墓穴"
             "均价从 12 万腰斩至 6.3 万；公积金贷款首套利率下调至 2.6%，商业首套约 3.05%；"
             "2025 年全国企业退休人员月均养老金约 3,322 元。\n"),
            ("h2", "重要提醒"),
            ("normal",
             "· 所有数字均为估算中值，个体实际差异可能很大，仅供了解量级与结构。\n"
             "· 城市成本系数以「三线城市≈全国城镇平均」为 1.0 基准换算。\n"
             "· 彩礼、丧葬等强文化属性项目，地域差异大于城市差异，请按本地实际调整。\n"
             "· 城市对比中的目标城市工资按「等比例缩放」预估：保持你在本地的相对工资"
             "位置不变，即 目标工资 = 你的工资 × (目标城市典型工资 ÷ 当前城市典型工资)。\n"
             "· 未计入通货膨胀、失业、大病、意外等风险，也未考虑时间价值。\n"
             "· 本工具不作为任何理财、投资或消费决策的依据。\n"),
            ("h2", "成本系数表（养育档位 / 城市等级）"),
        ] + self._factor_lines()

    def _tier_lines(self):
        lines = []
        for t in D.TIER_KEYS:
            info = D.TIER_CITIES[t]
            cities = "、".join(info["cities"][:6])
            if len(info["cities"]) > 6:
                cities += " 等"
            lines.append(("normal", f"· {t}：{cities}。{info['desc']}"))
        return lines

    def _factor_lines(self):
        lines = []
        lines.append(("normal", "养育档位系数（普惠=1.0）："))
        for lv, d in D.RAISE_LEVELS.items():
            lines.append(("normal", f"    {lv}：×{d['factor']}　{d['desc']}"))
        lines.append(("normal", "城市成本系数（三线=1.0）："))
        for t in D.TIER_KEYS:
            lines.append(("normal",
                          f"    {t}：×{D.COST_FACTOR[t]}　"
                          f"典型月薪约 {D.TYPICAL_WAGE[t]:,} 元，房价约 "
                          f"{D.TIER_PROFILE[t]['house_price']:,} 元/㎡"))
        return lines
