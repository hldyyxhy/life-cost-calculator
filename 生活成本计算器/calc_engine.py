# -*- coding: utf-8 -*-
"""
calc_engine.py —— 生活成本计算器的业务计算逻辑（纯函数，不依赖 tkinter）

设计目的：
    把"怎么算"和"怎么显示"彻底分开。本模块只负责：根据输入算出结构化结果(dict)，
    GUI 层只负责把结果渲染出来。这样计算逻辑可以用 unittest 单独验证。

两个核心函数：
    compute_life_cost()           —— 计算器1：从生到死的一生成本
    compute_current_situation()   —— 计算器2：当前生存境况

所有金额单位：人民币元。返回结构里金额保留浮点（内部精度），由 GUI 层负责四舍五入展示。
"""

import cost_data as D

# 养老方式：GUI 友好短名 -> cost_data 里的 key
CARE_MODE_MAP = {
    "居家养老": "居家养老（基本生活费）",
    "普惠养老机构": "普惠养老机构",
    "中高端养老机构": "中高端养老机构",
}


# ============================================================
# 一、计算器1：从生到死的一生成本
# ============================================================

def compute_life_cost(tier, level, birth_mode="公立·顺产", care_mode="居家养老",
                      uni_type="公办", graduate=False, retire_age=60,
                      purchase_mode="贷款"):
    """
    计算一个人从怀孕到死亡的完整生命周期成本。

    参数:
        tier:          城市等级（一线/新一线/二线/三线/四线/五线）
        level:         养育档位（普惠/中产/高端）
        birth_mode:    分娩方式（公立·顺产/公立·剖腹产/私立·顺产/私立·剖腹产）
        care_mode:     养老方式（居家养老/普惠养老机构/中高端养老机构）
        uni_type:      大学类型（公办/民办）
        graduate:      是否读研（True 则计入22-23岁硕士2年）
        retire_age:    退休年龄（55/60/65）
        purchase_mode: 购房方式（贷款=首付 / 全款=总价）

    返回 dict:
        rows:             逐行明细 [{stage, item, amount, note, is_income}, ...]
        stage_subtotals:  六大阶段小计 [{stage, amount, pct}, ...]
        grand_total:       净一生成本（元）
        gross_cost:        总支出（元，不含养老金）
        pension_offset:    养老金收入（元）
        assumptions:       估算假设说明 [str, ...]
    """
    cf = D.city_factor(tier)          # 城市系数
    rf = D.raise_factor(level)        # 养育档位系数
    high = (level == "高端")           # 高端档对教育/月子类额外加权

    rows = []          # 逐行明细
    assumptions = []   # 估算假设

    def add(stage, item, amount, note="", is_income=False):
        rows.append({"stage": stage, "item": item,
                     "amount": round(amount), "note": note,
                     "is_income": is_income})

    # ---------- 阶段1：孕育与生育 ----------
    for item in D.PREGNANCY_STAGE:
        base = item["base"]
        # 月嫂/月子中心项：高端档额外加权
        if item.get("moon_factor") and high:
            amount = base * cf * rf * D.MOON_HIGH_BOOST
        else:
            amount = base * cf * rf
        add("一、孕育与生育", item["key"], amount, item["note"])

    # 分娩方式：按 DELIVERY_MODES 倍数调整（基准为公立顺产自费）
    dm = D.DELIVERY_MODES.get(birth_mode, D.DELIVERY_MODES["公立·顺产"])
    for r in rows:
        if r["item"].startswith("分娩"):
            r["amount"] = round(r["amount"] * dm["mult"])
            r["note"] = dm["note"]
            r["item"] = f"分娩（{birth_mode}）"
            break

    # ---------- 阶段2：0-22岁逐年养育 + 教育额外投入 ----------
    uni_factor = D.UNI_TYPE_FACTOR.get(uni_type, 1.0)
    for age in sorted(D.AGE_STAGE):
        info = D.AGE_STAGE[age]
        # 硕士阶段：仅当选择读研时计入
        if info.get("grad") and not graduate:
            continue
        stage_name = info["stage"]
        # 大学/硕士阶段按公办/民办系数
        if stage_name in ("大学", "硕士"):
            base_cost = info["base"] * cf * rf * uni_factor
        else:
            base_cost = info["base"] * cf * rf
        # 该学段教育额外投入（课外/兴趣）
        edu = D.EDUCATION_EXTRA.get(stage_name, {"base": 0, "note": ""})
        edu_base = edu["base"]
        if edu_base > 0:
            edu_boost = D.EDUCATION_HIGH_BOOST if high else 1.0
            # 教育投入：普惠默认少量(已在base里偏低)，中产/高端用档位系数+高端加权
            edu_cost = edu_base * cf * rf * edu_boost if level != "普惠" else edu_base * cf * 0.5
        else:
            edu_cost = 0

        total_year = base_cost + edu_cost
        note = info["label"]
        if edu_cost > 0 and level != "普惠":
            note += f"（含课外/兴趣约 {edu_cost:,.0f}）"
        add(f"二、{stage_name}（{info['label']}）", f"{age}岁当年",
            total_year, note)

    # ---------- 阶段3：结婚 ----------
    cai = D.MARRIAGE_COST["彩礼"][tier]   # 彩礼不套系数，按城市取值
    add("三、结婚", "彩礼", cai, D.MARRIAGE_COST["彩礼"]["note"])
    wedding = D.MARRIAGE_COST["婚礼"]["base"] * cf
    add("三、结婚", "婚礼婚宴婚庆", wedding, D.MARRIAGE_COST["婚礼"]["note"])
    # 购房方式：贷款=首付（月供另计），全款=总价
    hp = D.HOUSE_PURCHASE[tier]
    if purchase_mode == "全款":
        add("三、结婚", "婚房（全款）", hp["total"],
            f"90㎡全款总价约 {hp['total']/10000:.0f} 万（{hp['total']:,.0f} 元）")
    else:
        house_dp = D.MARRIAGE_COST["婚房首付"]["base"] * cf
        add("三、结婚", "婚房首付", house_dp,
            f"{D.MARRIAGE_COST['婚房首付']['note']}；月供约 {hp['monthly_loan']:,.0f} 元/月×30年（已近似含于成年居住成本）")

    # ---------- 阶段4：成年工作期持续成本（22/24岁~退休） ----------
    # 读研则工作从24岁起算
    work_start = 24 if graduate else 22
    work_years = retire_age - work_start
    months = work_years * 12
    lf = D.ADULT_LIVING_FACTOR.get(level, 1.0)   # 成年生活档次系数
    # (a) 社保 / 医疗（按典型工资累计）；个税按该城市典型工资实算
    typical_wage = D.TYPICAL_WAGE.get(tier, 5000)
    typical_social = D.SOCIAL_INSURANCE_MONTHLY.get(tier, 580)
    for item in D.ADULT_ANNUAL:
        if "个人所得税" in item["key"]:
            # 个税基于该城市典型月薪实算（普通劳动者多在起征点附近，常为0）
            taxable = max(typical_wage - typical_social - D.TAX_THRESHOLD, 0)
            month_tax, _, _ = D.calc_personal_income_tax(taxable)
            amount = month_tax * 12 * work_years
            note = (f"按{tier}典型月薪 {typical_wage:,} 元实算"
                    f"（应纳税所得 {taxable:,}，月税 {month_tax:.0f}），累计{work_years}年")
        else:
            amount = item["base"] * cf * work_years
            note = f"{item['note']}（按工作{work_years}年累计）"
        add("四、成年工作期", f"{item['key']}（累计{work_years}年）", amount, note)
    # (b) 成年人日常生存成本（吃住行用）——按租房/等额居住估算
    living_items = [
        ("住房与水电（合租/等额居住）",
         D.HOUSING["合租单间"]["base"] + D.HOUSING["含水电物业网费"]["base"]),
        ("饮食", D.FOOD["base"]),
        ("交通（公交地铁）", D.TRANSPORT["公交地铁通勤"]["base"]),
        ("通讯+日用品+衣物",
         sum(v["base"] for v in D.OTHER_MONTHLY.values())),
    ]
    for name, base in living_items:
        amt = base * cf * lf * months
        add("四、成年工作期", f"{name}（累计{work_years}年）", amt,
            f"月约 {base*cf*lf:,.0f} 元 ×12 ×{work_years}年")

    # ---------- 阶段5：养老（退休~死亡） ----------
    # 养老年限按预期寿命反推（早退休 = 养老期更长）
    years = D.LIFE_EXPECTANCY - retire_age
    pension = D.RETIREMENT["pension_monthly"][tier] * 12 * years
    care_table = D.RETIREMENT["care_monthly"][CARE_MODE_MAP[care_mode]]
    care = care_table[tier] * 12 * years
    # 退休后医疗（用 base_old，老年慢性病支出高）
    medical_old = 0
    for item in D.ADULT_ANNUAL:
        if "医疗" in item["key"]:
            medical_old = item.get("base_old", item["base"]) * cf * years
            break
    add("五、养老期", f"养老金收入（{years}年）", -pension,
        f"企业职工养老金月约{D.RETIREMENT['pension_monthly'][tier]:,}元，作为退休后收入。",
        is_income=True)
    add("五、养老期", f"{care_mode}支出（{years}年）", care,
        f"月约{care_table[tier]:,}元 ×12 ×{years}年")
    add("五、养老期", f"老年医疗保健（{years}年）", medical_old, "老年慢性病支出显著高于均值")

    # ---------- 阶段6：丧葬 ----------
    funeral = D.FUNERAL[tier]
    add("六、丧葬", "殡葬（含墓地）", funeral, D.FUNERAL["note"])

    # ---------- 汇总 ----------
    # 养老金等收入项单独拎出；占比只统计支出，避免出现负值/负占比。
    gross_cost = sum(r["amount"] for r in rows if not r.get("is_income"))
    pension_offset = sum(-r["amount"] for r in rows if r.get("is_income"))  # 正数
    grand_total = gross_cost - pension_offset   # 净一生成本

    # 按阶段前缀聚合支出（排除收入项）
    stage_subtotals = []
    education_total = 0
    other_subtotals = {}
    for r in rows:
        if r.get("is_income"):
            continue
        st = r["stage"]
        if st.startswith("二、"):
            education_total += r["amount"]
        else:
            other_subtotals[st] = other_subtotals.get(st, 0) + r["amount"]

    # 组装阶段小计（顺序：孕育→养育→结婚→工作→养老→丧葬），占比基于总支出
    ordered = [
        ("一、孕育与生育", other_subtotals.get("一、孕育与生育", 0)),
        ("二、0-22岁养育（含教育）", education_total),
        ("三、结婚（彩礼+婚礼+婚房首付）", other_subtotals.get("三、结婚", 0)),
        ("四、成年工作期（生存+社保+个税+医疗）", other_subtotals.get("四、成年工作期", 0)),
        ("五、养老期（养老+老年医疗）", other_subtotals.get("五、养老期", 0)),
        ("六、丧葬", other_subtotals.get("六、丧葬", 0)),
    ]
    for name, amt in ordered:
        pct = (amt / gross_cost * 100) if gross_cost else 0
        stage_subtotals.append({"stage": name, "amount": round(amt), "pct": round(pct, 1)})

    # 估算假设
    edu_desc = f"大学{uni_type}"
    if graduate:
        edu_desc += " + 硕士（22-23岁）"
    assumptions = [
        f"城市成本系数：{tier} = {cf}（以三线/全国城镇平均=1.0）",
        f"养育档位系数：{level} = {rf}（普惠=1.0）",
        f"分娩方式：{birth_mode}",
        f"教育：{edu_desc}",
        f"购房方式：{purchase_mode}（{'首付20%，月供另计' if purchase_mode=='贷款' else '全款总价'}）",
        f"养老方式：{care_mode}，{retire_age}岁退休、预期寿命{D.LIFE_EXPECTANCY}岁（养老{years}年）",
        f"工作年限：{work_start}~{retire_age}岁，共{work_years}年",
        "养老金按企业职工中位数估算（机关事业更高、城乡居民更低），作为退休后收入，已从净成本中抵减。",
        "未成年阶段成本含食宿日用+教育；工作期含独立生活的吃住行用+社保+个税+医疗。",
        "未计入失业、大病、意外、通货膨胀等风险与时间价值。",
        "所有数字为公开调研的中值估算，个体实际可能差异很大，仅供了解量级。",
    ]

    return {
        "rows": rows,
        "stage_subtotals": stage_subtotals,
        "grand_total": round(grand_total),       # 净一生成本 = 总支出 - 养老金
        "gross_cost": round(gross_cost),          # 总支出（不含养老金抵减）
        "pension_offset": round(pension_offset),  # 养老金收入（抵减额）
        "assumptions": assumptions,
    }


# ============================================================
# 二、计算器2：当前生存境况
# ============================================================

def compute_current_situation(age, wage_pretax, tier, housing, food_level,
                              has_car=False, insurance_mode="在职（单位缴）",
                              num_children=0, children_by_age=None,
                              support_elderly=False, has_housing_deduction=False,
                              has_continuing_education=False,
                              support_family_monthly=0, overrides=None):
    """
    计算当前月度生存成本、到手收入与结余。

    参数:
        age:                 年龄
        wage_pretax:         税前月薪（元）
        tier:                城市等级
        housing:             住房方式（合租单间/一居室整租/已购房（还月供）/与父母同住（免租））
        food_level:          饮食档次（节俭/普通/宽裕）
        has_car:             是否养车
        insurance_mode:      社保模式（在职（单位缴）/灵活就业（全自缴）/不缴社保）
        num_children:        子女数量
        children_by_age:     子女按年龄段计数 {段: 人数}（空则用 num_children 兜底）
        support_elderly:     是否赡养老人
        has_housing_deduction: 是否有住房租金/贷款利息专项扣除
        has_continuing_education: 是否有继续教育专项扣除（+400元/月）
        support_family_monthly: 每月给老家生活费（元）

    返回 dict:
        cost_rows:     月度成本明细 [{item, amount, note}]
        cost_total:    月度生存成本合计
        social_ins:    五险一金月缴
        tax:           月个税
        tax_rate:      税率
        income_net:    月到手收入
        surplus:       月结余（正=结余，负=缺口）
        surplus_rate:  结余率（surplus/income_net）
        house_saving_years: 攒首付年数（None 若无结余）
        interpretation: 白话解读
        assumptions:   估算说明
    """
    cf = D.city_factor(tier)
    cost_rows = []
    breakdown = {}  # 类别 -> 月额（结构化，供 UI 直接读，避免按中文串匹配）

    def add_cost(item, amount, note="", category=None):
        cost_rows.append({"item": item, "amount": round(amount), "note": note,
                          "_cat": category})
        if category:
            breakdown[category] = breakdown.get(category, 0) + round(amount)

    # ---------- 月度生存成本 ----------
    # 住房
    if housing == "已购房（还月供）":
        house_cost = D.HOUSE_PURCHASE[tier]["monthly_loan"]
        add_cost("住房（房贷月供）", house_cost, "90㎡贷款70%、30年、约3.05%利率估算", "住房")
        utility = D.HOUSING["含水电物业网费"]["base"] * cf
    elif housing == "与父母同住（免租）":
        house_cost = 0
        add_cost("住房（与父母同住）", 0, "免房租；水电与父母分摊", "住房")
        utility = D.HOUSING["含水电物业网费"]["base"] * cf * 0.5   # 水电减半
    else:
        house_cost = D.HOUSING[housing]["base"] * cf
        add_cost(f"住房（{housing}）", house_cost, D.HOUSING[housing]["note"], "住房")
        utility = D.HOUSING["含水电物业网费"]["base"] * cf
    add_cost("水电燃气物业宽带", utility, D.HOUSING["含水电物业网费"]["note"], "住房")

    # 饮食
    food = D.FOOD["base"] * cf * D.LIFESTYLE_FACTOR[food_level]
    add_cost(f"饮食（{food_level}档）", food,
             f"三线普通基准{D.FOOD['base']}×城市{cf}×{food_level}系数{D.LIFESTYLE_FACTOR[food_level]}",
             "饮食")

    # 交通
    if has_car:
        transport = D.TRANSPORT["养车"]["base"] * cf
        add_cost("交通（养车）", transport, D.TRANSPORT["养车"]["note"], "交通")
    else:
        transport = D.TRANSPORT["公交地铁通勤"]["base"] * cf
        add_cost("交通（公交地铁）", transport, D.TRANSPORT["公交地铁通勤"]["note"], "交通")

    # 通讯、日用、衣物
    other_total = sum(v["base"] for v in D.OTHER_MONTHLY.values()) * cf
    for key, info in D.OTHER_MONTHLY.items():
        add_cost(key, info["base"] * cf, "", "通讯日用")
    breakdown["通讯日用"] = round(other_total)  # 合并为一项

    # 社保（作为成本计入）
    if insurance_mode == "在职（单位缴）":
        social_ins = D.SOCIAL_INSURANCE_MONTHLY[tier]
    elif insurance_mode == "灵活就业（全自缴）":
        social_ins = D.FREELANCE_INSURANCE_MONTHLY[tier]
    else:
        social_ins = 0
    if social_ins > 0:
        note_map = {
            "在职（单位缴）": D.SOCIAL_INSURANCE_MONTHLY["note"],
            "灵活就业（全自缴）": D.FREELANCE_INSURANCE_MONTHLY["note"],
        }
        add_cost(f"社保公积金（{insurance_mode}）", social_ins, note_map[insurance_mode], "社保")

    # 给老家生活费（新增，打工人的真实负担）
    if support_family_monthly > 0:
        add_cost("给老家生活费", support_family_monthly,
                 f"在外务工给父母/家庭的生活费，月 {support_family_monthly:,.0f} 元", "给老家")

    # —— 用户实际值覆盖估算（清楚自己情况的人可改；overrides: {类别: 实际月额}）——
    if overrides:
        for cat, val in overrides.items():
            if val is None or cat not in breakdown:
                continue
            cost_rows = [r for r in cost_rows if r.get("_cat") != cat]
            cost_rows.append({"item": f"{cat}（按实际）", "amount": round(val),
                              "note": "你填的实际金额", "_cat": cat})
            breakdown[cat] = round(val)

    cost_total = sum(r["amount"] for r in cost_rows)

    # ---------- 收入端：个税 ----------
    # 专项附加扣除
    special = 0
    special_detail = []
    # 子女专项附加扣除：按各年龄段分别累加（3岁以下→婴幼儿照护，其余→子女教育）
    for seg, n in _normalize_children(children_by_age, num_children).items():
        dedu_key = ("3岁以下婴幼儿照护" if seg.startswith("3岁以下")
                    else "子女教育（3岁至博士）")
        amt = D.SPECIAL_DEDUCTIONS[dedu_key]["amount"] * n
        special += amt
        special_detail.append(f"{dedu_key} {n}孩 = {amt:,}")
    if support_elderly:
        amt = D.SPECIAL_DEDUCTIONS["赡养老人"]["amount"]
        special += amt
        special_detail.append(f"赡养老人 {amt:,}")
    if has_continuing_education:
        amt = D.SPECIAL_DEDUCTIONS["继续教育"]["amount"]
        special += amt
        special_detail.append(f"继续教育 {amt:,}")
    if has_housing_deduction:
        # 简化：按城市规模选租金档；已购房用贷款利息
        if housing == "已购房（还月供）":
            amt = D.SPECIAL_DEDUCTIONS["住房贷款利息"]["amount"]
            name = "住房贷款利息"
        elif tier in ("一线", "新一线", "二线"):
            amt = D.SPECIAL_DEDUCTIONS["住房租金（直辖市/省会）"]["amount"]
            name = "住房租金"
        else:
            amt = D.SPECIAL_DEDUCTIONS["住房租金（≤100万人口城市）"]["amount"]
            name = "住房租金"
        special += amt
        special_detail.append(f"{name} {amt:,}")

    taxable = wage_pretax - social_ins - D.TAX_THRESHOLD - special
    tax, tax_rate, _ = D.calc_personal_income_tax(max(taxable, 0))
    income_net = wage_pretax - social_ins - tax
    surplus = income_net - cost_total

    # 结余率
    surplus_rate = (surplus / income_net * 100) if income_net > 0 else 0

    # 买房攒首付年限
    house_saving_years = None
    if surplus > 0:
        hp = D.HOUSE_PURCHASE[tier]
        downpayment = hp["downpayment"]
        annual_surplus = surplus * 12
        if annual_surplus > 0:
            house_saving_years = downpayment / annual_surplus

    # 城市生存底线（计算一次，解读与页面共用，避免重复算）
    survival_baseline = _survival_baseline(tier, insurance_mode)

    # ---------- 白话解读 ----------
    interpretation = _build_interpretation(
        age, wage_pretax, tier, cost_total, social_ins, tax,
        income_net, surplus, surplus_rate, house_saving_years, survival_baseline,
        special_detail, num_children, food_level,
        insurance_mode, children_by_age, support_family_monthly
    )

    assumptions = [
        f"城市成本系数：{tier} = {cf}（以三线/全国城镇平均=1.0）",
        f"社保：{insurance_mode}" + (f"，月缴 {social_ins:,} 元" if social_ins else "，未计入"),
        f"个税：起征点5,000元/月" + (f" + 专项附加扣除合计 {special:,} 元" if special else "，无专项附加扣除"),
        f"当地最低工资约 {D.MIN_WAGE[tier]:,} 元/月，城镇私营单位典型月薪约 {D.TYPICAL_WAGE[tier]:,} 元。",
        "生存成本仅含基本吃住行+社保，未含人情、娱乐、储蓄、意外、大病等。",
    ]

    return {
        "cost_rows": cost_rows,
        "breakdown": breakdown,
        "cost_total": round(cost_total),
        "survival_baseline": survival_baseline,
        "social_ins": round(social_ins),
        "tax": round(tax),
        "tax_rate": tax_rate,
        "income_net": round(income_net),
        "surplus": round(surplus),
        "surplus_rate": round(surplus_rate, 1),
        "house_saving_years": round(house_saving_years, 1) if house_saving_years else None,
        "special_total": special,
        "interpretation": interpretation,
        "assumptions": assumptions,
    }


def _normalize_children(children_by_age, num_children=0):
    """把子女段计数规整成 {段: 人数(>0)}；为空且 num_children>0 时兜底全归'中小学'。"""
    kids = {seg: n for seg, n in (children_by_age or {}).items() if n and n > 0}
    if not kids and num_children and num_children > 0:
        kids = {"中小学（6-18岁）": num_children}
    return kids


def _build_interpretation(age, wage, tier, cost_total, social_ins, tax,
                          income_net, surplus, surplus_rate, house_saving_years, survival_baseline,
                          special_detail, num_children, food_level,
                          insurance_mode, children_by_age, support_family_monthly=0):
    """生成增强版白话解读段落（survival_baseline 由调用方计算后传入，避免重复算）"""
    cf = D.city_factor(tier)
    lines = []
    lines.append(f"你 {age} 岁，在【{tier}】城市，税前月薪 {wage:,.0f} 元。")
    lines.append(f"扣除五险一金 {social_ins:,.0f} 元、个税 {tax:,.0f} 元后，每月到手约 "
                 f"{income_net:,.0f} 元。")
    if special_detail:
        lines.append("（个税已扣除专项附加：" + "；".join(special_detail) + "）")

    # 不缴社保的风险警告
    if insurance_mode == "不缴社保":
        lines.append("")
        lines.append("⚠️ 你选择了【不缴社保】：眼下每月到手看似多了，但这意味着")
        lines.append("   你未来【没有养老金、看病不能医保报销】，生病和养老的全部费用都要自担。")
        lines.append("   一次大病就可能耗尽多年积蓄，请务必重视这个隐患。")

    lines.append("")
    lines.append(f"你的【基本生存成本】约 {cost_total:,.0f} 元/月"
                 f"（含住房、{food_level}饮食、交通、通讯日用、社保"
                 + (f"、给老家生活费" if support_family_monthly > 0 else "")
                 + "）。")

    # 结余率分析
    lines.append("")
    lines.append(f"👉 每月到手 {income_net:,.0f} 元 - 生存成本 {cost_total:,.0f} 元"
                 f" = 结余 {surplus:+,.0f} 元")
    if surplus >= 0:
        lines.append(f"   结余率 {surplus_rate:.0f}%"
                     + ("（✅ 超过20%健康线）" if surplus_rate >= 20
                        else "（⚠️ 建议至少达20%以备急用）" if surplus_rate >= 10
                        else "（🔴 低于10%，抗风险能力极弱）"))
    else:
        lines.append(f"   已入不敷出，每月缺口约 {-surplus:,.0f} 元。")

    # 城市生存底线（节俭版最低成本，由调用方传入）
    lines.append("")
    lines.append(f"█ 城市生存底线")
    lines.append(f"   在【{tier}】如果极度节俭（合租+自己做饭+公交），"
                 f"每月最低约 {survival_baseline:,} 元能活。")
    if surplus > 0 and survival_baseline > 0:
        # 月结余 ÷ 月底线开支 = 每攒一个月结余，够按底线生活标准撑多久（是比值，不是绝对月数）
        ratio = surplus / survival_baseline
        lines.append(f"   你每月结余 {surplus:,.0f} 元 ÷ 底线月开支 {survival_baseline:,} 元 ≈ {ratio:.1f}："
                     f"每攒下一个月的结余，够按底线生活标准撑约 {ratio:.1f} 个月。")

    # 购房年限
    if house_saving_years is not None and house_saving_years < 100:
        hp = D.HOUSE_PURCHASE[tier]
        lines.append("")
        lines.append(f"█ 攒够婚房首付（{hp['downpayment']/10000:.0f}万）需约 {house_saving_years:.0f} 年。")
        lines.append(f"   如果月结余增加 500 元，可缩短至 "
                     f"{hp['downpayment'] / ((surplus+500)*12):.0f} 年。")
    elif surplus > 0:
        lines.append("")
        lines.append("█ 按当前结余，攒首付几乎不可能（需要>100年）。")

    # 孩子抚养成本提示：按各年龄段分别累加
    kids = _normalize_children(children_by_age, num_children)
    if kids:
        total_kids = sum(kids.values())
        child_month = sum(D.CHILD_CARE_MONTHLY_BASE.get(seg, 1500) * cf * n
                          for seg, n in kids.items())
        seg_desc = "、".join(f"{seg}{n}人" for seg, n in kids.items())
        lines.append("")
        lines.append(f"█ 你有 {total_kids} 个孩子（{seg_desc}）：")
        lines.append(f"   孩子每月基本支出约 {child_month:,.0f} 元（不包含辅导班、兴趣班）。")
        real_surplus = surplus - child_month
        lines.append(f"   扣掉孩子抚养后，你每月真实可支配约 {real_surplus:+,.0f} 元"
                     f"（{'有结余' if real_surplus >= 0 else '已入不敷出'}）。")

    # 参考对比
    lines.append("")
    lines.append(f"█ 参考对比")
    lines.append(f"   当地最低工资    {D.MIN_WAGE[tier]:,} 元/月")
    lines.append(f"   城镇私营平均    {D.TYPICAL_WAGE[tier]:,} 元/月")
    lines.append(f"   全市房租中位    {D.HOUSING['合租单间']['base'] * cf * 1.5:,.0f} 元/月（合租估算）")
    lines.append(f"   你的到手收入    {income_net:,.0f} 元/月"
                 + (f"（高于平均 ✓）" if income_net > D.TYPICAL_WAGE[tier]
                    else f"（低于平均）"))

    return "\n".join(lines)


def _survival_baseline(tier, insurance_mode):
    """计算城市生存底线——极度节俭下的最低月度成本"""
    cf = D.city_factor(tier)
    total = 0
    # 合租最便宜
    total += D.HOUSING["合租单间"]["base"] * cf * 0.85  # 偏远地区更便宜
    # 水电减半
    total += D.HOUSING["含水电物业网费"]["base"] * cf * 0.7
    # 节俭饮食
    total += D.FOOD["base"] * cf * D.LIFESTYLE_FACTOR["节俭"]
    # 公交
    total += D.TRANSPORT["公交地铁通勤"]["base"] * cf
    # 通讯日用（减量）
    total += sum(v["base"] for v in D.OTHER_MONTHLY.values()) * cf * 0.8
    # 社保最低档
    if insurance_mode == "在职（单位缴）":
        total += D.SOCIAL_INSURANCE_MONTHLY[tier]
    elif insurance_mode == "灵活就业（全自缴）":
        total += D.FREELANCE_INSURANCE_MONTHLY[tier]
    return round(total)


def compute_survival_baseline(tier, insurance_mode="在职（单位缴）"):
    """计算城市生存底线（公开接口）"""
    return _survival_baseline(tier, insurance_mode)


def _estimate_target_wage(wage, current_tier, target_tier):
    """
    预估从 current_tier 移居 target_tier 后的工资。
    政策：按目标城市相对当前城市的典型工资水平「等比例缩放」，
    即保持你在本地的相对工资位置不变——
        目标工资 = 你的工资 × (目标城市典型工资 / 当前城市典型工资)
    这样升线（如三线→一线）会合理上浮，降线（一线→三线）会合理下调，
    避免出现「升线后工资不涨、但社保更高，导致末流城市到手反而更高」的失真。
    """
    cur_wage = D.TYPICAL_WAGE.get(current_tier, 5000)
    tgt_wage = D.TYPICAL_WAGE.get(target_tier, 5000)
    return wage * (tgt_wage / cur_wage) if cur_wage else wage


def compute_surplus(wage, tier, housing="合租单间", food_level="普通",
                    insurance_mode="在职（单位缴）"):
    """
    轻量计算：只算月结余（收入-生存成本）。
    用于里程碑页面等只需要一个数字、不需要完整解读的场景，避免为读 surplus
    而跑完整的 compute_current_situation（含逐项明细 + 整段解读字符串）。
    """
    return compute_current_situation(
        age=30, wage_pretax=wage, tier=tier, housing=housing,
        food_level=food_level, insurance_mode=insurance_mode,
    )["surplus"]


def compute_family_situation(self_result, partner_wage, tier,
                             partner_insurance="在职（单位缴）"):
    """
    双收入家庭结余（口径：伴侣净增收）。
    家庭结余 = 本人结余 + 伴侣净增收
        伴侣净增收 = 伴侣(税前 − 社保 − 个税) − 伴侣个人生活费
    住房/子女抚养/给老家等家庭共享成本只在 self_result 里算过一次，不重复。

    self_result: 本人侧 compute_current_situation() 的返回 dict
    partner_wage: 伴侣税前月薪；为 0 表示无伴侣，直接返回本人结余
    返回: {partner_income_net, partner_surplus, family_surplus, family_surplus_rate}
    """
    self_surplus = self_result["surplus"]
    self_income_net = self_result["income_net"]

    if not partner_wage or partner_wage <= 0:
        rate = (self_surplus / self_income_net * 100) if self_income_net > 0 else 0
        return {"partner_income_net": 0, "partner_surplus": 0,
                "family_surplus": round(self_surplus),
                "family_surplus_rate": round(rate, 1)}

    # 伴侣社保
    if partner_insurance == "在职（单位缴）":
        p_social = D.SOCIAL_INSURANCE_MONTHLY.get(tier, 0)
    elif partner_insurance == "灵活就业（全自缴）":
        p_social = D.FREELANCE_INSURANCE_MONTHLY.get(tier, 0)
    else:
        p_social = 0
    # 伴侣个税（简化：起征点 5000，无专项附加，因为专项已在本人侧算）
    p_taxable = max(partner_wage - p_social - D.TAX_THRESHOLD, 0)
    p_tax, _, _ = D.calc_personal_income_tax(p_taxable)
    p_income_net = partner_wage - p_social - p_tax
    # 伴侣个人生活费（按城市系数）
    p_personal = D.PARTNER_PERSONAL_MONTHLY * D.city_factor(tier)
    p_surplus = p_income_net - p_personal

    family = self_surplus + p_surplus
    family_income = self_income_net + p_income_net
    rate = (family / family_income * 100) if family_income > 0 else 0
    return {"partner_income_net": round(p_income_net),
            "partner_surplus": round(p_surplus),
            "family_surplus": round(family),
            "family_surplus_rate": round(rate, 1)}


def compute_risk_indicators(savings, survival_baseline):
    """
    抗风险指标。
    savings: 现有存款/应急金（元）
    survival_baseline: 城市生存底线（result["survival_baseline"]）
    返回: {unemployment_months, emergency_fund_low, emergency_fund_high,
           emergency_gap, severe_illness_risk}
    """
    savings = savings or 0
    baseline = survival_baseline or 1
    # 失业能撑几个月
    unemp = savings / baseline if baseline > 0 else 0
    # 建议应急金 3~6 个月底线
    fund_low = baseline * 3
    fund_high = baseline * 6
    # 应急金缺口（相对下限；负数=已充足）
    gap = fund_low - savings
    # 大病自付风险：一次重病自付约 5-10 万
    severe_low, severe_high = 50000, 100000
    if savings < severe_low:
        severe_risk = "high"     # 存款不足5万，大病风险高
    elif savings < severe_high:
        severe_risk = "medium"
    else:
        severe_risk = "low"
    return {"unemployment_months": round(unemp, 1),
            "emergency_fund_low": round(fund_low),
            "emergency_fund_high": round(fund_high),
            "emergency_gap": round(gap),
            "severe_illness_risk": severe_risk}


def compare_cities(wage, current_tier, target_tier,
                   insurance_mode="在职（单位缴）",
                   housing="合租单间", food_level="普通",
                   has_car=False, num_children=0, children_by_age=None,
                   support_elderly=False, support_family_monthly=0):
    """对比在当前城市和目标城市的生活成本与生活质量。"""
    estimated_wage = _estimate_target_wage(wage, current_tier, target_tier)

    common = dict(housing=housing, food_level=food_level, has_car=has_car,
                  insurance_mode=insurance_mode, num_children=num_children,
                  children_by_age=children_by_age,
                  support_elderly=support_elderly,
                  support_family_monthly=support_family_monthly)
    current = compute_current_situation(age=30, wage_pretax=wage, tier=current_tier, **common)
    target = compute_current_situation(age=30, wage_pretax=estimated_wage, tier=target_tier, **common)

    # 生成对比解读
    income_diff = target["income_net"] - current["income_net"]
    cost_diff = target["cost_total"] - current["cost_total"]
    surplus_diff = target["surplus"] - current["surplus"]

    lines = [f"▶ 对比【{current_tier}】vs【{target_tier}】："]
    if surplus_diff > 0:
        income_word = f"收入少了 {abs(income_diff):,.0f} 元" if income_diff < 0 else f"收入多了 {income_diff:,.0f} 元"
        cost_word = f"生活成本低了 {abs(cost_diff):,.0f} 元" if cost_diff < 0 else f"生活成本高了 {cost_diff:,.0f} 元"
        lines.append(f"移到【{target_tier}】后，虽然{income_word}，但{cost_word}，")
        lines.append(f"每月结余反而增加 {surplus_diff:,.0f} 元 ✅")
    elif surplus_diff == 0:
        lines.append(f"移到【{target_tier}】后，收支基本不变。")
    else:
        lines.append(f"⚠️ 移到【{target_tier}】后结余会减少 {-surplus_diff:,.0f} 元，当前【{current_tier}】更优。")
        # 若能指出具体原因
        if income_diff < 0 and cost_diff > 0:
            lines.append("（收入下降的同时生活成本反而上升，不建议搬迁。）")
        elif income_diff < 0:
            lines.append("（主要原因是收入下降幅度超过生活成本降低。）")

    # 富文本段落（结果区 RichNote 渲染）
    rich = [{"t": f"对比【{current_tier}】vs【{target_tier}】\n", "tag": "h"}]
    if surplus_diff > 0:
        inc = f"少了 {_money(abs(income_diff))}" if income_diff < 0 else f"多了 {_money(income_diff)}"
        cst = f"低了 {_money(abs(cost_diff))}" if cost_diff < 0 else f"高了 {_money(cost_diff)}"
        rich.append({"t": f"移到【{target_tier}】每月结余增加 {_money(surplus_diff)} ✅\n", "tag": "big"})
        rich.append({"t": f"（收入{inc}，生活成本{cst}）\n", "tag": "muted"})
    elif surplus_diff == 0:
        rich.append({"t": f"移到【{target_tier}】收支基本不变\n", "tag": "normal"})
    else:
        rich.append({"t": f"移到【{target_tier}】每月结余减少 {_money(-surplus_diff)} ⚠\n", "tag": "bigbad"})
        rich.append({"t": "（当前城市更优）\n", "tag": "muted"})
    rich.append({"t": f"\n预设目标城市工资：按比例估算约 {_money(estimated_wage)}/月", "tag": "normal"})
    return {
        "current": current,
        "target": target,
        "estimated_wage": round(estimated_wage),
        "income_diff": round(income_diff),
        "cost_diff": round(cost_diff),
        "surplus_diff": round(surplus_diff),
        "comparison_text": "\n".join(lines),
        "rich": rich,
    }


# ============================================================
# 借贷真实年化反算（识破网贷/信用卡分期陷阱）
# ============================================================
# ============================================================
# 借贷通用 helper（被 compute_loan_apr 及下列债务函数复用，统一口径）
# ============================================================

def _solve_monthly_irr(principal, monthly_payment, periods):
    """二分法解月内部收益率（IRR）：使 sum(monthly/(1+r)^t, t=1..periods) = principal 的 r。
    封顶 100%/月，迭代 200 次。principal/月还/期数非正或总还款≤本金时返回 0.0。"""
    if principal <= 0 or monthly_payment <= 0 or periods <= 0:
        return 0.0
    if monthly_payment * periods <= principal:
        return 0.0  # 无利息甚至负利息

    def npv(r):
        s = 0.0
        for t in range(1, periods + 1):
            s += monthly_payment / (1 + r) ** t
        return s - principal

    lo, hi = 0.0, 1.0  # 月 irr 搜索区间 0~100%
    if npv(hi) > 0:
        return hi  # 利息高得离谱，封顶
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _annual_irr_from_monthly(monthly_irr):
    """月 IRR → 真实年化（复利口径 (1+m)^12 - 1）"""
    return (1 + monthly_irr) ** 12 - 1


def _level_from_annual_irr(annual_irr):
    """真实年化 → (level 评级, 颜色提示)。阈值沿用借贷司法解释口径。"""
    if annual_irr >= 0.36:
        return "极高", "deficit"
    if annual_irr >= 0.24:
        return "高利贷", "deficit"
    if annual_irr >= 0.15:
        return "偏高", "warn"
    return "正常", "surplus"


def compute_loan_apr(principal, monthly_payment, periods):
    """反算借贷的真实年化利率（IRR 口径）。

    principal: 借款本金（元）
    monthly_payment: 每期还款额（元）
    periods: 期数（月）

    返回 dict：
        monthly_irr    月内部收益率
        annual_irr     真实年化 ((1+月irr)^12 - 1) —— 复利口径，最能反映真实成本
        nominal_apr    名义年化 (月irr × 12) —— 机构常用此口径压低数字
        total_payment  总还款额
        interest       总利息
        interest_ratio 利息占本金比
        level          风险评级
        note           白话解读（含维权提示）
    总还款 ≤ 本金时返回 {"error": ...}。
    """
    if principal <= 0 or monthly_payment <= 0 or periods <= 0:
        return {"error": "借款本金、每月还款、期数都必须为正数。"}

    total = monthly_payment * periods
    if total <= principal:
        return {"error": "总还款（月还×期数）≤ 本金，这不可能是贷款，请检查输入。"}

    monthly_irr = _solve_monthly_irr(principal, monthly_payment, periods)
    annual_irr = _annual_irr_from_monthly(monthly_irr)
    nominal_apr = monthly_irr * 12
    interest = total - principal
    interest_ratio = interest / principal

    level, _ = _level_from_annual_irr(annual_irr)
    if level == "极高":
        note = (f"真实年化 {annual_irr*100:.1f}%，超过 36% 红线。"
                f"按司法解释，超过 36% 的利息约定无效，已还的超额部分可主张返还。")
    elif level == "高利贷":
        note = (f"真实年化 {annual_irr*100:.1f}%，处于 24%~36% 区间。"
                f"这部分利息法院不予保护，未还部分可以拒绝支付。")
    elif level == "偏高":
        note = (f"真实年化 {annual_irr*100:.1f}%，超过民间借贷利率上限"
                f"（LPR 的 4 倍，约 14%~15%）。不算高利贷，但成本明显偏高。")
    else:
        note = f"真实年化 {annual_irr*100:.1f}%，处于正常区间。"

    return {
        "monthly_irr": monthly_irr,
        "annual_irr": annual_irr,
        "nominal_apr": nominal_apr,
        "total_payment": total,
        "interest": interest,
        "interest_ratio": interest_ratio,
        "level": level,
        "note": note,
    }


# ============================================================
# 债务功能扩展（4 个纯函数）
# ============================================================

def _monthly_payment(principal, annual_rate, months):
    """等额本息月供：M = P·r·(1+r)^n / ((1+r)^n − 1)，r=年利率/12，n=月数。"""
    r = annual_rate / 12
    if r == 0:
        return principal / months
    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1)


def _remaining_principal(principal, annual_rate, total_months, paid_months):
    """等额本息：贷 total_months、已还 paid_months 后的剩余本金。"""
    if paid_months >= total_months:
        return 0.0
    r = annual_rate / 12
    if r == 0:
        return principal * (total_months - paid_months) / total_months
    return principal * ((1 + r) ** total_months - (1 + r) ** paid_months) \
        / ((1 + r) ** total_months - 1)


def compare_loan_methods(principal, nominal_apr, periods):
    """对比「等额本息」与「等本等息（消费分期固定手续费制）」两种还款方式。

    principal: 借款本金（元）
    nominal_apr: 名义年化（小数，如 0.18）—— 机构报价口径
    periods: 期数（月）

    核心信息差：等本等息的手续费按初始本金固定收、不随余额递减，
    其真实年化(IRR)远高于名义——这正是消费分期/信用卡分期「月费率0.7%」的话术陷阱。

    返回 dict：equal_payment{} / equal_principal_flat{} 各含
        monthly(月供) / total_interest(总利息) / total_payment(总还款) / annual_irr(真实年化IRR)
        nominal_apr / interest_diff(等本等息多付的利息) / note
    """
    if principal <= 0:
        return {"error": "借款本金必须为正数。"}
    if periods <= 0:
        return {"error": "期数必须为正数。"}
    if nominal_apr < 0:
        return {"error": "名义年化不能为负数。"}

    r = nominal_apr / 12  # 月利率 / 月费率
    n = periods

    # --- 等额本息：月供恒定，本金递增、利息递减（银行房贷口径） ---
    ep_monthly = _monthly_payment(principal, nominal_apr, n)
    ep_total = ep_monthly * n
    ep_interest = ep_total - principal
    ep_irr = _annual_irr_from_monthly(_solve_monthly_irr(principal, ep_monthly, n))

    # --- 等本等息（固定手续费制）：每月本金=P/n，每月手续费=P*r（固定不递减） ---
    epf_fee_monthly = principal * r
    epf_monthly = principal / n + epf_fee_monthly
    epf_total = epf_monthly * n
    epf_interest = epf_total - principal  # = P*r*n
    epf_irr = _annual_irr_from_monthly(_solve_monthly_irr(principal, epf_monthly, n))

    interest_diff = epf_interest - ep_interest
    level_epf, _ = _level_from_annual_irr(epf_irr)

    if nominal_apr == 0:
        note = ("名义年化 0%，两种方式都无利息。但务必确认没有"
                "「服务费/手续费/担保费」——很多无息分期正是靠这些隐形收费赚钱。")
    else:
        parts = [
            f"机构报价的名义年化 {nominal_apr*100:.1f}%，"
            f"但等本等息（消费分期/信用卡分期常用）的真实年化高达 {epf_irr*100:.1f}%，"
            f"是名义的 {epf_irr/nominal_apr:.1f} 倍。",
            f"原因：等本等息的手续费按初始本金固定收，你越还本金越少、实际占用的钱越少，"
            f"利息却不降——所谓「月费率0.7%」折成真实年化不是 8.4%，而是约 15%+。",
            f"等额本息（银行房贷口径）真实年化约 {ep_irr*100:.1f}%，更接近名义。"
            f"同一笔本金、同一期数，等本等息比等额本息多付利息 {interest_diff:,.0f} 元。",
        ]
        if level_epf in ("极高", "高利贷"):
            parts.append("⚠️ 等本等息真实年化越过 24%/36% 红线：24%~36% 区间法院不予保护，"
                         "超 36% 部分约定无效、可主张返还。")
        note = "".join(parts)

    return {
        "equal_payment": {
            "monthly": ep_monthly,
            "total_interest": ep_interest,
            "total_payment": ep_total,
            "annual_irr": ep_irr,
        },
        "equal_principal_flat": {
            "monthly": epf_monthly,
            "monthly_fee": epf_fee_monthly,
            "total_interest": epf_interest,
            "total_payment": epf_total,
            "annual_irr": epf_irr,
        },
        "nominal_apr": nominal_apr,
        "interest_diff": interest_diff,
        "note": note,
    }


def compute_affordable_debt(monthly_surplus, nominal_apr, periods, income=None):
    """按月结余反算可承受的负债上限（等额本息口径）。

    monthly_surplus: 月结余（元，收入扣掉必要开支后可自由支配的钱）
    nominal_apr: 名义年化（小数）
    periods: 期数（月）
    income: 可选月薪（元）；提供则月还款上限取 min(月结余×0.5, 月薪×0.5)

    经验线：月还款别超过你能自由支配的钱（月结余）的一半，否则一笔意外就断供。
    返回 dict：max_monthly / max_principal(50%档) / safe_principal(30%档) /
              ratio_used / monthly_surplus / note
    """
    if monthly_surplus <= 0:
        return {"error": "你目前月结余 ≤ 0（入不敷出），暂时不具备新增负债的能力。"
                         "建议先把收入提上去、或削减一些非必要开支，等情况好转再考虑借钱。"}
    if nominal_apr < 0:
        return {"error": "名义年化不能为负数。"}
    if periods <= 0:
        return {"error": "期数必须为正数。"}

    cap = monthly_surplus * 0.5                 # 50% 档（激进）
    if income is not None and income > 0:
        cap = min(cap, income * 0.5)
    safe_cap = cap * 0.6                        # 30% 档（保守）

    r = nominal_apr / 12
    n = periods

    def principal_from_monthly(m):
        if r == 0:
            return m * n
        return m * ((1 + r) ** n - 1) / (r * (1 + r) ** n)

    max_principal = principal_from_monthly(cap)
    safe_principal = principal_from_monthly(safe_cap)

    note = (
        f"按经验线，月还款别超过你能自由支配的钱（月结余）的一半，"
        f"也就是每月最多还 {cap:,.0f} 元。"
        f"按名义年化 {nominal_apr*100:.1f}%、{n} 期等额本息反推，"
        f"你能承受的借款本金上限约 {max_principal:,.0f} 元（50%档），"
        f"更稳一点按 30% 档约 {safe_principal:,.0f} 元。\n"
        f"注意：这是按等额本息算的。若你借的是消费分期（等本等息），"
        f"同样月供能借的本金更少，因为它的真实利息更贵（见「还款方式对比」）。\n"
        f"⚠️「先借了再说」是绝大多数债务雪崩的起点：一旦收入波动或生病变失业，"
        f"月还款就成了压垮你的最后一根稻草。"
    )

    return {
        "max_monthly": cap,
        "max_principal": max_principal,
        "safe_principal": safe_principal,
        "ratio_used": 0.5,
        "monthly_surplus": monthly_surplus,
        "note": note,
    }


def simulate_debt_payoff(debts, method="avalanche", extra_monthly=0):
    """模拟多笔债的还清过程（雪球法 / 雪崩法）。

    debts: [{"name","balance"(当前余额),"annual_rate"(年化小数),"min_monthly"(最低月还款)}, ...]
    method: "snowball"(先还余额最小) / "avalanche"(先还利率最高)
    extra_monthly: 每月额外多还的钱，集中砸向目标债

    策略：每笔债只还最低还款（避免违约/催收），把所有挤得出的余钱
    （extra + 当月结清债省下的最低额）集中砸向 method 选出的「目标债」。

    返回 dict：method / payoff_order[] / total_months / total_payment /
              total_interest / monthly_snapshots[] / unpayable / unpayable_reason / note
    """
    if not debts:
        return {"error": "请至少输入一笔债。"}

    parsed = []
    for i, d in enumerate(debts):
        try:
            bal = float(d["balance"])
            rate = float(d["annual_rate"])
            mn = float(d["min_monthly"])
        except (KeyError, ValueError, TypeError):
            return {"error": f"第 {i+1} 笔债的输入有误（金额/年化/月还必须是数字）。"}
        if bal <= 0:
            return {"error": f"第 {i+1} 笔债的余额必须为正数。"}
        if rate < 0:
            return {"error": f"第 {i+1} 笔债的年化不能为负。"}
        if mn <= 0:
            return {"error": f"第 {i+1} 笔债的最低月还款必须为正数。"}
        parsed.append({
            "name": str(d.get("name") or f"债{i+1}"),
            "balance": bal,
            "annual_rate": rate,
            "min_monthly": mn,
        })

    # 失控预检：某笔最低还款 ≤ 当月利息 → 该笔永远还不清（本金只增不减）
    for d in parsed:
        monthly_interest = d["balance"] * d["annual_rate"] / 12
        if d["min_monthly"] <= monthly_interest:
            need = monthly_interest + 1
            return {
                "method": method,
                "unpayable": True,
                "unpayable_reason": (
                    f"「{d['name']}」按当前最低月还款 {d['min_monthly']:.0f} 元永远还不清："
                    f"它每月新增利息就有 {monthly_interest:.0f} 元（年化 {d['annual_rate']*100:.0f}%），"
                    f"最低还款连利息都盖不住，本金只会越滚越多。要压住这笔，"
                    f"每月至少得还 {need:.0f} 元。\n这是信用卡最低还款"
                    f"（通常只有账单的 10% 左右）的真实陷阱——你以为在还钱，"
                    f"其实大部分在还利息、本金纹丝不动。"),
                "note": "",
                "payoff_order": [],
                "total_months": None,
                "total_payment": 0,
                "total_interest": 0,
                "monthly_snapshots": [],
            }

    rates = {d["name"]: d["annual_rate"] for d in parsed}
    mins = {d["name"]: d["min_monthly"] for d in parsed}
    balances = {d["name"]: d["balance"] for d in parsed}

    total_interest = 0.0
    total_payment = 0.0
    payoff_order = []
    snapshots = []
    month = 0

    def pick_target(bals):
        if method == "snowball":
            return min(bals, key=lambda nm: (bals[nm], -rates[nm]))
        return max(bals, key=lambda nm: (rates[nm], -bals[nm]))

    while balances and month < 1200:
        month += 1
        balances_prev = dict(balances)

        # 1) 计息
        interest = {nm: balances[nm] * rates[nm] / 12 for nm in balances}
        for nm in interest:
            total_interest += interest[nm]

        # 2) 每笔先付最低还款（但不超过本息合计）
        free_pool = float(extra_monthly)
        new_balances = {}
        for nm in list(balances):
            owed = balances[nm] + interest[nm]
            pay_min = min(mins[nm], owed)
            total_payment += pay_min
            remaining = owed - pay_min
            if remaining <= 0.005:
                payoff_order.append({"name": nm, "payoff_month": month})
                free_pool += mins[nm] - owed          # 本笔最低额的富余滚入自由池
            else:
                new_balances[nm] = remaining
        balances = new_balances

        # 3) 自由池集中砸向目标债，结清则顺延下一个
        main_target = None
        while free_pool > 0.005 and balances:
            target = pick_target(balances)
            if main_target is None:
                main_target = target
            owed = balances[target]
            pay = min(free_pool, owed)
            total_payment += pay
            free_pool -= pay
            if owed - pay <= 0.005:
                payoff_order.append({"name": target, "payoff_month": month})
                del balances[target]
            else:
                balances[target] = owed - pay

        snapshots.append({
            "month": month,
            "balances": balances_prev,
            "target": main_target if main_target else "",
            "extra": extra_monthly,
        })

    if balances:
        return {
            "method": method,
            "unpayable": True,
            "unpayable_reason": "模拟超过 100 年仍未还清，请检查输入（最低还款可能偏低）。",
            "note": "",
            "payoff_order": payoff_order,
            "total_months": month,
            "total_payment": total_payment,
            "total_interest": total_interest,
            "monthly_snapshots": snapshots,
        }

    method_cn = "雪球法" if method == "snowball" else "雪崩法"
    note = (
        f"按「{method_cn}」：{month} 个月还清全部债务，总共付出 {total_payment:,.0f} 元，"
        f"其中利息 {total_interest:,.0f} 元。\n核心动作：每笔债只还最低还款（避免违约催收），"
        f"把所有挤得出的余钱集中砸向"
        f"{'余额最小的那笔（雪球法：先尝到结清的甜头，靠成就感撑下去）' if method == 'snowball' else '利率最高的那笔（雪崩法：数学最优，总利息最少）'}。"
    )
    return {
        "method": method,
        "payoff_order": payoff_order,
        "total_months": month,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "monthly_snapshots": snapshots,
        "unpayable": False,
        "unpayable_reason": "",
        "note": note,
    }


def simulate_loan_spiral(initial_balance, annual_rate, months, actual_monthly_payment=0):
    """演示「以贷养贷/只还最低」时债务如何利滚利、指数增长。

    initial_balance: 初始债务（元）
    annual_rate: 年化（小数）
    months: 演示月数
    actual_monthly_payment: 每月实际还款（默认 0 = 完全借新还旧，一分不还）

    逐月：balance = balance*(1+rate/12) − actual_monthly_payment
    若实还 ≤ 当月利息，差额持续滚进本金（利滚利）。
    返回 dict：final_balance / doubled / doubling_month / monthly_snapshots[] /
              breakeven_monthly / note
    """
    if initial_balance <= 0:
        return {"error": "初始债务必须为正数。"}
    if annual_rate <= 0:
        return {"error": "年化必须为正数（演示利滚利才有意义）。"}
    if months <= 0:
        return {"error": "演示月数必须为正数。"}
    if actual_monthly_payment < 0:
        return {"error": "每月实际还款不能为负。"}

    r = annual_rate / 12
    balance = initial_balance
    snapshots = []
    doubled = False
    doubling_month = None

    for m in range(1, months + 1):
        interest = balance * r
        balance = balance + interest - actual_monthly_payment
        if balance < 0:
            balance = 0
        snapshots.append({"month": m, "balance": balance, "interest_accrued": interest})
        if not doubled and balance >= initial_balance * 2:
            doubled = True
            doubling_month = m

    breakeven = initial_balance * r  # 每月至少还这么多才能压住利息、让债务不增长
    years_72 = 72 / (annual_rate * 100)  # 72 法则估算翻倍年数

    if actual_monthly_payment < breakeven:
        trend = (f"每月实还 {actual_monthly_payment:.0f} 元 < 每月新增利息 {breakeven:.0f} 元，"
                 f"差额持续滚进本金——{months} 个月后债务从 {initial_balance:,.0f} 涨到 {balance:,.0f} 元。")
    else:
        trend = (f"每月实还 {actual_monthly_payment:.0f} 元 ≥ 每月利息 {breakeven:.0f} 元，"
                 f"债务在下降（{months} 个月后 {balance:,.0f} 元）。保持这个力度就能逐步脱困。")

    if doubled:
        spiral_warn = f"仅 {doubling_month} 个月就翻倍（72 法则估算约 {years_72:.0f} 年翻倍）。"
    elif actual_monthly_payment < breakeven:
        spiral_warn = f"本期间未翻倍，但按 72 法则约 {years_72:.0f} 年会翻倍。"
    else:
        spiral_warn = ""

    note = (
        f"「借新还旧、只还最低、以贷养贷」是债务失控的标准路径："
        f"利息按复利指数增长，你还的钱不够覆盖利息，缺口就滚进本金再生利息。\n"
        f"{trend}\n{spiral_warn}\n"
        f"要止血，每月至少得还 {breakeven:.0f} 元（= 初始债务的月利息）才能让债务不再增长，"
        f"之后再往上加码还本金。\n"
        f"⚠️ 若这笔债真实年化超 36%，超过部分约定无效、可主张返还（见「反算真实年化」）。"
    )

    return {
        "final_balance": balance,
        "doubled": doubled,
        "doubling_month": doubling_month,
        "monthly_snapshots": snapshots,
        "breakeven_monthly": breakeven,
        "note": note,
    }


# ============================================================
# 劳动权益（加班费 / 最低工资 —— 法定标准，全国统一，无需各地数据）
# ============================================================

# 月计薪天数（《劳动法》/劳社部发[2008]3号）：(365-104)÷12 = 21.75
MONTH_WORK_DAYS_PAY = 21.75
DAILY_HOURS = 8  # 法定每日工作 8 小时


def compute_overtime_pay(monthly_wage, weekday_ot=0, weekend_ot=0, holiday_ot=0):
    """依法反算加班费（《劳动法》第44条 + 劳社部发[2008]3号）。

    monthly_wage: 月工资（元，加班费计算基数，按全额月工资算）
    weekday_ot:   工作日延时加班小时/月（依法 150%）
    weekend_ot:   休息日加班小时/月（不能补休的，依法 200%）
    holiday_ot:   法定节假日加班小时/月（依法 300%）

    法定时薪 = 月工资 ÷ 21.75 ÷ 8。
    返回 dict：hourly_wage / 各类加班费 / total_overtime / detail[] / note
    """
    if monthly_wage <= 0:
        return {"error": "月工资必须为正数。"}
    if weekday_ot < 0 or weekend_ot < 0 or holiday_ot < 0:
        return {"error": "加班小时不能为负。"}

    hourly = monthly_wage / MONTH_WORK_DAYS_PAY / DAILY_HOURS  # 法定时薪

    weekday_pay = hourly * 1.5 * weekday_ot
    weekend_pay = hourly * 2.0 * weekend_ot
    holiday_pay = hourly * 3.0 * holiday_ot
    total = weekday_pay + weekend_pay + holiday_pay

    detail = []
    if weekday_ot > 0:
        detail.append({"type": "工作日延时", "hours": weekday_ot, "rate": 1.5, "pay": weekday_pay})
    if weekend_ot > 0:
        detail.append({"type": "休息日", "hours": weekend_ot, "rate": 2.0, "pay": weekend_pay})
    if holiday_ot > 0:
        detail.append({"type": "法定节假日", "hours": holiday_ot, "rate": 3.0, "pay": holiday_pay})

    if total == 0:
        note = (f"你的法定时薪约 {hourly:.2f} 元/小时（月工资 ÷ 21.75 天 ÷ 8 小时）。"
                f"还没填加班时长——把每月各类加班小时填上，就能算出依法应得的加班费。\n"
                f"提示：企业常以「包薪」「综合工时」或只给调休为由不给加班费，这不合法；"
                f"只要你加了班且企业没依法付钱，差额就是被克扣的。")
    else:
        note = (
            f"你的法定时薪约 {hourly:.2f} 元/小时，本月加班费依法应得约 {total:,.0f} 元"
            f"（工作日1.5倍、休息日2倍、法定节假日3倍）——这是你应得的钱。\n"
            f"争取它需要花些时间、备好证据，在职期间也要考虑周全。"
            f"下方「维权现实评估」会结合你的实际情况，帮你看看怎么处理对你最有利。"
        )

    return {
        "hourly_wage": hourly,
        "weekday_pay": weekday_pay,
        "weekend_pay": weekend_pay,
        "holiday_pay": holiday_pay,
        "total_overtime": total,
        "detail": detail,
        "note": note,
    }


def compute_min_wage_check(monthly_wage, tier):
    """对照当地最低工资标准（《劳动法》第48条）。

    monthly_wage: 你的月薪（元）
    tier: 城市等级（一线/新一线/二线/三线/四线/五线）

    月薪低于当地最低工资即违法。返回 dict：min_wage / below / ratio / monthly_wage / tier / note
    """
    if monthly_wage <= 0:
        return {"error": "月薪必须为正数。"}
    if tier not in D.MIN_WAGE:
        return {"error": f"城市等级无效（应为 {D.TIER_KEYS} 之一）。"}

    min_wage = D.MIN_WAGE[tier]
    below = monthly_wage < min_wage
    ratio = monthly_wage / min_wage

    if below:
        gap = min_wage - monthly_wage
        note = (
            f"你所在地区（{tier}城市）现行最低工资标准约 {min_wage:,.0f} 元/月，"
            f"你的月薪 {monthly_wage:,.0f} 元低于最低工资 {gap:,.0f} 元，这是违法的——"
            f"即便试用期、学徒期，工资也不得低于当地最低工资。\n"
            f"维权：拨打 12333 或到当地劳动监察大队投诉，可要求补足差额。\n"
            f"（注：此处最低工资是按城市等级的概值，精确标准以当地人社局公布为准。）"
        )
    elif ratio < 1.2:
        note = (
            f"你所在地区（{tier}城市）最低工资约 {min_wage:,.0f} 元/月，"
            f"你的月薪 {monthly_wage:,.0f} 元刚好在最低工资线上方（是最低工资的 {ratio:.1%}），"
            f"勉强合法，议价空间很小。"
        )
    else:
        note = (
            f"你所在地区（{tier}城市）最低工资约 {min_wage:,.0f} 元/月，"
            f"你的月薪 {monthly_wage:,.0f} 元是最低工资的 {ratio:.1%}，高于最低线，合法。"
        )

    return {
        "min_wage": min_wage,
        "below": below,
        "ratio": ratio,
        "monthly_wage": monthly_wage,
        "tier": tier,
        "note": note,
    }


def assess_overtime_claim(owed_amount, employed=True, evidence="部分"):
    """评估「为这笔加班费去争」的现实成本与收益，给值不值得的建议。

    owed_amount: 被欠的加班费总额（元，依法应得 − 实际拿到）
    employed: 是否还在职（True=在职，硬刚风险高）
    evidence: 证据情况 "充分" / "部分" / "几乎没有"

    设计立场：不煽动维权，按劳动者实际利益最大化给现实分级建议。
    返回 dict：win_chance / time_cost / money_cost / risk /
              verdict / verdict_level(good|caution|warn) / note
    """
    if owed_amount <= 0:
        return {"error": "被欠金额必须为正数（若实际已拿到全部加班费，就没有被欠部分）。"}
    if evidence not in ("充分", "部分", "几乎没有"):
        return {"error": "证据情况应选：充分 / 部分 / 几乎没有。"}

    win_chance = {
        "充分": "中高（证据是关键，齐全则胜算较大）",
        "部分": "中等（部分证据可补强；企业若拿不出考勤反而对你有利）",
        "几乎没有": "偏低（证据较少，先把证据备齐会更稳妥）",
    }[evidence]

    time_cost = ("劳动仲裁一审通常 2-4 个月；企业不服起诉到法院，一审再加 3-6 个月，"
                 "走完一审二审可能大半年到一年。期间要准备材料、跑立案、出庭。")
    money_cost = ("劳动仲裁本身不收费。请律师多为风险代理（胜诉后抽 10-30%），"
                  "小额案件律师往往不愿接；收入低可申请 12348 法律援助（免费）。")
    if employed:
        risk = ("在职期间主张，可能面临调岗、降薪等压力；已离职则没有这个顾虑，"
                "但仲裁时效从离职起算 1 年。")
    else:
        risk = "你已离职，没有在职方面的顾虑；注意仲裁时效从离职起算 1 年，别拖过。"

    if evidence == "几乎没有":
        verdict = "建议先收集证据"
        verdict_level = "warn"
        note = (f"你被欠约 {owed_amount:,.0f} 元，这笔钱是该给你的，目前证据还比较少。"
                f"加班费需要由劳动者一方举证，所以现阶段先把证据备齐，要回来的把握会大很多。\n"
                f"建议悄悄收集：排班表拍照、加班通知/群消息截图、打卡记录、"
                f"跟主管确认加班的聊天记录。证据备齐后（或离职时）再主张，"
                f"仲裁时效从离职起算 1 年，时间够用——准备做足，成功把握更大。")
    elif owed_amount < 3000 and employed and evidence != "充分":
        verdict = "先留证，离职时一并主张更划算"
        verdict_level = "caution"
        note = (f"你被欠约 {owed_amount:,.0f} 元，金额不算大、还在职。"
                f"更划算的做法是先把证据留好（排班、加班通知、打卡、沟通记录），"
                f"等离职时把加班费和经济补偿等一次性主张——这样 1 年时效能用足，"
                f"金额累积起来更可观，离职后也没有后顾之忧。")
    elif owed_amount >= 10000 or not employed or evidence == "充分":
        verdict = "值得争取"
        verdict_level = "good"
        reasons = []
        if owed_amount >= 10000:
            reasons.append("金额较大")
        if not employed:
            reasons.append("已离职无后顾之忧")
        if evidence == "充分":
            reasons.append("证据较齐全")
        note = (f"你被欠约 {owed_amount:,.0f} 元（{'、'.join(reasons)}），"
                f"这笔钱值得争取回来。\n胜算：{win_chance}\n"
                f"可以先打 12333 咨询，或申请 12348 法律援助（低收入免费），"
                f"也可以找风险代理律师（胜诉才抽成，不赢不花钱）。\n"
                f"小提示：万一企业拖欠，还能申请强制执行，给自己留足时间预期。")
    else:
        verdict = "可以争取，选稳妥的方式"
        verdict_level = "caution"
        note = (f"你被欠约 {owed_amount:,.0f} 元，金额中等、证据一般"
                f"{'、还在职' if employed else ''}。\n胜算：{win_chance}\n"
                f"两条路都行：一是现在就把证据补强（排班、加班通知、打卡、沟通记录）去主张；"
                f"二是先留好证据，等离职时再一并提（时效 1 年）。"
                f"结合自己的情况，选更稳妥的那条。")

    return {
        "owed_amount": owed_amount,
        "employed": employed,
        "evidence": evidence,
        "win_chance": win_chance,
        "time_cost": time_cost,
        "money_cost": money_cost,
        "risk": risk,
        "verdict": verdict,
        "verdict_level": verdict_level,
        "note": note,
    }


def build_overtime_prompt(wage, weekday_ot, weekend_ot, holiday_ot,
                          actual, months, employed, evidence, city=""):
    """生成「问 AI 的加班费维权提示词」，自动填充用户数据。

    返回纯文本提示词，用户一键复制粘贴到任意 AI（豆包/Kimi/DeepSeek/ChatGPT 等）。
    设计依据 prompt-engineering-patterns：角色设定 + 变量插值 + 结构化分段 +
    现实立场（见 pragmatic-rights-design）+ 可执行步骤 + 本地政策外包给 AI 查。
    """
    employed_cn = "还在职" if employed else "已经离职"
    evidence_desc = {
        "充分": "比较齐全（考勤、排班、加班通知、聊天记录等基本都有）",
        "部分": "有一部分（比如排班表或聊天记录，但不全）",
        "几乎没有": "几乎没有（没什么能证明加班的材料）",
    }.get(evidence, evidence)
    if city:
        city_line = f"- 所在城市：{city}"
        local_q = f"针对我所在城市「{city}」，有没有我该知道的本地规定或更划算的做法？"
    else:
        city_line = "- 所在城市：（我稍后补充，请先按一般情况分析）"
        local_q = "有没有我该知道的常见地方性规定或更划算的做法？"

    return (
        "请以资深劳动法律师的口吻，面向不太懂法律的普通劳动者，用大白话帮我解答。"
        "我的情况如下：\n\n"
        "【我的情况】\n"
        f"- 月工资：{wage:,.0f} 元\n"
        f"- 每月加班：工作日延时 {weekday_ot} 小时、休息日 {weekend_ot} 小时、"
        f"法定节假日 {holiday_ot} 小时\n"
        f"- 每月实际拿到的加班费：{actual:,.0f} 元\n"
        f"- 这种情况持续了：{months} 个月\n"
        f"- 我目前：{employed_cn}\n"
        f"- 手头的证据：{evidence_desc}\n"
        f"{city_line}\n\n"
        "【请帮我算清楚，并告诉我怎么办】\n"
        "1. 按国家法律，我每月依法应得多少加班费？请给出计算过程"
        "（法定时薪 = 月工资 ÷ 21.75 ÷ 8；工作日延时 1.5 倍、休息日 2 倍、"
        "法定节假日 3 倍）。\n"
        f"2. 对照我实际拿到的，我每月被欠多少？这 {months} 个月总共被欠多少？\n"
        "3. 如果我想把这笔钱要回来，具体该怎么操作？请分步骤讲"
        "（先做什么、再做什么），需要准备哪些材料证据、找哪个部门、打哪个电话。\n"
        "4. 维权大概要花多少时间、有哪些成本和风险"
        "（比如在职会不会被针对、劳动仲裁时效、举证难不难、赢了能不能真拿到钱）？"
        "请结合我的情况实事求是地说，既不夸大也不劝退。\n"
        f"5. {local_q}\n"
        "6. 综合我的实际情况，你最建议我怎么做"
        "（现在就去争取 / 先悄悄留好证据以后再说 / 其他）？说说理由。\n\n"
        "要求：站在我的利益最大化角度，给具体、能照着做的建议，"
        "别讲空话套话，也别不管不顾地鼓励我去硬刚。"
    )


def build_loan_apr_prompt(principal, monthly, periods, profile=None):
    """真实年化反算 → 问 AI 的提示词（判断是否高利贷、维权）。"""
    return (
        "请以资深金融消费者权益保护专家的口吻，用大白话帮我判断这笔贷款正不正常、"
        "我有没有被坑。情况如下：\n\n"
        "【这笔贷款】\n"
        f"- 借款本金：{principal:,.0f} 元\n"
        f"- 每月还款：{monthly:,.0f} 元\n"
        f"- 期数：{periods} 个月\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 反算这笔贷款的真实年化利率（IRR 复利口径）和名义年化，给出计算过程。\n"
        "2. 按真实年化判断它属于哪类（正常 / 偏高 / 高利贷 24%-36% / 超过 36% 红线），"
        "结合国家法律说清楚。\n"
        "3. 如果是高利贷或超红线，我有哪些权利？（如超 36% 部分约定无效可主张返还、"
        "24%-36% 法院不予保护等）\n"
        "4. 我该怎么维权？分步骤讲——找谁、打什么电话、准备什么材料。\n"
        "5. 综合看，我现在怎么做最划算？\n\n"
        "要求：站在我的利益最大化角度，实事求是，给能照着做的具体建议，别讲空话。"
    )


def build_compare_methods_prompt(principal, apr_pct, periods, profile=None):
    """还款方式对比 → 问 AI 的提示词。"""
    return (
        "请以资深金融顾问的口吻，用大白话帮我讲清楚两种还款方式的区别，我快被绕晕了。"
        "情况如下：\n\n"
        "【这笔贷款】\n"
        f"- 本金：{principal:,.0f} 元\n"
        f"- 名义年化：{apr_pct:.1f}%（机构报的价）\n"
        f"- 期数：{periods} 个月\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 分别按「等额本息」和「等本等息（消费分期常见的固定手续费制）」算："
        "每月还多少、总利息多少、真实年化（IRR）多少，给计算过程。\n"
        "2. 重点解释：为什么「等本等息」的真实年化会比名义高那么多？"
        "（提示：手续费按初始本金收、不随还款递减）\n"
        "3. 如果我正被推销的消费分期 / 信用卡分期用的是「等本等息」，我实际多花了多少？"
        "划不划算？\n"
        "4. 我该怎么选、怎么跟机构谈、有什么要注意的坑？\n\n"
        "要求：大白话，给具体建议，别讲空话。"
    )


def build_affordable_debt_prompt(surplus, apr_pct, periods, income=None, profile=None):
    """可承受负债上限 → 问 AI 的提示词。"""
    income_line = (f"- 月薪：{income:,.0f} 元\n" if income
                   else "- 月薪：（我没填，请按一般情况估算）\n")
    return (
        "请以资深理财顾问的口吻，用大白话帮我判断我现在能不能再借钱、借多少安全。"
        "情况如下：\n\n"
        "【我的情况】\n"
        f"- 每月结余（收入扣掉必要开支后剩下的）：{surplus:,.0f} 元\n"
        + income_line +
        f"- 想借的名义年化：{apr_pct:.1f}%\n"
        f"- 想借的期数：{periods} 个月\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 按健康负债的标准（月还款不超过月结余 / 收入的合理比例），"
        "我最多能借多少本金？给计算。\n"
        "2. 我目前的负债能力算健康吗？有没有风险信号？\n"
        "3. 借之前我该想清楚哪些事？（用途、还款来源、万一收入断了怎么办）\n"
        "4. 有没有比借钱更好的替代办法？\n\n"
        "要求：站在我不踩坑的角度，实事求是，给具体建议。"
    )


def build_debt_payoff_prompt(debts_desc, extra):
    """多笔债雪球/雪崩 → 问 AI 的提示词。debts_desc 为各笔债的文本描述（UI 组装）。"""
    return (
        "请以资深债务顾问的口吻，用大白话帮我制定还清多笔债务的最优方案。"
        "情况如下：\n\n"
        "【我的债务】\n"
        f"{debts_desc}\n"
        f"- 每月除了各笔最低还款，我还能额外挤出：{extra:,.0f} 元\n\n"
        "【请帮我】\n"
        "1. 按「雪球法」（先还余额最小）和「雪崩法」（先还利率最高）分别推演："
        "多久能全还清、总共要付多少利息？哪种更省？\n"
        "2. 结合我的情况，建议用哪种、为什么。\n"
        "3. 有没有哪笔债的最低还款根本盖不住利息（越还越多）？怎么处理？\n"
        "4. 分步骤讲具体怎么操作（各笔怎么分配、怎么跟债权方谈减免 / 分期）。\n"
        "5. 怎样能更快摆脱债务（增收、减支、协商等现实办法）？\n\n"
        "要求：给现实、可执行的方案，别讲空话，也别吓唬我。"
    )


def build_spiral_prompt(init, apr_pct, months, pay, profile=None):
    """以贷养贷螺旋 → 问 AI 的提示词。"""
    return (
        "请以资深债务顾问的口吻，用大白话帮我判断我是不是陷入了「以贷养贷」的恶性循环、"
        "该怎么脱困。情况如下：\n\n"
        "【我的情况】\n"
        f"- 目前欠着：{init:,.0f} 元\n"
        f"- 这笔债的年化：{apr_pct:.1f}%\n"
        f"- 每月我实际能还：{pay:,.0f} 元\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 按这个还款力度，我的债务是在涨还是在降？大概多久会翻倍？给计算。\n"
        "2. 我算不算陷入了「借新还旧 / 以贷养贷」的螺旋？严重程度如何？\n"
        "3. 要让债务停止增长，我每月至少得还多少（止血线）？\n"
        "4. 给我一个现实可行的脱困方案：怎么止血、怎么逐步还清、要不要债务重组 / 协商、"
        "找什么帮助。\n"
        "5. 如果是网贷 / 信用卡，有没有我该知道的维权或救济渠道（如暴力催收投诉）？\n\n"
        "要求：实事求是，给我能照着做的出路，别只吓唬我。"
    )


def build_min_wage_prompt(wage, tier, city="", profile=None):
    """最低工资对照 → 问 AI 的提示词。"""
    city_line = (f"- 所在城市：{city}" if city
                 else "- 所在城市：（请按我所在城市等级对应的典型城市分析）")
    return (
        "请以资深劳动法律师的口吻，用大白话帮我判断我的工资是不是低于法定底线、该怎么办。"
        "情况如下：\n\n"
        "【我的情况】\n"
        f"- 我的月薪：{wage:,.0f} 元\n"
        f"- 所在城市等级：{tier}\n"
        f"{city_line}\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 我所在地区目前的最低工资标准（精确值）是多少？我的工资有没有低于这个底线？\n"
        "2. 如果低于，这是违法的——法律依据是什么（如《劳动法》第 48 条）？\n"
        "3. 就算没低于，我的工资在当地处在什么水平？议价空间大不大？\n"
        "4. 如果我想争取合理工资或维权，具体怎么做（找谁、打什么电话、准备什么）？\n"
        "5. 针对我所在地区，有没有我该知道的本地规定？\n\n"
        "要求：站在我的利益角度，给现实、能照着做的建议。"
    )


def build_unemployment_prompt(city="", years="", wage="", reason="", profile=None):
    """失业金（外包给 AI 查当地标准）→ 问 AI 的提示词。
    years/wage/reason 可选：界面有就传，没有让 AI 问。"""
    city_line = (f"- 我所在的城市：{city}" if city
                 else "- 我所在的城市：（我稍后告诉你，请先问我）")
    try:
        yr = float(years)
        years_line = f"- 失业保险累计缴费年限：{yr:.0f} 年"
    except (TypeError, ValueError):
        years_line = "- 失业保险累计缴费年限：（请问我，这决定能领几个月）"
    try:
        wage_line = f"- 上份工作月工资：{float(wage):,.0f} 元" if wage else "- 上份工作月工资：（请问我）"
    except (TypeError, ValueError):
        wage_line = "- 上份工作月工资：（请问我）"
    return (
        "请以资深社保 / 劳动保障专家的口吻，用大白话帮我算清楚：我被裁（或快失业）了，"
        "能领多少失业金、领多久、怎么领。情况如下：\n\n"
        "【我的情况】\n"
        f"{city_line}\n"
        f"{years_line}\n"
        f"{wage_line}\n"
        f"- 离职原因：{reason or '（请问我：公司辞退 / 合同到期不续签 / 协商解除 / 个人原因，这关系到能不能领）'}\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 按我所在城市的最新规定，算我大概能领多少失业金、能领几个月。\n"
        "2. 领失业金需要满足什么条件？我的情况符不符合？\n"
        "3. 具体怎么申领？去哪里办、带什么材料、能线上办吗？\n"
        "4. 领失业金期间，我的医保 / 养老保险怎么办？有没有其他配套待遇？\n"
        "5. 除了失业金，我还能不能领别的（如失业补助金、临时救助、就业服务）？\n\n"
        "要求：结合我所在城市的最新政策，给具体、能照着办的步骤。"
    )


def build_subsidy_prompt(city="", profile=None):
    """灵活就业社保补贴（4050，外包给 AI）→ 问 AI 的提示词。
    年龄/社保等从 profile 的事实段带入（_profile_brief），性别档案未存则让 AI 问。"""
    city_line = (f"- 我所在的城市：{city}" if city
                 else "- 我所在的城市：（我稍后告诉你，请先问我）")
    return (
        "请以资深社保 / 就业援助专家的口吻，用大白话帮我搞清楚：我能不能领「灵活就业社保补贴」"
        "（有的地方叫 4050 补贴、就业困难人员社保补贴），能补多少、怎么申请。"
        "情况如下：\n\n"
        "【我的情况】\n"
        f"{city_line}\n"
        "- 性别：（请问我，4050 对性别和年龄都有要求，一般女≥40/男≥50）\n"
        "- 是否以灵活就业身份自己缴职工养老+医保？（居民社保不算，请确认）\n"
        "- 我有没有被认定为「就业困难人员」？（请问我，这是申领前提）\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 按我所在城市的最新规定，结合我的年龄/性别/社保情况，判断我能不能享受这个补贴。\n"
        "2. 如果能，补贴标准大概多少、能享受多久？\n"
        "3. 怎么申请？去哪里办、带什么材料、流程是什么？\n"
        "4. 有没有我容易忽略的坑（比如要先做灵活就业登记、认定就业困难人员等）？\n"
        "5. 除了这个补贴，我这种情况还有没有别的能领的（如创业补贴、技能补贴）？\n\n"
        "要求：结合我所在城市的最新政策，给具体、能照着办的步骤。"
    )


# 求助场景库：key → {title, role, situation, law_hint}（用于求助渠道页的按钮墙）
HELP_SCENARIOS = {
    "欠薪": {"title": "被拖欠工资 / 加班费", "role": "资深劳动法律师",
             "situation": "我的工资 / 加班费被拖欠了",
             "law": "《劳动法》《劳动合同法》《保障农民工工资支付条例》"},
    "社保": {"title": "公司不缴社保 / 公积金", "role": "资深社保与劳动法律师",
             "situation": "公司没给我缴社保，或没缴公积金",
             "law": "《社会保险法》《住房公积金管理条例》"},
    "辞退": {"title": "违法辞退 / 没给经济补偿", "role": "资深劳动法律师",
             "situation": "我被辞退了，公司没给经济补偿，或补偿不合理",
             "law": "《劳动合同法》第 47、87 条"},
    "无合同": {"title": "没签劳动合同", "role": "资深劳动法律师",
               "situation": "公司一直没和我签书面劳动合同",
               "law": "《劳动合同法》第 10、82 条（未签合同可主张二倍工资）"},
    "工伤": {"title": "受了工伤", "role": "资深工伤与劳动法律师",
             "situation": "我在工作中受了伤",
             "law": "《工伤保险条例》"},
    "消费": {"title": "消费纠纷（商品 / 服务 / 预付卡跑路）", "role": "资深消费者权益保护律师",
             "situation": "我买商品或服务遇到问题，或商家收了钱跑路",
             "law": "《消费者权益保护法》"},
    "网贷催收": {"title": "网贷 / 信用卡 / 暴力催收", "role": "资深金融消费者权益律师",
                 "situation": "我被网贷或信用卡催收困扰（利息过高、暴力催收等）",
                 "law": "民间借贷利率上限（LPR 4 倍）、催收自律公约"},
    "租房": {"title": "租房 / 押金纠纷", "role": "资深房屋租赁纠纷律师",
             "situation": "我租房遇到问题（押金不退、房东违约、中介坑等）",
             "law": "《民法典》合同编、当地房屋租赁规定"},
    "派遣中介": {"title": "劳务派遣 / 黑中介", "role": "资深劳动法律师",
                 "situation": "我通过劳务派遣或中介找工作，被坑了（收费、克扣、不安排等）",
                 "law": "《劳动合同法》劳务派遣专节、《就业促进法》"},
    "心理": {"title": "心理崩溃 / 压力撑不住", "role": "有共情力的心理援助工作者",
             "situation": "我最近压力大到撑不住了，不知道怎么办",
             "law": "（非法律问题，重点是情绪支持和求助渠道）"},
}


def build_help_prompt(scene_key, city=""):
    """求助场景 → 问 AI 的提示词（让 AI 指路：找谁、打什么电话、怎么操作）。"""
    s = HELP_SCENARIOS.get(scene_key)
    if not s:
        return "（未知场景）"
    city_line = (f"- 我所在的城市：{city}" if city
                 else "- 我所在的城市：（请先问我，或先按一般情况）")
    local = f"结合我所在城市 {city} 的最新规定，" if city else ""
    return (
        f"请以{s['role']}的口吻，用大白话帮我。{s['situation']}。情况如下：\n\n"
        "【先了解我的情况】\n"
        f"{city_line}\n"
        "- 请你先问清楚我关键的细节（比如事情经过、有没有合同或证据、涉及多少钱、"
        "拖了多久、对方是什么单位等），再给我建议。\n\n"
        "【请帮我】\n"
        "1. 我这种情况，最该找哪个部门？打什么电话？"
        "（如 12333 / 12345 / 12315 / 12348 / 110、劳动监察大队、劳动仲裁委等，"
        "结合我的问题给准确）\n"
        "2. 我具体该怎么操作？分步骤讲——先做什么、准备什么材料证据、去哪里办、"
        "能不能线上办。\n"
        f"3. 有没有时效限制（比如劳动仲裁时效 1 年）？相关法律依据是什么（{s['law']}）？\n"
        f"4. {local}有没有我该知道的本地政策或更划算的做法？\n"
        "5. 综合看，我现在第一步最该干什么？\n\n"
        "要求：站在我的利益最大化角度，给具体、能照着做的建议，别讲空话，"
        "也别不管不顾地鼓励我去硬刚。"
    )


# ============================================================
# 反诈骗（按钮墙）：让 AI 判断是否骗局 + 紧急止损
# ============================================================
FRAUD_TYPES = {
    "task_rebate": {
        "title": "刷单 / 兼职返利",
        "features": "先让你刷几单、返小额佣金建立信任，再要求大额任务或垫付；"
                    "或说「操作失误，要连做几单才能提现」。刷单本身违法，凡要先垫钱的兼职 = 骗。",
    },
    "loan_fee": {
        "title": "网贷 / 提额要先交钱",
        "features": "放款前要交「解冻费/保证金/工本费/验资」，或让你往自己账户打流水证明还款能力。"
                    "正规贷款放款前不收任何费用；凡先交钱的贷款 = 骗。",
    },
    "pig_butchering": {
        "title": "网恋带投资（杀猪盘）",
        "features": "网上认识的「高富帅/美女」嘘寒问暖建立感情，再透露「内幕/漏洞」带你到某投资或博彩平台赚大钱。"
                    "你看到的账户余额是假的，最后血本无归。",
    },
    "impersonate": {
        "title": "冒充客服 / 公检法",
        "features": "自称京东/微信/支付宝客服说你「注销校园贷/账户异常/理赔」，"
                    "或自称公检法说你「涉嫌洗钱/案件」要配合、转钱到「安全账户」、开屏幕共享。"
                    "真警察不会电话办案，没有所谓「安全账户」。",
    },
    "lottery_refund": {
        "title": "中奖 / 理赔先交钱",
        "features": "说你中奖或快递丢失要理赔，领钱前先交「税/手续费/公证费」，"
                    "或退款要你「刷流水恢复信用」。先要钱的中奖理赔 = 骗。",
    },
    "misc": {
        "title": "其他 / 我也说不准",
        "features": "说不清是哪类，但对方在要钱、要验证码、要屏幕共享，或催促威胁你不让挂电话、不让告诉家人。",
    },
}


def build_antifraud_prompt(key, city=""):
    """反诈场景 → 问 AI 提示词（让 AI 判断是否骗局 + 紧急止损 + 报警渠道）。"""
    f = FRAUD_TYPES.get(key)
    if not f:
        return "（未知场景）"
    city_line = (f"- 我所在的城市：{city}" if city
                 else "- 我所在的城市：（请先问我，或先按一般情况）")
    local = f"结合我所在城市 {city}，" if city else ""
    return (
        f"请以资深反诈民警的口吻，用大白话帮我判断。我怀疑遇到了【{f['title']}】类骗局。"
        "对方的情况、原话、或发来的链接/二维码如下（我会贴在下面）：\n\n"
        "【请在这里贴对方的话术、行为描述、或链接/二维码】\n\n"
        f"这类骗局的典型特征：{f['features']}\n\n"
        f"{city_line}\n\n"
        "【请帮我】\n"
        "1. 先判断：这大概率是不是骗局？依据是什么（对照上面的典型特征，一条条比对）？\n"
        "2. 如果是或存疑：我**现在绝对不能做什么**？"
        "（别转账、别给验证码/短信码、别开屏幕共享、别按对方说的操作、"
        "别退出官方 APP 去加对方私聊）\n"
        "3. 如果我已经转了钱 / 给了银行卡和验证码 / 开了屏幕共享："
        "**现在立刻怎么紧急止损**？（打银行客服冻结、96110、110——分步骤、抢时间）\n"
        "4. 怎么核实对方真伪？（通过官方 APP、官方客服电话、或 110 反查，"
        "千万别用对方提供的号码去「核实」）\n"
        f"5. {local}我该去哪里报警、怎么举报（96110 / 110 / 国家反诈中心 APP / 12321）？\n\n"
        "要求：宁可错杀不可放过——只要对方要钱、要验证码、要屏幕共享、催你或威胁你，"
        "就先按骗局处理：停止操作、止损、再核实。别讲空话，给我能立刻照做的步骤。"
    )


def build_current_situation_prompt(age, tier, wage, ins, housing, food,
                                  has_car, num_kids, support_elderly, savings, city="",
                                  children_by_age=None, family_monthly=0,
                                  has_partner=False, partner_wage=0, partner_ins=""):
    """处境解读 → 问 AI 的提示词（让 AI 详细诊断处境、给可执行建议，代替内置长解读）。
    family_monthly/has_partner/partner_wage/partner_ins 可选：界面有就传。"""
    car_cn = "有车（含养车成本）" if has_car else "无车"
    elder_cn = "需要赡养老人" if support_elderly else "暂不需要赡养老人"
    if num_kids:
        _segs = _normalize_children(children_by_age, num_kids)
        _desc = "、".join(f"{seg}{n}人" for seg, n in _segs.items())
        kids_cn = f"有 {num_kids} 个孩子" + (f"（{_desc}）" if _desc else "")
    else:
        kids_cn = "没孩子"
    savings_cn = f"{savings:,.0f} 元" if savings else "几乎没存款"
    city_line = (f"- 所在城市：{city}（等级 {tier}）" if city
                 else f"- 所在城市等级：{tier}（具体城市请结合该等级典型城市分析，或先问我）")
    extra_lines = ""
    if family_monthly:
        extra_lines += f"- 每月给老家：{family_monthly:,.0f} 元\n"
    if has_partner:
        pw_cn = f"伴侣月薪约 {partner_wage:,.0f} 元" + (f"（{partner_ins}）" if partner_ins else "")
        extra_lines += f"- {pw_cn}（家庭双收入）\n"
    return (
        "请以资深个人理财顾问和生活规划师的口吻，面向一个不太懂理财的普通劳动者，"
        "用大白话帮我分析处境、给可执行的建议。我的情况如下：\n\n"
        "【我的情况】\n"
        f"- 年龄：{age} 岁\n"
        f"- 月薪（税前）：{wage:,.0f} 元\n"
        f"- 社保：{ins}\n"
        f"- 住房：{housing}　饮食档次：{food}\n"
        f"- {car_cn}\n"
        f"- 家庭：{kids_cn}，{elder_cn}\n"
        f"{extra_lines}"
        f"- 目前存款：{savings_cn}\n"
        f"{city_line}\n\n"
        "【请帮我分析】\n"
        "1. 先帮我估算：按我的情况，每月大概能结余多少钱（还是入不敷出）？给估算和思路。\n"
        "2. 我的财务处境健康吗？最该警惕的风险是什么（如没存款抗不了意外、社保断缴"
        "影响养老、结余太少攒不下钱等）？\n"
        "3. 给我几条**能照着做**的建议——请区分哪些是我个人能改的（消费习惯、副业、"
        "技能），哪些是结构性的（城市、行业、政策）。别只说「努力攒钱」这种空话，"
        "也别把系统性问题全怪到我头上。\n"
        "4. 如果我想改善处境（增收 / 减支 / 换城市 / 提升技能），最现实、性价比最高的"
        "第一步是什么？\n"
        "5. 结合我所在地区，有没有我该知道的政策或补贴（如灵活就业社保补贴、公租房、"
        "个税专项扣除等）？\n\n"
        "要求：实事求是，不灌鸡汤，给具体能落地的建议。"
    )


def build_milestones_prompt(tier, wage, city="", profile=None):
    """人生三座山（结婚/养娃/养老）→ 问 AI 的提示词。
    年龄/家庭/存款等从 profile 的事实段带入。"""
    city_line = (f"- 所在城市：{city}（等级 {tier}）" if city
                 else f"- 所在城市等级：{tier}")
    return (
        "请以资深生活规划师的口吻，面向普通劳动者，用大白话帮我算清楚「人生三座山」"
        "（结婚、养娃、养老）大概要花多少钱、我该怎么准备。我的情况如下：\n\n"
        "【我的情况】\n"
        f"- 月薪：{wage:,.0f} 元\n"
        f"{city_line}\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 先问清楚我最关心哪座山（结婚 / 养娃 / 养老）以及细节——比如结婚的话"
        "有没有彩礼/婚房压力；养娃的话孩子多大、想走公办还是民办；养老的话打算几岁退、"
        "社保缴了多少——然后再估算要花多少钱。\n"
        "2. 按我的收入和所在城市，攒够这笔钱大概要多久？现实不现实？\n"
        "3. 有没有省钱也能办成的现实办法（公办、补贴、集体办、平替方案）？\n"
        "4. 我现在每月该存多少、怎么存，才不至于到时候抓瞎？\n"
        "5. 结合我所在地区，有没有相关的政策、补贴或低门槛途径？\n\n"
        "要求：实事求是，区分我能改变的和政策/社会层面的，不灌鸡汤。"
    )


def build_compare_prompt(tier_a, tier_b, wage, target_city="", housing="合租单间",
                        food="普通", has_car=False, insurance="在职（单位缴）"):
    """城市加减法 → 问 AI 的提示词。target_city 为用户补充的目标具体城市名。"""
    b_line = (f"- 想去的目标城市：{target_city}（等级 {tier_b}）" if target_city
              else f"- 想去的目标城市：等级 {tier_b}（具体城市名我稍后补充，请先问我）")
    life_line = (f"- 住房方式：{housing}　饮食档次：{food}　"
                 f"{'有车' if has_car else '无车'}　社保：{insurance}")
    return (
        "请以资深职业与生活规划师的口吻，面向普通劳动者，用大白话帮我判断「换个城市值不值」。"
        "我的情况如下：\n\n"
        "【我的情况】\n"
        f"- 月薪：{wage:,.0f} 元\n"
        f"- 现在城市：等级 {tier_a}（具体城市名请先问我）\n"
        f"{b_line}\n"
        f"{life_line}\n\n"
        "【请帮我】\n"
        "1. 先问清楚我两边的具体城市名，然后对比这两座城市：生活成本（房租、吃饭、交通）、"
        "工资水平、就业机会、买房 / 落户难度。\n"
        "2. 按我的收入，在两个城市分别能结余多少？生活质量差别大吗？\n"
        "3. 换到目标城市，我的工资大概能涨 / 跌多少？多久能回本（搬家成本、过渡期没收入）？\n"
        "4. 除了钱，还有哪些该考虑的（离家远近、社保转移、孩子教育、人脉等）？\n"
        "5. 综合看，我这种情况换城市值不值？有什么风险和注意事项？\n\n"
        "要求：结合两座城市的真实情况给具体、现实的判断，别只说「大城市机会多」这种空话。"
    )


def build_injury_prompt(city, grade, monthly_wage, profile=None):
    """工伤赔偿 → 问 AI 的提示词（让 AI 确认赔偿项目 + 讲认定/鉴定流程）。"""
    return (
        "请以资深工伤与劳动法律师的口吻，用大白话帮我。我在工作中受了伤，"
        "想搞清楚能赔多少、怎么走流程。情况如下：\n\n"
        "【我的情况】\n"
        f"- 所在城市：{city}\n"
        f"- 伤残等级（劳动能力鉴定）：{grade} 级（若还没鉴定，请先问我伤情帮我预估级别）\n"
        f"- 受伤前 12 个月平均月工资：{monthly_wage:,.0f} 元\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 按国家《工伤保险条例》，我这个等级能拿到哪些赔偿？"
        "（一次性伤残补助金、伤残津贴、一次性工伤医疗/就业补助金等）逐项算给我看。\n"
        "2. 我所在省/市有没有额外标准或差异？\n"
        "3. 工伤认定完整流程：单位多久内申报、单位不报我怎么办、去哪认定、多久出结果。\n"
        "4. 劳动能力鉴定怎么申请、对评级不服怎么办。\n"
        "5. 治疗期间（停工留薪期）工资怎么发、医疗费谁出。\n"
        "6. 如果单位没缴工伤保险，我该找谁、怎么办。\n\n"
        "要求：结合我所在地的规定，给具体金额和步骤，别讲空话。"
    )


# ============================================================
# 自检（原有保持不变，末尾追加城市对比测试）
# ============================================================
# ============================================================
# 住房决策（买 vs 租 / 公积金额度 / 利率压力测试）
# 注意：房价/利率波动大，结果均为估算，务必结合「问 AI」查最新行情
# ============================================================

def _money(x):
    """金额简写：≥1万显示 'X.X 万'，否则 'X,XXX 元'。供结果区富文本段落用。"""
    return f"{x/10000:.1f} 万" if abs(x) >= 10000 else f"{x:,.0f} 元"


def _profile_brief(profile):
    """从档案 dict 提取客观个人情况（年龄/健康/社保/家庭/存款/负债），拼一段供提示词用。

    只放用户自填的**事实**（确认性信息），不含任何工具估算——提示词是给 AI 的，
    工具算的数字本身就不准，塞进去反而误导 AI。profile 为空/None 或无可填项时返回空串。
    """
    if not profile:
        return ""
    p = profile
    bits = []
    age = p.get("age")
    gender = p.get("gender")
    if age:
        line = f"年龄 {age} 岁"
        if gender:
            line += f"（{gender}）"
        health = p.get("health")
        if health and "健康" not in str(health):
            line += f"，{health}"
        bits.append(line)
    elif gender:
        bits.append(f"性别：{gender}")
    ins = p.get("insurance")
    if ins:
        bits.append(f"社保：{ins}")
    fam = []
    if p.get("has_partner"):
        pw = p.get("partner_wage")
        fam.append("有伴侣" + (f"（月薪约 {pw}）" if pw not in (None, "", 0) else ""))
    nc = p.get("num_children")
    if nc:
        fam.append(f"{nc} 个孩子")
    if p.get("support_elderly"):
        fam.append("需赡养老人")
    if fam:
        bits.append("家庭：" + "、".join(fam))
    sav = p.get("savings")
    if sav not in (None, "", 0):
        bits.append(f"现有存款约 {sav} 元")
    debts = []
    m = p.get("mortgage_monthly")
    if m not in (None, "", 0):
        debts.append(f"房贷 {m}/月")
    cl = p.get("car_loan_monthly")
    if cl not in (None, "", 0):
        debts.append(f"车贷 {cl}/月")
    if debts:
        bits.append("现有月供负债：" + "、".join(debts))
    if not bits:
        return ""
    return "【我的其他情况（个人档案）】\n- " + "；".join(bits) + "\n\n"


def compare_buy_rent(tier, years=10, house_area=90, down_ratio=0.3,
                     commercial_rate=None, fund_rate=None, rent_monthly=None,
                     loan_years=30):
    """买 vs 租 N 年成本对比（不预测房价涨跌，按「房价不变」中性估算）。

    买房净成本 = 住 N 年还的贷款利息（本金通过房子按买时价收回）。
    即：房价不涨不跌时，买房的真正代价就是利息；若房价下跌，买房还要额外亏跌幅。
    租房净成本 = 月租 × 12 × 年数（不假设租金增长）。
    """
    prof = D.TIER_PROFILE.get(tier) or D.TIER_PROFILE["三线"]
    cf = D.city_factor(tier)
    house_price = prof["house_price"] * house_area          # 总价（按当前价）
    downpay = house_price * down_ratio
    loan = house_price - downpay
    cr = commercial_rate if commercial_rate is not None else D.HOUSING_FUND["commercial_rate"]
    fr = fund_rate if fund_rate is not None else D.HOUSING_FUND["first_rate"]
    fund_max = D.HOUSING_FUND["max_loan"].get(tier, 400000)
    fund_part = min(loan, fund_max)                         # 组合贷：公积金用满
    comm_part = loan - fund_part
    loan_months = loan_years * 12
    live_months = years * 12

    m_fund = _monthly_payment(fund_part, fr, loan_months) if fund_part > 0 else 0
    m_comm = _monthly_payment(comm_part, cr, loan_months) if comm_part > 0 else 0
    monthly = m_fund + m_comm
    total_paid = downpay + monthly * live_months            # N 年现金流出
    # N 年后剩余本金（组合贷分别）
    rem_fund = _remaining_principal(fund_part, fr, loan_months, live_months) if fund_part > 0 else 0
    rem_comm = _remaining_principal(comm_part, cr, loan_months, live_months) if comm_part > 0 else 0
    remaining = rem_fund + rem_comm
    paid_principal = loan - remaining                       # N 年已还本金
    interest_paid = monthly * live_months - paid_principal  # N 年还的利息 = 买房净成本
    buy_net = interest_paid

    if rent_monthly is None:
        rent_monthly = D.HOUSING["一居室整租"]["base"] * cf
    rent_total = rent_monthly * 12 * years                  # 不假设租金增长
    rent_net = rent_total
    diff = buy_net - rent_net

    note = (
        f"【买】{house_area}㎡ 总价约 {house_price:,.0f}，首付 {downpay:,.0f}（{down_ratio*100:.0f}%），"
        f"贷款 {loan:,.0f}（{loan_years} 年，公积金 {fund_part:,.0f}@{fr*100:.2f}% + 商贷 {comm_part:,.0f}@{cr*100:.2f}%），"
        f"月供约 {monthly:,.0f}。\n"
        f"   住 {years} 年共还月供 {monthly*live_months:,.0f}，其中利息约 {interest_paid:,.0f}"
        f"（本金通过房子按买时价收回，不预测房价涨跌，所以买房的代价 ≈ 利息）。\n"
        f"【租】{tier} 一居室月租约 {rent_monthly:,.0f}，{years} 年共付租金 {rent_total:,.0f}。\n"
        f"→ 房价不涨不跌时，{'买房（利息成本）更低' if diff < 0 else '租房更低'}约 {abs(diff):,.0f} 元。"
    )
    note += ("\n\n⚠️ 关键提醒：这是「房价不涨不跌」的中性估算。当前多数城市房价在跌"
             "（除一线城市核心），若你买的房子跌了，买房还要额外亏掉跌幅——"
             "跌幅可能远超利息。务必用「问 AI」查你关注小区的真实行情再决定。")
    # 富文本段落（结果区 RichNote 渲染，层次比纯 note 文本清晰）
    if diff < 0:
        concl = {"t": f"房价不跌时 买房省 {_money(abs(diff))}\n", "tag": "big"}
    else:
        concl = {"t": f"房价不跌时 租房省 {_money(abs(diff))}\n", "tag": "bigbad"}
    rich = [
        {"t": f"买房成本（买 vs 租 · {years} 年）\n", "tag": "h"},
        {"t": f"总价 {_money(house_price)} · 首付 {_money(downpay)} · 贷款 {_money(loan)}\n", "tag": "normal"},
        {"t": f"月供 {_money(monthly)}/月\n", "tag": "buy"},
        {"t": f"住 {years} 年还利息 ≈ {_money(interest_paid)}  ← 买房真代价\n", "tag": "buy"},
        {"t": "\n租房成本\n", "tag": "h"},
        {"t": f"月租 {_money(rent_monthly)}/月\n", "tag": "rent"},
        {"t": f"{years} 年租金 ≈ {_money(rent_total)}\n", "tag": "rent"},
        {"t": "\n", "tag": "normal"},
        concl,
        {"t": "（房价若跌，买房还要额外亏掉跌幅）\n", "tag": "muted"},
        {"t": "\n⚠ 当前房价波动剧烈，以上为粗算估算（未含税费/维修/空置），"
         "点「问 AI」结合最新行情再判断。", "tag": "warn"},
    ]
    return {
        "tier": tier, "years": years, "house_price": house_price, "downpay": downpay,
        "loan": loan, "monthly": monthly, "buy_total_paid": total_paid,
        "interest_paid": interest_paid, "remaining": remaining, "residual": house_price,
        "buy_net": buy_net, "rent_monthly": rent_monthly, "rent_total": rent_total,
        "rent_net": rent_net, "diff": diff, "note": note, "rich": rich,
    }


def housing_fund_loan(tier, balance=0, monthly_contribution=0, years=30):
    """公积金可贷额度估算（三重限制取小）+ 月供。"""
    fund = D.HOUSING_FUND
    max_by_tier = fund["max_loan"].get(tier, 400000)
    by_balance = balance * fund["balance_multiplier"]
    by_contribution = monthly_contribution * 12 * years * 0.45 if monthly_contribution > 0 else None
    limits = [max_by_tier, by_balance]
    if by_contribution is not None:
        limits.append(by_contribution)
    eligible = max(0, min(limits))
    rate = fund["first_rate"]
    months = years * 12
    monthly = _monthly_payment(eligible, rate, months) if eligible > 0 else 0
    total_interest = monthly * months - eligible if eligible > 0 else 0
    note = (
        f"公积金可贷额 = min(当地上限 {max_by_tier:,.0f}，余额 {balance:,.0f}×{fund['balance_multiplier']}"
        f" = {by_balance:,.0f}"
        + (f"，月缴存 {monthly_contribution}×12×{years}×0.45 = {by_contribution:,.0f}" if by_contribution else "")
        + f") = {eligible:,.0f} 元。\n"
        f"按首套利率 {rate*100:.2f}%、{years} 年等额本息：月供约 {monthly:,.0f}，总利息约 {total_interest:,.0f}。"
    )
    note += ("\n⚠️ 各地公积金政策差异大（上限/倍数/缴存要求不同），以上是估算。"
             "用「问 AI」查你所在城市的最新公积金贷款政策更准。")
    rich = [
        {"t": "公积金可贷额度\n", "tag": "h"},
        {"t": f"可贷约 {_money(eligible)}\n", "tag": "big"},
        {"t": f"按首套利率 {rate*100:.2f}%、{years} 年等额本息\n", "tag": "normal"},
        {"t": f"月供约 {_money(monthly)}/月 · 总利息约 {_money(total_interest)}\n", "tag": "buy"},
        {"t": "\n⚠ 各地公积金政策差异大（上限/倍数/缴存要求不同），以上为估算，"
         "点「问 AI」查当地最新政策更准。", "tag": "warn"},
    ]
    return {
        "tier": tier, "eligible": eligible, "rate": rate, "years": years,
        "monthly": monthly, "total_interest": total_interest,
        "max_by_tier": max_by_tier, "by_balance": by_balance,
        "by_contribution": by_contribution, "note": note, "rich": rich,
    }


def rate_stress_test(principal, base_rate=0.0345, years=30):
    """利率压力测试：基准 / +0.5% / +1% 三档月供对比。"""
    months = years * 12
    rows = []
    for delta in (0, 0.005, 0.01):
        rate = base_rate + delta
        m = _monthly_payment(principal, rate, months)
        rows.append({"rate": rate, "monthly": m, "total_interest": m * months - principal})
    base_m = rows[0]["monthly"]
    note = (
        f"贷款 {principal:,.0f}、{years} 年等额本息：\n"
        f"· 利率 {base_rate*100:.2f}%：月供 {rows[0]['monthly']:,.0f}，总利息 {rows[0]['total_interest']:,.0f}\n"
        f"· 利率 {(base_rate+0.005)*100:.2f}%（+0.5%）：月供 {rows[1]['monthly']:,.0f}\n"
        f"· 利率 {(base_rate+0.01)*100:.2f}%（+1%）：月供 {rows[2]['monthly']:,.0f}\n"
        f"→ 利率每涨 1%，月供多约 {rows[2]['monthly']-base_m:,.0f} 元，"
        f"{years} 年多付利息 {rows[2]['total_interest']-rows[0]['total_interest']:,.0f} 元。"
    )
    note += "\n⚠️ 实际利率以你签贷款时的 LPR + 加点为准，会随央行调整变动。"
    rich = [
        {"t": f"利率压力测试（贷 {_money(principal)} / {years} 年）\n", "tag": "h"},
        {"t": f"· 利率 {base_rate*100:.2f}%：月供 {_money(rows[0]['monthly'])}\n", "tag": "normal"},
        {"t": f"· 利率 {(base_rate+0.005)*100:.2f}%（+0.5%）：月供 {_money(rows[1]['monthly'])}\n", "tag": "normal"},
        {"t": f"· 利率 {(base_rate+0.01)*100:.2f}%（+1%）：月供 {_money(rows[2]['monthly'])}\n", "tag": "buy"},
        {"t": "\n", "tag": "normal"},
        {"t": f"利率每涨 1%，月供多约 {_money(rows[2]['monthly']-base_m)}，"
         f"{years} 年多付利息 {_money(rows[2]['total_interest']-rows[0]['total_interest'])}\n", "tag": "bigbad"},
        {"t": "\n⚠ 实际利率以签贷款时的 LPR + 加点为准，会随央行调整变动。", "tag": "warn"},
    ]
    return {"principal": principal, "base_rate": base_rate, "years": years,
            "rows": rows, "note": note, "rich": rich}


def build_buy_rent_prompt(tier, years, area=90, down_ratio=0.3, city="", profile=None):
    city_line = (f"- 关注的城市：{city}（等级 {tier}）" if city
                 else f"- 城市等级：{tier}（请结合该等级典型城市，或先问我具体城市）")
    return (
        "请以资深房产分析师的口吻，用大白话帮我判断「买房还是租房」。我的情况：\n\n"
        "【我的情况】\n"
        f"{city_line}\n"
        f"- 对比年限：{years} 年　房产面积：{area}㎡　首付比例：{down_ratio*100:.0f}%\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 结合当地最新的房价、租金、房贷利率，算一算这几年买房 vs 租房大致花多少、哪个更划算。\n"
        "2. 现在的楼市行情，是买房的好时机吗？房价在涨还是跌？给出判断依据。\n"
        "3. 如果买房，首付、月供、税费、维修大概多少？我这种收入和存款能承受吗？\n"
        "4. 如果租房，有什么该注意的（租售比、租金走势、长租稳定性）？\n"
        "5. 综合看，你建议我买还是租？给明确倾向和理由，别和稀泥。\n\n"
        "要求：结合当地真实行情和最新政策。我知道楼市波动大，给判断时请说明依据和不确定性。"
    )


def build_fund_prompt(tier, balance, contrib=0, years=30, city="", profile=None):
    city_line = f"- 所在城市：{city}（等级 {tier}）" if city else f"- 城市等级：{tier}"
    contrib_line = f"- 月缴存：{contrib} 元　" if contrib not in (None, "", 0) else ""
    return (
        "请以熟悉各地公积金政策的顾问口吻，用大白话帮我算公积金贷款。我的情况：\n\n"
        "【我的情况】\n"
        f"{city_line}\n- 公积金账户余额约：{balance:,.0f} 元\n"
        f"{contrib_line}贷款年限：{years} 年\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 按我所在城市的公积金政策，我最多能贷多少？（当地最高额度、余额倍数、缴存要求都查一下）\n"
        "2. 首套/二套利率分别是多少？按我的额度算月供和总利息。\n"
        "3. 公积金贷款 vs 商业贷款，我能省多少利息？\n"
        "4. 申请公积金贷款要满足什么条件、怎么操作（缴存时长、连续性等）？\n"
        "5. 有没有我该知道的本地优惠政策（组合贷、人才补贴等）？\n\n"
        "要求：查当地最新公积金政策，给准确数字和能照着做的步骤。"
    )


def build_rate_stress_prompt(principal, base_rate, years=30, city="", profile=None):
    city_line = f"- 所在城市：{city}\n" if city else ""
    return (
        "请以资深房贷顾问的口吻，用大白话帮我做利率压力测试。我的情况：\n\n"
        "【我的情况】\n"
        f"- 计划贷款：{principal:,.0f} 元\n"
        f"- 当前参考利率：{base_rate*100:.2f}%　贷款年限：{years} 年\n"
        f"{city_line}\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 当前 LPR 和首套/二套房贷利率是多少？我这种能拿到什么利率？\n"
        "2. 利率再涨 0.5% 或 1%（或降），月供和总利息会变多少？\n"
        "3. 现在选固定利率还是 LPR 浮动更划算？为什么？\n"
        "4. 未来若加息压力大，有什么应对（提前还贷、转贷等）？\n"
        "5. 综合看，我现在该锁定利率还是等等？\n\n"
        "要求：结合当前 LPR 走势和政策，给明确建议。"
    )


# ============================================================
# 个税优化（年终奖单独 vs 合并 / 专项附加扣除）
# ============================================================

def bonus_tax_compare(annual_salary, bonus, annual_special=0, annual_social=0):
    """年终奖单独计税 vs 合并计税对比，给省税建议。

    annual_salary: 年税前工资（不含奖金，≈月薪×12）；bonus: 全年一次性奖金；
    annual_special: 年专项附加扣除合计；annual_social: 年个人五险一金。
    """
    if bonus <= 0:
        return {"error": "年终奖金额需大于 0。"}
    base_taxable = max(0, annual_salary - 60000 - annual_social - annual_special)
    base_tax, _, _ = D.calc_annual_income_tax(base_taxable)

    # 单独计税：奖金÷12 找月度税率
    monthly_eq = bonus / 12
    sep_rate, sep_quick = D.bonus_monthly_rate(monthly_eq)
    separate_tax = max(0, bonus * sep_rate - sep_quick)

    # 合并计税：奖金并入综合所得
    combined_taxable = base_taxable + bonus
    combined_total_tax, _, _ = D.calc_annual_income_tax(combined_taxable)
    combined_tax = combined_total_tax - base_tax

    saving = separate_tax - combined_tax   # 正=合并更省
    if saving > 0:
        recommend = "并入综合所得（合并计税）更省"
    elif saving < 0:
        recommend = "单独计税更省"
    else:
        recommend = "两种计税一样"

    note = (
        f"假设年工资 {annual_salary:,.0f}、年终奖 {bonus:,.0f}、"
        f"年专项扣除 {annual_special:,.0f}、年社保 {annual_social:,.0f}：\n"
        f"· 单独计税：奖金÷12={monthly_eq:,.0f} 对应税率 {sep_rate*100:.0f}%，年终奖纳税 {separate_tax:,.0f}。\n"
        f"· 合并计税：奖金并入年薪，全年综合所得纳税 {combined_total_tax:,.0f}"
        f"（其中奖金部分约 {combined_tax:,.0f}）。\n"
        f"→ {recommend}约 {abs(saving):,.0f} 元。"
    )
    note += ("\n⚠️ 年终奖单独计税优惠目前执行到 2027 年底，之后是否延续以当年政策为准；"
             "最终以个税 APP 年度汇算为准，或用「问 AI」结合最新政策确认。")
    return {
        "separate_tax": separate_tax, "combined_tax": combined_tax,
        "combined_total_tax": combined_total_tax, "base_tax": base_tax,
        "saving": saving, "recommend": recommend, "note": note,
    }


def special_deduction_hints(has_children=0, support_elderly=False,
                            has_loan=False, continuing_edu=False):
    """根据用户情况，提示可用 / 可能漏报的专项附加扣除（每条一句话）。"""
    hints = []
    if has_children:
        hints.append(f"子女教育：每个孩子 2000 元/月（你有 {has_children} 个 = {has_children*2000} 元/月），"
                     "孩子满 3 岁起就能申报，别漏。")
        hints.append("3 岁以下婴幼儿照护：每个 2000 元/月（孩子没满 3 岁的走这项，别和子女教育混）。")
    else:
        hints.append("子女教育 / 婴幼儿照护：有孩子的话每孩 2000 元/月，很多人没申报。")
    if support_elderly:
        hints.append("赡养老人：独生子女 3000 元/月、非独生按分摊（每人≤1500）。父母满 60 岁即可。")
    else:
        hints.append("赡养老人：父母任一方满 60 岁就能扣（独生 3000 元/月），达标了别忘报。")
    if has_loan:
        hints.append("住房贷款利息：首套 1000 元/月（最长 240 个月）。和住房租金二选一，不能同扣。")
    else:
        hints.append("住房租金：按城市 800~1500 元/月（和房贷利息二选一）。租房的别漏。")
    if continuing_edu:
        hints.append("继续教育：学历教育 400 元/月（最长 48 个月），职业资格证书取得当年扣 3600 元。")
    else:
        hints.append("继续教育：在考证/在读学历的话，可扣 400 元/月 或 取证当年 3600 元。")
    hints.append("大病医疗：年度医保目录内自付超 1.5 万的部分，最高扣 8 万/年（汇算时申报，留好票据）。")
    return hints


def build_tax_prompt(annual_salary, bonus, city="", special=0, social=0,
                     kids=0, elderly=False, loan=False, edu=False, profile=None):
    """个税优化 → 问 AI 的提示词。special/social 为月专项扣除/月社保；
    kids/elderly/loan/edu 为家庭情况（决定专项附加扣除）。"""
    city_line = f"- 所在城市：{city}\n" if city else ""
    family_bits = []
    if kids:
        family_bits.append(f"子女 {kids} 个")
    if elderly:
        family_bits.append("需赡养老人")
    if loan:
        family_bits.append("有首套房贷")
    if edu:
        family_bits.append("本人继续教育")
    family_line = ("- 家庭扣除情况：" + "、".join(family_bits) + "\n") if family_bits else ""
    dedu_line = ((f"- 月专项附加扣除合计：{special:,.0f} 元　月社保个人部分：{social:,.0f} 元\n")
                 if (special or social) else "")
    return (
        "请以熟悉个税政策的税务顾问口吻，用大白话帮我做税务优化。我的情况：\n\n"
        "【我的情况】\n"
        f"- 年税前工资约 {annual_salary:,.0f} 元\n"
        f"- 年终奖约 {bonus:,.0f} 元\n"
        f"{dedu_line}"
        f"{family_line}"
        f"{city_line}\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 我的年终奖该单独计税还是并入综合所得？分别算给我看，哪个省、省多少。\n"
        "2. 我能享受哪些专项附加扣除？每项能扣多少、我符不符合、怎么在个税 APP 申报？\n"
        "3. 有没有我容易漏的扣除（赡养老人、继续教育、大病医疗、房租/房贷）？\n"
        "4. 按我的情况，全年大概交多少税、到手多少？有没有合法节税空间？\n"
        "5. 结合最新个税政策（起征点、专项扣除标准、年终奖优惠延续到何时），给明确建议。\n\n"
        "要求：算给我看（给税额），给能在个税 APP 照着操作的步骤。"
    )


# ============================================================
# 本地救助对照（低保 / 低保边缘 / 特困）
# ============================================================

def check_relief(city, per_capita_income, family_size=1, asset=None):
    """对照当地低保/边缘/特困，判断「符合/接近/不符」。

    city: 城市；per_capita_income: 家庭人均月收入（元）；
    family_size: 家庭人数（展示用）；asset: 可选家庭人均金融资产（元）。
    """
    import relief_data as RL
    import rights_data as R
    dibao, db_note, db_est = RL.get_dibao_for_city(city)
    if dibao is None:
        return {"error": db_note}
    income = per_capita_income
    edge = dibao * RL.DIBAO_EDGE_RATIO        # 低保边缘线（1.5 倍）
    edge_max = dibao * RL.DIBAO_EDGE_RATIO_MAX  # 放宽至 2 倍

    if income < dibao:
        matched, head, color = "符合低保", (
            f"✅ 人均月收入 {income:,.0f} 元 < 当地低保 {dibao} 元/月（{db_note}）"), "surplus"
        detail = (f"→ 大概率符合低保，可领差额补助（补到 {dibao} 元/月）。"
                  "\n申请：户籍地街道/乡镇民政，或 12345 转民政；带身份证、收入/财产证明。")
    elif income < edge:
        matched, head, color = "低保边缘家庭", (
            f"⚠️ 人均收入 {income:,.0f} 在低保边缘区间（{dibao} ~ {edge:,.0f} 元）"), "accent"
        detail = ("→ 属低保边缘家庭，可享专项救助：" + "、".join(RL.DIBAO_EDGE_ASSISTANCE)
                  + f"\n（边缘线 = 低保 × 1.5 = {edge:,.0f}，部分地区放宽至 2 倍 = {edge_max:,.0f}）")
    elif income < edge_max:
        matched, head, color = "距边缘线较近", (
            f"人均收入 {income:,.0f}，距低保边缘线（{edge:,.0f}）差 {income - edge:,.0f} 元"), "neutral"
        detail = "→ 暂不符合，但若收入下降或遇大病/失业，可申请临时救助（低保 × 2~12 倍）。"
    else:
        matched, head, color = "不符合", (
            f"人均收入 {income:,.0f} 明显高于低保边缘线（{edge:,.0f}），不符合低保。"), "deficit"
        detail = "→ 工具只是粗算，最终以当地民政认定为准。"

    prop_hint = ""
    if asset is not None and asset > 0:
        prov = R.CITY_TO_PROVINCE.get(city, city)
        limit = RL.PROPERTY_LIMIT.get(prov, RL.PROPERTY_LIMIT_COMMON)
        fin = limit.get("金融资产人均") or limit.get("金融资产", "人均不超过当地年低保×2~4倍")
        over = asset > dibao * 36
        prop_hint = (f"\n\n【财产提醒】当地金融资产限制：{fin}。你填的人均金融资产 {asset:,.0f} 元，"
                     + ("可能因财产超标影响认定，以民政核实为准。" if over else "未明显超标。"))
    note = head + "\n" + detail + prop_hint + "\n\n【临时救助】遇急难（大病/意外）可申请，约低保月标准 × 2~12 倍。"
    if db_est:
        note += f"\n\n⚠️ {db_note}（数据为估算，请用「问 AI」查当地最新标准）。"
    return {"dibao": dibao, "edge": edge, "edge_max": edge_max,
            "tier_matched": matched, "head": head, "color": color,
            "note": note, "estimated": db_est}


def build_assistance_prompt(city, per_capita_income, family_info="", asset=None, profile=None):
    """本地救助 → 问 AI 的提示词。asset 为家庭人均金融资产（财产限制判断用）。"""
    asset_line = f"- 家庭人均金融资产：{asset:,.0f} 元\n" if asset else ""
    return (
        "请以民政/社会救助专家的口吻，用大白话帮我判断能申请什么救助。我的情况：\n\n"
        "【我的情况】\n"
        f"- 所在城市：{city}\n- 家庭人均月收入约：{per_capita_income:,.0f} 元\n"
        f"{asset_line}"
        f"- 家庭情况：{family_info or '（请先问我家庭人数、是否有老小病残、现有保障）'}\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 按我所在城市的最新标准，我符合低保 / 低保边缘 / 特困哪一档？能领多少？\n"
        "2. 怎么申请？去哪里（街道/乡镇民政）、带什么材料、流程几步、多久能批？\n"
        "3. 财产限制（金融资产/车辆/房产）我过不过？\n"
        "4. 除了低保，我还能申请什么（临时救助/医疗救助/教育救助/公租房/残疾人补贴等）？\n"
        "5. 申请被拒了怎么办？有没有复议或投诉渠道？\n\n"
        "要求：查当地最新政策和标准，给能照着做的步骤。"
    )


# ============================================================
# 医保就医（住院报销估算 + 提示词）
# ============================================================

def estimate_medical_cost(city, identity="职工", cost=50000, remote="none", retired=False):
    """住院报销估算（基本医保 + 大病 + 异地），委托 medical_data。"""
    import medical_data as M
    return M.estimate_inpatient(city, identity, cost, remote, retired)


def build_medical_prompt(city, identity, cost, retired=False, remote="none", profile=None):
    """医保报销 → 问 AI 的提示词。remote 为就医方式键（none/filed/unfiled）。"""
    _DISP = {"none": "本地就医", "filed": "异地已备案", "unfiled": "异地未备案"}
    return (
        "请以医保政策专家的口吻，用大白话帮我算医保报销。我的情况：\n\n"
        "【我的情况】\n"
        f"- 参保城市：{city}\n- 医保类型：{identity}{'（退休）' if retired else ''}\n"
        f"- 就医方式：{_DISP.get(remote, '本地就医')}\n"
        f"- 预估住院费用：{cost:,.0f} 元（三级医院）\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 基本医保 + 大病保险，我大概能报多少、自付多少？按当地最新政策算给我看。\n"
        "2. 我要不要先办异地备案/转诊？怎么办（线上步骤）？不办会少报多少？\n"
        "3. 我有高血压/糖尿病等慢性病，能不能认定门诊慢特病？认定后门诊能多报多少？\n"
        "4. 我用的药如果是乙类/谈判药，要先自付多少？怎么查药品在不在医保目录？\n"
        "5. DRG 改革对我这种病/治疗方式有影响吗？该选什么医院？\n\n"
        "要求：按当地医保局最新政策，给能照着做的步骤。"
    )


# ============================================================
# 债务健康仪表盘
# ============================================================

def assess_debt_health(total_debt, monthly_income, monthly_pay, avg_apr=0.18):
    """债务健康评估：负债率、月供比、还清月数、风险等级。

    total_debt: 总负债；monthly_income: 月收入；monthly_pay: 每月能还；avg_apr: 平均年化（小数）。
    """
    import math
    if total_debt <= 0:
        return {"error": "总负债需大于 0。"}
    if monthly_income <= 0:
        return {"error": "月收入需大于 0。"}

    annual_income = monthly_income * 12
    debt_ratio = total_debt / annual_income          # 负债 / 年收入
    pay_ratio = monthly_pay / monthly_income          # 月供 / 月收入
    r = avg_apr / 12
    monthly_interest = total_debt * r
    runaway = monthly_pay <= monthly_interest          # 还款盖不住利息 = 失控

    months = None
    if runaway:
        level, color = "危险：还款盖不住利息，越还越多", "deficit"
    else:
        months = math.ceil(-math.log(1 - total_debt * r / monthly_pay) / math.log(1 + r))
        if debt_ratio > 0.5 or pay_ratio > 0.5:
            level, color = "危险（负债/月供占收入过高）", "deficit"
        elif debt_ratio > 0.3 or pay_ratio > 0.3:
            level, color = "警戒", "accent"
        else:
            level, color = "健康", "surplus"

    parts = [
        f"负债收入比：{debt_ratio*100:.0f}%（总负债 {total_debt:,.0f} ÷ 年收入 {annual_income:,.0f}）"
        f"——{'偏高' if debt_ratio > 0.3 else '可控'}（经验线：<30% 健康、30~50% 警戒、>50% 危险）。",
        f"月供占收入：{pay_ratio*100:.0f}%——{'吃紧' if pay_ratio > 0.3 else '可承受'}"
        f"（月还款最好不超月收入 30%，超 50% 一笔意外就断供）。",
    ]
    if runaway:
        parts.append(f"⚠️ 你每月还 {monthly_pay:,.0f}，但月利息约 {monthly_interest:,.0f}——"
                     f"还款盖不住利息，债务会越滚越多、永远还不清。必须增收或协商减免/债务重组。")
    elif months is not None:
        parts.append(f"按每月还 {monthly_pay:,.0f}（年化 {avg_apr*100:.0f}%），约 {months} 个月（{months/12:.1f} 年）还清，"
                     f"总利息约 {monthly_pay * months - total_debt:,.0f} 元。")
    parts.append("建议：优先还高息债（雪崩法）、必要时和债权方协商分期/减免、砍非必要开支、"
                 "考虑债务重组；千万别以贷养贷。")
    return {"debt_ratio": debt_ratio, "pay_ratio": pay_ratio, "months": months,
            "runaway": runaway, "monthly_interest": monthly_interest,
            "level": level, "color": color, "note": "\n".join(parts)}


def build_debt_health_prompt(total_debt, monthly_income, monthly_pay, avg_apr, profile=None):
    return (
        "请以资深债务顾问的口吻，用大白话帮我评估债务健康、给摆脱债务的建议。我的情况：\n\n"
        f"- 总负债约：{total_debt:,.0f} 元\n- 月收入：{monthly_income:,.0f} 元\n"
        f"- 每月能还：{monthly_pay:,.0f} 元\n- 平均年化约：{avg_apr*100:.0f}%\n\n"
        + _profile_brief(profile) +
        "【请帮我】\n"
        "1. 我的负债健康吗？负债率/月供比算给我看，给明确评级。\n"
        "2. 按现在还款节奏，多久能还清？总利息多少？有没有更省的还法？\n"
        "3. 现在最该先做什么？（先还哪笔、要不要债务重组/协商减免、怎么增收）\n"
        "4. 该警惕什么？（以贷养贷、高息网贷、催收陷阱、征信影响）\n"
        "5. 实在还不上了，合法出路有哪些（调解/法律援助/个人破产试点）？\n\n"
        "要求：结合我的实际数字，给能照着做的步骤，别讲空话。"
    )


if __name__ == "__main__":
    print("=" * 60)
    print("计算器1：三线城市·普惠·顺产·居家养老")
    print("=" * 60)
    r1 = compute_life_cost("三线", "普惠")
    print(f"一生总成本: {D.fmt_money(r1['grand_total'])}")
    print("\n阶段小计:")
    for s in r1["stage_subtotals"]:
        print(f"  {s['stage']}: {s['amount']:>12,} 元 ({s['pct']}%)")

    print("\n" + "=" * 60)
    print("计算器1：一线城市·高端")
    print("=" * 60)
    r2 = compute_life_cost("一线", "高端")
    print(f"一生总成本: {D.fmt_money(r2['grand_total'])}")
    print(f"（是三线·普惠的 {r2['grand_total']/r1['grand_total']:.1f} 倍）")

    print("\n" + "=" * 60)
    print("计算器2：30岁·二线·月薪6000·合租·普通饮食·无车·在职")
    print("=" * 60)
    r3 = compute_current_situation(
        age=30, wage_pretax=6000, tier="二线", housing="合租单间",
        food_level="普通", has_car=False, insurance_mode="在职（单位缴）",
        num_children=0, support_elderly=False)
    print(f"月度生存成本: {r3['cost_total']:,} 元")
    print(f"五险一金: {r3['social_ins']:,} 元 | 个税: {r3['tax']:,} 元")
    print(f"到手收入: {r3['income_net']:,} 元")
    print(f"月结余: {r3['surplus']:,} 元")
    print("\n解读:")
    print(r3["interpretation"])

    # ---- 债务功能自检 ----
    print("\n" + "=" * 60)
    print("债务1：还款方式对比（本金1万 / 名义18% / 12期）")
    print("=" * 60)
    d1 = compare_loan_methods(10000, 0.18, 12)
    print(f"等额本息：月供 {d1['equal_payment']['monthly']:.0f}，"
          f"总利息 {d1['equal_payment']['total_interest']:.0f}，"
          f"真实年化 {d1['equal_payment']['annual_irr']*100:.1f}%")
    print(f"等本等息：月供 {d1['equal_principal_flat']['monthly']:.0f}，"
          f"总利息 {d1['equal_principal_flat']['total_interest']:.0f}，"
          f"真实年化 {d1['equal_principal_flat']['annual_irr']*100:.1f}%")
    print(f"（等本等息比等额本息多付利息 {d1['interest_diff']:.0f} 元）")

    print("\n" + "=" * 60)
    print("债务2：可承受负债上限（月结余2000 / 18% / 24期）")
    print("=" * 60)
    d2 = compute_affordable_debt(2000, 0.18, 24)
    print(f"月还款上限 {d2['max_monthly']:.0f}，可借本金上限 {d2['max_principal']:.0f}，"
          f"保守档 {d2['safe_principal']:.0f}")

    print("\n" + "=" * 60)
    print("债务3：雪球 vs 雪崩（信用卡3000@18%月还300 / 网贷10000@36%月还500，每月额外多还500）")
    print("=" * 60)
    debts = [
        {"name": "信用卡", "balance": 3000, "annual_rate": 0.18, "min_monthly": 300},
        {"name": "网贷", "balance": 10000, "annual_rate": 0.36, "min_monthly": 500},
    ]
    sb = simulate_debt_payoff(debts, "snowball", extra_monthly=500)
    av = simulate_debt_payoff(debts, "avalanche", extra_monthly=500)
    if sb.get("unpayable"):
        print(f"雪球失控：{sb['unpayable_reason']}")
    else:
        print(f"雪球法：{sb['total_months']} 月还清，总利息 {sb['total_interest']:.0f}")
    if av.get("unpayable"):
        print(f"雪崩失控：{av['unpayable_reason']}")
    else:
        print(f"雪崩法：{av['total_months']} 月还清，总利息 {av['total_interest']:.0f}")
    if not sb.get("unpayable") and not av.get("unpayable"):
        print(f"（雪崩比雪球省利息 {sb['total_interest']-av['total_interest']:.0f} 元）")
    bad = simulate_debt_payoff(
        [{"name": "高息贷", "balance": 10000, "annual_rate": 0.36, "min_monthly": 200}],
        "avalanche")
    print(f"\n失控用例（1万@36%月还200）："
          f"{'触发失控 ✓' if bad.get('unpayable') else '未触发 ✗'}")

    print("\n" + "=" * 60)
    print("债务4：以贷养贷螺旋（初始1万 / 年化24% / 24月 / 每月实还0）")
    print("=" * 60)
    d4 = simulate_loan_spiral(10000, 0.24, 24, 0)
    print(f"24个月后余额 {d4['final_balance']:.0f}，"
          f"{'翻倍用时' + str(d4['doubling_month']) + '月' if d4['doubled'] else '未翻倍'}，"
          f"止血线 {d4['breakeven_monthly']:.0f}/月")

    # ---- 劳动权益自检 ----
    print("\n" + "=" * 60)
    print("权益1：加班费反算（月薪6000 / 工作日40h / 休息日16h / 节假日8h）")
    print("=" * 60)
    e1 = compute_overtime_pay(6000, 40, 16, 8)
    print(f"时薪 {e1['hourly_wage']:.2f} 元，加班费合计 {e1['total_overtime']:,.0f} 元")
    for d in e1["detail"]:
        print(f"  {d['type']} {d['hours']}h × {d['rate']}倍 = {d['pay']:,.0f}")

    print("\n" + "=" * 60)
    print("权益2：最低工资对照（月薪3500 / 三线）")
    print("=" * 60)
    e2 = compute_min_wage_check(3500, "三线")
    print(f"当地最低工资 {e2['min_wage']} 元，月薪 {e2['monthly_wage']} 元，"
          f"{'低于最低工资 ⚠' if e2['below'] else '高于最低线'}（{e2['ratio']:.1%}）")
    low = compute_min_wage_check(1800, "三线")
    print(f"违法用例（月薪1800/三线）：{'触发违法 ⚠' if low['below'] else '未触发 ✗'}")

    print("\n" + "=" * 60)
    print("权益3：维权现实评估（被欠8000 / 在职 / 证据部分）")
    print("=" * 60)
    e3 = assess_overtime_claim(8000, employed=True, evidence="部分")
    print(f"判定：{e3['verdict']}（{e3['verdict_level']}）  胜算：{e3['win_chance']}")
    print(f"对比（证据几乎没有）：{assess_overtime_claim(8000, True, '几乎没有')['verdict']}")
    print(f"对比（被欠1500/在职/部分）：{assess_overtime_claim(1500, True, '部分')['verdict']}")
    print(f"对比（被欠8000/已离职/充分）：{assess_overtime_claim(8000, False, '充分')['verdict']}")

    print("\n" + "=" * 60)
    print("权益4：生成「问AI的加班费提示词」（月薪6000/在职/部分/北京）")
    print("=" * 60)
    print(build_overtime_prompt(6000, 40, 16, 8, 0, 3, True, "部分", "北京"))
