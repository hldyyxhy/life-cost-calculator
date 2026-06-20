# -*- coding: utf-8 -*-
"""
report.py —— 综合报告生成（纯函数）

把档案 + 各模块（处境/对比/三座山）的计算结果汇总成一份可保存的文本文档，
并基于数据给出针对性的「综合建议」。

输入都是各模块已算好的 dict/str（没算过的模块传 None，报告里标注「未计算」）。
"""

from datetime import datetime
import profile as P
import cost_data as D


def _fmt_profile(profile):
    """档案 dict → 人类可读行列表（按组、跳过空值）。"""
    lines = []
    for group, fields in P.FIELD_DEFS.items():
        lines.append(f"【{P.GROUP_TITLES[group]}】")
        for key, default, label, ctype, meta in fields:
            val = profile.get(key, default)
            if ctype == "entry" and val == "":
                continue  # 未填的字段不显示
            if ctype == "check":
                val = "是" if val else "否"
            lines.append(f"  · {label}：{val}")
        lines.append("")
    return lines


def _fmt_current(cur):
    """处境页结果 → 文本片段。"""
    if not cur:
        return ["（尚未计算：请到「我现在的处境」点「算一算」）", ""]
    L = ["【二、我现在的处境（月度）】"]
    L.append(f"  · 到手收入：{cur['income_net']:,} 元/月　（五险一金 {cur['social_ins']:,}、个税 {cur['tax']:,}）")
    L.append(f"  · 生存成本：{cur['cost_total']:,} 元/月　（城市生存底线 {cur['survival_baseline']:,}）")
    sign = "+" if cur['surplus'] >= 0 else ""
    L.append(f"  · 月结余：{sign}{cur['surplus']:,} 元/月　（结余率 {cur['surplus_rate']:.0f}%）")
    if cur.get("house_saving_years"):
        L.append(f"  · 攒够婚房首付约需 {cur['house_saving_years']:.0f} 年")
    L.append("")
    if cur.get("interpretation"):
        for ln in cur["interpretation"].split("\n"):
            if ln.strip():
                L.append("    " + ln)
        L.append("")
    return L


def _fmt_compare(cmp):
    """对比页结果 → 文本片段。"""
    if not cmp:
        return ["【三、城市加减法】", "  （尚未计算：请到「城市加减法」点「开始对比」）", ""]
    L = ["【三、城市加减法】"]
    if cmp.get("comparison_text"):
        for ln in cmp["comparison_text"].split("\n"):
            if ln.strip():
                L.append("  " + ln)
    cur, tgt = cmp.get("current"), cmp.get("target")
    if cur and tgt:
        L.append(f"  · 当前城市：到手 {cur['income_net']:,} / 成本 {cur['cost_total']:,} / 结余 {cur['surplus']:,}")
        L.append(f"  · 目标城市：到手 {tgt['income_net']:,} / 成本 {tgt['cost_total']:,} / 结余 {tgt['surplus']:,}")
    L.append("")
    return L


def _fmt_milestones(ms):
    """三座山 → 文本片段。ms = {"marriage":..., "child":..., "retire":...}，每项是文本或 None。"""
    L = ["【四、人生三座山】"]
    for key, title in (("marriage", "结婚"), ("child", "养娃"), ("retire", "养老")):
        txt = (ms or {}).get(key)
        L.append(f"  ▸ {title}：")
        if txt:
            for ln in txt.split("\n"):
                if ln.strip():
                    L.append("      " + ln)
        else:
            L.append("      （尚未计算）")
    L.append("")
    return L


def build_advice(profile, cur, cmp, ms):
    """基于数据生成针对性综合建议（行列表）。"""
    L = ["【综合建议】"]
    tips = []

    if cur:
        sr = cur["surplus_rate"]
        surplus = cur["surplus"]
        if surplus < 0:
            tips.append(f"⚠️ 你目前入不敷出，每月缺口 {-surplus:,} 元。可以从两方面着手："
                        f"一是增收（副业/换岗），二是减支（把「宽裕」档饮食降为「普通」、不养车、搬郊区合租），"
                        f"先把每月成本压到生存底线以内。")
        elif sr < 10:
            tips.append(f"结余率仅 {sr:.0f}%，抗风险能力极弱。建议把饮食/交通降一档，"
                        f"目标是月结余率提到 20% 以上（约多存 {cur['cost_total']*0.1:,.0f} 元/月）。")
        elif sr < 20:
            tips.append(f"结余率 {sr:.0f}%，略低于 20% 健康线。控制人情娱乐、给老家等弹性支出即可达标。")
        else:
            tips.append(f"✅ 结余率 {sr:.0f}%，处于健康区间。可考虑把结余的一部分用于应急金、一部分做长期储备。")

        # 买房
        if cur.get("house_saving_years"):
            yrs = cur["house_saving_years"]
            if yrs >= 30:
                tips.append(f"按当前结余攒首付需 {yrs:.0f} 年，几乎不现实。可考虑：换低成本城市、"
                            f"双收入家庭、或降低购房预期（小户型/远郊）。")

    # 抗风险（用档案里的存款 + 处境的生存底线）
    try:
        savings = float(profile.get("savings") or 0)
    except (TypeError, ValueError):
        savings = 0
    if cur and savings is not None:
        baseline = cur.get("survival_baseline", 0) or 1
        months = savings / baseline if baseline > 0 else 0
        if savings < 50000:
            tips.append(f"🔴 存款 {savings:,.0f} 元偏低：失业仅能撑 {months:.1f} 个月，"
                        f"一次大病自付（约5-10万）就可能击穿。建议优先攒够 {baseline*3:,.0f} 元（3个月底线）应急金。")
        elif months < 6:
            tips.append(f"应急储备偏薄：失业能撑 {months:.1f} 个月，建议攒到 6 个月底线（约 {baseline*6:,.0f} 元）。")

    # 养娃（三座山的养娃片段里若提到占比）
    child_txt = (ms or {}).get("child") or ""
    if "耗尽" in child_txt or "入不敷出" in child_txt:
        tips.append("养娃成本已接近或超过你的结余能力。建议选普惠路线（公办+基础养育），"
                    "避免在课外班上过度投入；有伴侣的话按家庭收入评估更现实。")

    # 城市对比
    if cmp and cmp.get("surplus_diff", 0) > 0:
        tips.append(f"城市对比显示：移居目标城市后每月结余可增加 {cmp['surplus_diff']:,} 元，"
                    f"值得一试（尤其对买房年限的改善明显）。")

    if not tips:
        tips.append("数据已记录。建议保持稳定储蓄，量入为出，定期用本工具复盘。")

    for i, t in enumerate(tips, 1):
        L.append(f"  {i}. {t}")
    L.append("")
    return L


def build_full_report(profile, cur, cmp, ms):
    """汇总成完整报告字符串。"""
    L = ["＝ 生活成本计算器 · 个人计算结果 ＝"]
    L.append(f"生成时间：{datetime.now():%Y-%m-%d %H:%M}")
    L.append("（所有数字为公开调研的估算中值，仅供了解量级，不作为理财依据。）")
    L.append("")
    L.append("【一、基本档案】")
    L += _fmt_profile(profile)
    L += _fmt_current(cur)
    L += _fmt_compare(cmp)
    L += _fmt_milestones(ms)
    L += build_advice(profile, cur, cmp, ms)
    return "\n".join(L)
