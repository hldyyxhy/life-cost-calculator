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
                              num_children=0, child_age_group="中小学（6-18岁）",
                              support_elderly=False, has_housing_deduction=False,
                              has_continuing_education=False,
                              support_family_monthly=0):
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
        child_age_group:     子女年龄段
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
        cost_rows.append({"item": item, "amount": round(amount), "note": note})
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

    cost_total = sum(r["amount"] for r in cost_rows)

    # ---------- 收入端：个税 ----------
    # 专项附加扣除
    special = 0
    special_detail = []
    if num_children > 0:
        dedu_key = ("3岁以下婴幼儿照护" if child_age_group.startswith("3岁以下")
                    else "子女教育（3岁至博士）")
        amt = D.SPECIAL_DEDUCTIONS[dedu_key]["amount"] * num_children
        special += amt
        special_detail.append(f"{dedu_key} {num_children}孩 = {amt:,}")
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
        insurance_mode, child_age_group, support_family_monthly
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


def _build_interpretation(age, wage, tier, cost_total, social_ins, tax,
                          income_net, surplus, surplus_rate, house_saving_years, survival_baseline,
                          special_detail, num_children, food_level,
                          insurance_mode, child_age_group, support_family_monthly=0):
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
        survive_months = surplus / survival_baseline
        if survive_months > 0:
            lines.append(f"   你目前的月结余按底线标准可多活 {survive_months:.1f} 个月。")

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

    # 孩子抚养成本提示
    if num_children > 0:
        care_base = D.CHILD_CARE_MONTHLY_BASE.get(child_age_group, 1500)
        child_month = care_base * cf * num_children
        lines.append("")
        lines.append(f"█ 你有 {num_children} 个孩子（{child_age_group}）：")
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
                   has_car=False, num_children=0,
                   support_elderly=False, support_family_monthly=0):
    """对比在当前城市和目标城市的生活成本与生活质量。"""
    estimated_wage = _estimate_target_wage(wage, current_tier, target_tier)

    common = dict(housing=housing, food_level=food_level, has_car=has_car,
                  insurance_mode=insurance_mode, num_children=num_children,
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

    return {
        "current": current,
        "target": target,
        "estimated_wage": round(estimated_wage),
        "income_diff": round(income_diff),
        "cost_diff": round(cost_diff),
        "surplus_diff": round(surplus_diff),
        "comparison_text": "\n".join(lines),
    }


# ============================================================
# 自检（原有保持不变，末尾追加城市对比测试）
# ============================================================
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
