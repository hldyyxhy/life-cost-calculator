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
            ("h", "关于这个工具  ·  v1.2"),
            ("normal",
             "这是一个面向普通劳动者的「生活成本计算器」。本工具的目的，是帮助劳动者"
             "看清自己的生活成本、明确努力方向；更关键的是补「信息差」——告诉你不知道的"
             "权利 / 补贴 / 陷阱，算完给可立刻执行的动作。信息差比收入差更致命。\n"),
            ("normal",
             "设计思路：工具负责「算死的」（结构化计算 + 你的数据填充），再一键生成"
             "「问 AI」的提示词（带你的具体情况），复制去问任意 AI（豆包 / Kimi / DeepSeek 等），"
             "拿到结合本地政策的详细建议——因为你最缺的往往不是答案，而是「怎么把问题问清楚」。\n"),
            ("h2", "八个模块"),
            ("normal",
             "① 我的档案：填写个人情况（年龄、城市、工资、家庭），可一键同步到各页。\n"),
            ("normal",
             "② 我现在的处境：输入工资、城市、生活方式、家庭负担，算出每月到手收入、"
             "生存成本与结余/缺口，附工资去向、生存底线、攒首付年限等指标。\n"),
            ("normal",
             "③ 城市加减法：并排对比两个城市的收入、成本、结余、攒首付年限，回答「换城市值不值」。\n"),
            ("normal",
             "④ 人生三座山：结婚（彩礼+婚礼+婚房）、养娃（普惠/中产/高端三档）、"
             "养老（退休金与支出缺口），各自独立计算。\n"),
            ("normal",
             "⑤ 借贷真相：反算真实年化（IRR）、等额本息 vs 等本等息对比、可承受负债上限、"
             "多笔债雪球/雪崩模拟、以贷养贷螺旋演示。\n"),
            ("normal",
             "⑥ 劳动权益：加班费依法反算（含维权现实评估）、最低工资对照、失业金对照、"
             "灵活就业社保补贴（4050）对照、工伤赔偿估算。\n"),
            ("normal",
             "⑦ 求助渠道：按常见困境（欠薪/社保/辞退/工伤/消费/网贷催收等）生成提示词，"
             "让 AI 告诉你该找谁、打什么电话、怎么操作。\n"),
            ("normal",
             "⑧ 关于与数据说明：即本页。\n"),
            ("h2", "「问 AI」提示词体系"),
            ("normal",
             "除档案外，几乎每个功能都有「生成问 AI 的提示词」按钮（醒目蓝色）。点开后弹窗里是"
             "一段带你的具体数据、可一键复制的提示词，粘到任意 AI 即可得到比工具内置解读详细得多、"
             "且结合本地政策的回答。需各地数据的功能（失业金 / 补贴 / 工伤等）已用 rights_data.py "
             "本地算出硬数字，同时保留提示词让 AI 补充申领流程等细则。\n"),
            ("h2", "城市分级说明（第一财经标准）"),
        ] + self._tier_lines() + [
            ("h2", "数据来源与可靠性"),
            ("normal",
             "本工具数据来自 2023-2026 年公开调研报告，包括：育娲人口研究"
             "《中国生育成本报告 2026 版》、国家统计局《2025 年国民经济和社会发展统计公报》、"
             "北大 CIEFR 教育支出调查、国家医保局、人社部 2025-2026 年社保缴费基数与最低工资标准、"
             "各市统计局、贝壳/中指/麟评居住大数据研究院（2025 百城房价与租金）、"
             "中规院《2025 城市通勤监测报告》等。\n"),
            ("normal",
             "劳动权益类数据（各省最低工资、失业保险金、灵活就业社保补贴、工伤赔偿）见 "
             "rights_data.py，来自人社部官网及各地人社局/社保局 2025-2026 年公告、"
             "《工伤保险条例》。详见上级目录「调研数据」文件夹（含详细文档）。\n"),
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
