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
    if r == 0:
        ep_monthly = principal / n
    else:
        ep_monthly = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
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
        return {"error": "你目前月结余 ≤ 0（入不敷出），不具备新增负债能力。"
                         "先想办法提高收入或砍掉非必要开支，再谈借钱。"}
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


def build_loan_apr_prompt(principal, monthly, periods):
    """真实年化反算 → 问 AI 的提示词（判断是否高利贷、维权）。"""
    return (
        "请以资深金融消费者权益保护专家的口吻，用大白话帮我判断这笔贷款正不正常、"
        "我有没有被坑。情况如下：\n\n"
        "【这笔贷款】\n"
        f"- 借款本金：{principal:,.0f} 元\n"
        f"- 每月还款：{monthly:,.0f} 元\n"
        f"- 期数：{periods} 个月\n\n"
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


def build_compare_methods_prompt(principal, apr_pct, periods):
    """还款方式对比 → 问 AI 的提示词。"""
    return (
        "请以资深金融顾问的口吻，用大白话帮我讲清楚两种还款方式的区别，我快被绕晕了。"
        "情况如下：\n\n"
        "【这笔贷款】\n"
        f"- 本金：{principal:,.0f} 元\n"
        f"- 名义年化：{apr_pct:.1f}%（机构报的价）\n"
        f"- 期数：{periods} 个月\n\n"
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


def build_affordable_debt_prompt(surplus, apr_pct, periods, income=None):
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


def build_spiral_prompt(init, apr_pct, months, pay):
    """以贷养贷螺旋 → 问 AI 的提示词。"""
    return (
        "请以资深债务顾问的口吻，用大白话帮我判断我是不是陷入了「以贷养贷」的恶性循环、"
        "该怎么脱困。情况如下：\n\n"
        "【我的情况】\n"
        f"- 目前欠着：{init:,.0f} 元\n"
        f"- 这笔债的年化：{apr_pct:.1f}%\n"
        f"- 每月我实际能还：{pay:,.0f} 元\n\n"
        "【请帮我】\n"
        "1. 按这个还款力度，我的债务是在涨还是在降？大概多久会翻倍？给计算。\n"
        "2. 我算不算陷入了「借新还旧 / 以贷养贷」的螺旋？严重程度如何？\n"
        "3. 要让债务停止增长，我每月至少得还多少（止血线）？\n"
        "4. 给我一个现实可行的脱困方案：怎么止血、怎么逐步还清、要不要债务重组 / 协商、"
        "找什么帮助。\n"
        "5. 如果是网贷 / 信用卡，有没有我该知道的维权或救济渠道（如暴力催收投诉）？\n\n"
        "要求：实事求是，给我能照着做的出路，别只吓唬我。"
    )


def build_min_wage_prompt(wage, tier, city=""):
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
        "【请帮我】\n"
        "1. 我所在地区目前的最低工资标准大概是多少？我的工资有没有低于这个底线？\n"
        "2. 如果低于，这是违法的——法律依据是什么（如《劳动法》第 48 条）？\n"
        "3. 就算没低于，我的工资在当地处在什么水平？议价空间大不大？\n"
        "4. 如果我想争取合理工资或维权，具体怎么做（找谁、打什么电话、准备什么）？\n"
        "5. 针对我所在地区，有没有我该知道的本地规定？\n\n"
        "要求：站在我的利益角度，给现实、能照着做的建议。"
    )


def build_unemployment_prompt(city=""):
    """失业金（外包给 AI 查当地标准）→ 问 AI 的提示词。"""
    city_line = (f"- 我所在的城市：{city}" if city
                 else "- 我所在的城市：（我稍后告诉你，请先问我）")
    return (
        "请以资深社保 / 劳动保障专家的口吻，用大白话帮我算清楚：我被裁（或快失业）了，"
        "能领多少失业金、领多久、怎么领。情况如下：\n\n"
        "【我的情况】\n"
        f"{city_line}\n"
        "- 社保（失业保险）缴费年限：（请问我，或我稍后补充）\n"
        "- 上份工作的月工资：（请问我）\n"
        "- 离职原因：是公司辞退 / 合同到期不续签 / 协商解除 / 还是个人原因？"
        "（请问我，这关系到能不能领）\n\n"
        "【请帮我】\n"
        "1. 先问清楚我上面还缺的信息，然后按我所在城市的最新规定，算我大概能领多少失业金、"
        "能领几个月。\n"
        "2. 领失业金需要满足什么条件？我的情况符不符合？\n"
        "3. 具体怎么申领？去哪里办、带什么材料、能线上办吗？\n"
        "4. 领失业金期间，我的医保 / 养老保险怎么办？有没有其他配套待遇？\n"
        "5. 除了失业金，我还能不能领别的（如失业补助金、临时救助、就业服务）？\n\n"
        "要求：结合我所在城市的最新政策，给具体、能照着办的步骤。"
    )


def build_subsidy_prompt(city=""):
    """灵活就业社保补贴（4050，外包给 AI）→ 问 AI 的提示词。"""
    city_line = (f"- 我所在的城市：{city}" if city
                 else "- 我所在的城市：（我稍后告诉你，请先问我）")
    return (
        "请以资深社保 / 就业援助专家的口吻，用大白话帮我搞清楚：我能不能领「灵活就业社保补贴」"
        "（有的地方叫 4050 补贴、就业困难人员社保补贴），能补多少、怎么申请。"
        "情况如下：\n\n"
        "【我的情况】\n"
        f"{city_line}\n"
        "- 我的年龄、性别：（请问我，补贴对年龄有要求）\n"
        "- 我现在是不是以灵活就业身份自己缴社保？（请问我）\n"
        "- 我有没有被认定为「就业困难人员」？（请问我）\n\n"
        "【请帮我】\n"
        "1. 先问清楚我上面缺的信息，然后按我所在城市的最新规定，判断我能不能享受这个补贴。\n"
        "2. 如果能，补贴标准大概多少（补社保缴费的百分之几、每月 / 每年封顶多少）？能享受多久？\n"
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


def build_current_situation_prompt(age, tier, wage, ins, housing, food,
                                  has_car, num_kids, support_elderly, savings, city=""):
    """处境解读 → 问 AI 的提示词（让 AI 详细诊断处境、给可执行建议，代替内置长解读）。"""
    car_cn = "有车（含养车成本）" if has_car else "无车"
    elder_cn = "需要赡养老人" if support_elderly else "暂不需要赡养老人"
    kids_cn = f"有 {num_kids} 个孩子" if num_kids else "没孩子"
    savings_cn = f"{savings:,.0f} 元" if savings else "几乎没存款"
    city_line = (f"- 所在城市：{city}（等级 {tier}）" if city
                 else f"- 所在城市等级：{tier}（具体城市请结合该等级典型城市分析，或先问我）")
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


def build_milestones_prompt(tier, wage, city=""):
    """人生三座山（结婚/养娃/养老）→ 问 AI 的提示词。"""
    city_line = (f"- 所在城市：{city}（等级 {tier}）" if city
                 else f"- 所在城市等级：{tier}")
    return (
        "请以资深生活规划师的口吻，面向普通劳动者，用大白话帮我算清楚「人生三座山」"
        "（结婚、养娃、养老）大概要花多少钱、我该怎么准备。我的情况如下：\n\n"
        "【我的情况】\n"
        f"- 月薪：{wage:,.0f} 元\n"
        f"{city_line}\n\n"
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


def build_compare_prompt(tier_a, tier_b, wage, target_city=""):
    """城市加减法 → 问 AI 的提示词。target_city 为用户补充的目标具体城市名。"""
    b_line = (f"- 想去的目标城市：{target_city}（等级 {tier_b}）" if target_city
              else f"- 想去的目标城市：等级 {tier_b}（具体城市名我稍后补充，请先问我）")
    return (
        "请以资深职业与生活规划师的口吻，面向普通劳动者，用大白话帮我判断「换个城市值不值」。"
        "我的情况如下：\n\n"
        "【我的情况】\n"
        f"- 月薪：{wage:,.0f} 元\n"
        f"- 现在城市：等级 {tier_a}（具体城市名请先问我）\n"
        f"{b_line}\n\n"
        "【请帮我】\n"
        "1. 先问清楚我两边的具体城市名，然后对比这两座城市：生活成本（房租、吃饭、交通）、"
        "工资水平、就业机会、买房 / 落户难度。\n"
        "2. 按我的收入，在两个城市分别能结余多少？生活质量差别大吗？\n"
        "3. 换到目标城市，我的工资大概能涨 / 跌多少？多久能回本（搬家成本、过渡期没收入）？\n"
        "4. 除了钱，还有哪些该考虑的（离家远近、社保转移、孩子教育、人脉等）？\n"
        "5. 综合看，我这种情况换城市值不值？有什么风险和注意事项？\n\n"
        "要求：结合两座城市的真实情况给具体、现实的判断，别只说「大城市机会多」这种空话。"
    )


def build_injury_prompt(city, grade, monthly_wage):
    """工伤赔偿 → 问 AI 的提示词（让 AI 确认赔偿项目 + 讲认定/鉴定流程）。"""
    return (
        "请以资深工伤与劳动法律师的口吻，用大白话帮我。我在工作中受了伤，"
        "想搞清楚能赔多少、怎么走流程。情况如下：\n\n"
        "【我的情况】\n"
        f"- 所在城市：{city}\n"
        f"- 伤残等级（劳动能力鉴定）：{grade} 级（若还没鉴定，请先问我伤情帮我预估级别）\n"
        f"- 受伤前 12 个月平均月工资：{monthly_wage:,.0f} 元\n\n"
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
