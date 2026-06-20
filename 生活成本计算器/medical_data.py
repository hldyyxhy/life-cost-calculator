# -*- coding: utf-8 -*-
"""
medical_data.py —— 医保就医数据（2025-2026）

数据来源：调研数据/09_医保就医细则.md（第一轮 + 第二轮补齐）
注意：医保政策各地差异大、每年调整，起付/封顶/报销比为代表值，估算以当地医保局为准。
对接：page_medical.py + calc_engine.estimate_medical_cost。
"""

import cost_data as D
import rights_data as R

# 省名归一（深圳等单列城市归到所在省查职工住院表）
_PROVINCE_ALIAS = {"深圳": "广东"}


# ============================================================
# 1. EMPLOYEE_INPATIENT —— 职工医保住院（三级医院）31 省
# 报销比为小数（0.80=80%）；退休为 None 时按 在职+0.04 估（ret_est=True）
# ============================================================
EMPLOYEE_INPATIENT = {
    "北京": {"城市": "北京", "在职": 0.90, "退休": None, "ret_est": True,
             "起付": 1300, "封顶": 500000, "备注": "三级分段 85%~95%"},
    "上海": {"城市": "上海", "在职": 0.85, "退休": 0.90, "ret_est": False,
             "起付": 1500, "封顶": 530000, "备注": ""},
    "重庆": {"城市": "重庆", "在职": 0.80, "退休": None, "ret_est": True,
             "起付": 1200, "封顶": 460000, "备注": "起付 300~1200 取上限"},
    "天津": {"城市": "天津", "在职": 0.85, "退休": None, "ret_est": True,
             "起付": 1000, "封顶": 450000, "备注": "按直辖市估"},
    "广东": {"城市": "广州", "在职": 0.80, "退休": 0.86, "ret_est": False,
             "起付": 1000, "封顶": 950000, "备注": "封顶最高之一"},
    "浙江": {"城市": "杭州", "在职": 0.85, "退休": 0.89, "ret_est": False,
             "起付": 800, "封顶": 400000, "备注": "4 万分段"},
    "江苏": {"城市": "南京", "在职": 0.90, "退休": 0.93, "ret_est": False,
             "起付": 1000, "封顶": 600000, "备注": "部分无上限"},
    "福建": {"城市": "福州", "在职": 0.78, "退休": None, "ret_est": True,
             "起付": 800, "封顶": 300000, "备注": "估算"},
    "山东": {"城市": "济南", "在职": 0.90, "退休": None, "ret_est": True,
             "起付": 1000, "封顶": 600000, "备注": "分段 85%~96%"},
    "湖北": {"城市": "武汉", "在职": 0.86, "退休": 0.888, "ret_est": False,
             "起付": 800, "封顶": 240000, "备注": ""},
    "湖南": {"城市": "长沙", "在职": 0.85, "退休": 0.87, "ret_est": False,
             "起付": 1100, "封顶": 150000, "备注": ""},
    "河南": {"城市": "郑州", "在职": 0.89, "退休": 0.94, "ret_est": False,
             "起付": 900, "封顶": 550000, "备注": "15 万基本+40 万补充"},
    "江西": {"城市": "南昌", "在职": 0.85, "退休": 0.85, "ret_est": False,
             "起付": 800, "封顶": 600000, "备注": "退休同在职"},
    "安徽": {"城市": "合肥", "在职": 0.90, "退休": 0.95, "ret_est": False,
             "起付": 600, "封顶": 300000, "备注": "含大病"},
    "四川": {"城市": "成都", "在职": 0.85, "退休": None, "ret_est": True,
             "起付": 800, "封顶": 580000, "备注": "按年龄递增"},
    "贵州": {"城市": "贵阳", "在职": 0.78, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
    "云南": {"城市": "昆明", "在职": 0.75, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
    "河北": {"城市": "石家庄", "在职": 0.78, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
    "山西": {"城市": "太原", "在职": 0.75, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
    "内蒙古": {"城市": "呼和浩特", "在职": 0.78, "退休": None, "ret_est": True,
               "起付": None, "封顶": None, "备注": "估算"},
    "辽宁": {"城市": "沈阳", "在职": 0.88, "退休": 0.91, "ret_est": False,
             "起付": 600, "封顶": 550000, "备注": "15 万+大额补助"},
    "吉林": {"城市": "长春", "在职": 0.75, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
    "黑龙江": {"城市": "哈尔滨", "在职": 0.75, "退休": None, "ret_est": True,
               "起付": None, "封顶": None, "备注": "估算"},
    "陕西": {"城市": "西安", "在职": 0.88, "退休": 0.91, "ret_est": False,
             "起付": 650, "封顶": 400000, "备注": "分段"},
    "甘肃": {"城市": "兰州", "在职": 0.75, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
    "青海": {"城市": "西宁", "在职": 0.78, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
    "宁夏": {"城市": "银川", "在职": 0.78, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
    "新疆": {"城市": "乌鲁木齐", "在职": 0.75, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
    "广西": {"城市": "南宁", "在职": 0.75, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
    "海南": {"城市": "海口", "在职": 0.78, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
    "西藏": {"城市": "拉萨", "在职": 0.80, "退休": None, "ret_est": True,
             "起付": None, "封顶": None, "备注": "估算"},
}
assert len(EMPLOYEE_INPATIENT) == 31, f"职工住院应 31 省，实际 {len(EMPLOYEE_INPATIENT)}"

# ============================================================
# 2. 居民医保住院（按城市等级 6 档）
# ============================================================
RESIDENT_INPATIENT = {
    "一线":   {"报销比": (0.65, 0.75), "起付": (600, 1000), "封顶": (400000, 500000)},
    "新一线": {"报销比": (0.60, 0.70), "起付": (500, 800),  "封顶": (300000, 450000)},
    "二线":   {"报销比": (0.60, 0.68), "起付": (400, 700),  "封顶": (250000, 400000)},
    "三线":   {"报销比": (0.58, 0.65), "起付": (300, 600),  "封顶": (200000, 350000)},
    "四线":   {"报销比": (0.55, 0.63), "起付": (200, 500),  "封顶": (150000, 300000)},
    "五线":   {"报销比": (0.50, 0.60), "起付": (150, 400),  "封顶": (100000, 250000)},
}

# ============================================================
# 3. 大病保险（7 省 + 全国分段）
# ============================================================
BIGILLNESS_DEFAULT_TIERS = [
    {"区间": "起付线~5万", "比例": 0.60},
    {"区间": "5~10万",     "比例": 0.65},
    {"区间": "10~20万",    "比例": 0.75},
    {"区间": "20万以上",   "比例": 0.80},
]
BIGILLNESS = {
    "安徽":   {"起付线": 15000, "封顶": 300000, "分段": BIGILLNESS_DEFAULT_TIERS},
    "北京":   {"起付线": 39000, "封顶": None,   "分段": None, "备注": "起付与收入挂钩，不设封顶"},
    "山西":   {"起付线": 10000, "封顶": 400000, "分段": BIGILLNESS_DEFAULT_TIERS},
    "黑龙江": {"起付线": None,  "封顶": 500000, "分段": BIGILLNESS_DEFAULT_TIERS},
    "青海":   {"起付线": 12000, "封顶": None,   "分段": None, "备注": "不设封顶"},
    "河南":   {"起付线": 15000, "封顶": 400000, "分段": BIGILLNESS_DEFAULT_TIERS},
    "重庆":   {"起付线": 18800, "封顶": 200000, "分段": BIGILLNESS_DEFAULT_TIERS},
}
BIGILLNESS_DEDUCTIBLE_RANGE = (12000, 20000)

# ============================================================
# 4. 规则常量
# ============================================================
REMOTE_DROP = {
    "filed":   0.10,   # 异地备案：降 ≤10 个百分点
    "unfiled": 0.20,   # 未备案：降 ≤20 个百分点
}
REMOTE_PRINCIPLE = "就医地目录，参保地政策"

CHRONIC_DISEASE_RATIO = {
    "门诊慢性病": {"比例": (0.60, 0.80), "常见病": ["高血压", "糖尿病", "冠心病", "脑卒中", "慢阻肺", "哮喘"]},
    "门诊特殊病": {"比例": "参照住院", "常见病": ["恶性肿瘤放化疗", "尿毒症透析", "器官移植抗排异"]},
}
CHRONIC_MUST_INCLUDE = ["高血压", "糖尿病"]

DRUG_CATEGORY = {
    "甲类": {"自付": 0.00, "规则": "100% 纳入报销基数"},
    "乙类": {"自付": (0.05, 0.20), "规则": "先自付 5~20%，剩余纳入报销"},
    "谈判药": {"自付": 0.20, "规则": "乙类管理，肿瘤药通常先自付 20%"},
    "丙类": {"自付": 1.00, "规则": "全部自费"},
}
DRUG_NOT_COVERED = ["营养滋补品/保健品", "美容整形/减肥", "特需/VIP 病房", "部分高端进口药（丙类）", "境外医疗"]

DRG_NOTE = ("DRG/DIP 改革后：次均住院总费用降 9~12%、药费降 13.7~18.9%；"
            "但检查费反升 4.17%、患者自费比例每月升约 0.82%。"
            "标准化治疗的普通患者整体受益；需进口药/创新疗法者可能受限。")

# ============================================================
# 5. 城市等级 fallback（无精确数据城市估算）
# ============================================================
EMPLOYEE_TIER_FALLBACK = {
    "一线":   {"报销比": (0.80, 0.85), "起付": (1300, 1500), "封顶": (500000, 600000)},
    "新一线": {"报销比": (0.75, 0.82), "起付": (800, 1000),  "封顶": (350000, 600000)},
    "二线":   {"报销比": (0.72, 0.80), "起付": (600, 800),   "封顶": (300000, 500000)},
    "三线":   {"报销比": (0.70, 0.78), "起付": (500, 700),   "封顶": (250000, 400000)},
    "四线":   {"报销比": (0.65, 0.75), "起付": (400, 600),   "封顶": (200000, 350000)},
    "五线":   {"报销比": (0.60, 0.72), "起付": (300, 500),   "封顶": (150000, 300000)},
}


# ============================================================
# 工具函数
# ============================================================
def _resolve_province(city):
    """城市 → 省名（查职工住院表用，深圳归广东）。"""
    if city in EMPLOYEE_INPATIENT:
        return city
    prov = R.CITY_TO_PROVINCE.get(city)
    return _PROVINCE_ALIAS.get(prov, prov)


def get_employee_rate(city):
    """查城市职工住院（三级）报销。返回 (在职比, 退休比, 起付, 封顶, 说明, 是否估算)。"""
    prov = _resolve_province(city)
    if prov in EMPLOYEE_INPATIENT:
        d = EMPLOYEE_INPATIENT[prov]
        emp = d["在职"]
        ret = d["退休"] if d["退休"] is not None else min(emp + 0.04, 0.97)
        return emp, ret, d["起付"], d["封顶"], f"{prov}（{d['城市']}）标准", d.get("ret_est", False)
    tier = D.city_to_tier(city)
    if tier:
        fb = EMPLOYEE_TIER_FALLBACK[tier]
        emp = sum(fb["报销比"]) / 2
        ret = emp + 0.04
        ded = sum(fb["起付"]) / 2
        cap = fb["封顶"][1] or fb["封顶"][0]
        return emp, ret, ded, cap, f"{tier} 城市估算（{city}）", True
    return None, None, None, None, "未找到该地数据", True


def estimate_inpatient(city, identity="职工", cost=50000, remote="none", retired=False):
    """估算住院报销（基本医保 + 大病 + 异地调整）。

    identity: 职工/居民；cost: 住院总费用；remote: none/filed(备案)/unfiled(未备案)；retired: 是否退休。
    """
    if cost <= 0:
        return {"error": "住院费用需大于 0。"}
    if identity == "职工":
        emp, ret, ded, cap, note, est = get_employee_rate(city)
        if emp is None:
            return {"error": note}
        rate = ret if retired else emp
    else:  # 居民
        tier = D.city_to_tier(city) or "三线"
        fb = RESIDENT_INPATIENT.get(tier, RESIDENT_INPATIENT["三线"])
        rate = sum(fb["报销比"]) / 2
        ded = sum(fb["起付"]) / 2
        cap = sum(fb["封顶"]) / 2
        note = f"{tier} 城市居民估算"
        est = True

    remote_note = ""
    if remote in REMOTE_DROP:
        rate = max(rate - REMOTE_DROP[remote], 0.30)
        remote_note = f"异地{'已备案降 10' if remote == 'filed' else '未备案降 20'} 个百分点；"

    deductible = ded or 800
    cap_line = cap or 99999999
    base_pay = min(max(cost - deductible, 0) * rate, cap_line)

    # 大病：基本医保后自付超起付触发（简化按首段比例）
    big_pay = 0.0
    big_note = ""
    self_after_base = cost - base_pay
    prov = _resolve_province(city)
    big = BIGILLNESS.get(prov, {})
    big_ded = big.get("起付线") or BIGILLNESS_DEDUCTIBLE_RANGE[0]
    if self_after_base > big_ded:
        tiers = big.get("分段") or BIGILLNESS_DEFAULT_TIERS
        ratio = tiers[0]["比例"]
        big_pay = min((self_after_base - big_ded) * ratio, big.get("封顶") or 400000)
        big_note = (f"基本报销后自付 {self_after_base:,.0f} 超大病起付线 {big_ded:,.0f}，"
                    f"大病再报约 {big_pay:,.0f}（按首段 {ratio*100:.0f}% 估，精确分段以结算为准）。\n")

    total_pay = base_pay + big_pay
    self_final = cost - total_pay
    cap_str = f"{cap:,.0f}" if cap else "无上限"
    text = (
        f"假设 {city} {identity}{'退休' if retired else ''}，三级医院住院 {cost:,.0f} 元：\n"
        f"· 报销比约 {rate*100:.0f}%，起付线 {deductible:,.0f}，封顶 {cap_str}。\n"
        f"{remote_note}"
        f"· 基本医保报销约 {base_pay:,.0f} 元。\n"
        f"{big_note}"
        f"→ 合计报销约 {total_pay:,.0f} 元（约 {total_pay/cost*100:.0f}%），个人自付约 {self_final:,.0f} 元。\n"
        f"· DRG 影响：{DRG_NOTE}"
    )
    text += ("\n⚠️ 粗算：未含乙类药先行自付、各地起付线差异、大病分段累进等细节；"
             "实际以就诊医院结算为准，可用「问 AI」查精确。")
    if est:
        text += f"\n（{note}，数据为估算）"
    return {"base_pay": base_pay, "big_pay": big_pay, "total_pay": total_pay,
            "self_pay": self_final, "rate": rate, "note": text, "estimated": est}


# ============================================================
# 自检
# ============================================================
if __name__ == "__main__":
    print(f"EMPLOYEE_INPATIENT 省份数: {len(EMPLOYEE_INPATIENT)}")
    for city in ["广州", "深圳", "上海", "成都", "某未知城"]:
        emp, ret, ded, cap, note, est = get_employee_rate(city)
        print(f"  {city}: 在职{emp}, 起付{ded}, 封顶{cap}（{note}{'，估' if est else ''}）")
    print("\n=== 住院估算（广州职工三级 5 万）===")
    r = estimate_inpatient("广州", "职工", 50000)
    print(r["note"][:200])
