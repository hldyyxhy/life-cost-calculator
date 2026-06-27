# -*- coding: utf-8 -*-
"""
dump_baselines.py —— 把 Python 计算函数的「完整返回 dict」dump 成黄金基准（阶段0）

输出 core/__fixtures__/*.json，供 TS 翻译后逐字段对拍。这是现有 __main__（只 print
挑拣字段）的核心缺口——这里 dump 完整返回，含 cost_rows/_cat/interpretation 全文/assumptions。

fixture 两种格式：
    单例：{name, source, input, expected}            —— situation 等单次调用
    批量：{name, source, batch:true, cases:[{note,input,expected}]}  —— 查表类多例

用法：
    cd core && python scripts/dump_baselines.py
"""
import sys
import json
from pathlib import Path

# Windows 控制台用 utf-8 输出中文（若失败无碍，文件本身仍为 utf-8）
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CORE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import calc_engine as CE
import cost_data as D
import rights_data as RD
import medical_data as MD
import relief_data as RLF
import profile as P
import tracking as T
import report as RP

FIX_DIR = CORE_ROOT / "__fixtures__"
FIX_DIR.mkdir(parents=True, exist_ok=True)


def write_fixture(name, obj):
    path = FIX_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=True)
    return path


# ============================================================
# situation 调用桥：驼峰 input → 蛇形 kwargs 调 Python
# 这个映射同时是「未来小程序表单 → 核心函数」的参数契约。
# ============================================================
def call_situation(inp):
    return CE.compute_current_situation(
        age=inp["age"],
        wage_pretax=inp["wagePretax"],
        tier=inp["tier"],
        housing=inp["housing"],
        food_level=inp["foodLevel"],
        has_car=inp.get("hasCar", False),
        insurance_mode=inp.get("insuranceMode", "在职（单位缴）"),
        num_children=inp.get("numChildren", 0),
        children_by_age=inp.get("childrenByAge"),
        support_elderly=inp.get("supportElderly", False),
        has_housing_deduction=inp.get("hasHousingDeduction", False),
        has_continuing_education=inp.get("hasContinuingEducation", False),
        support_family_monthly=inp.get("supportFamilyMonthly", 0),
        overrides=inp.get("overrides"),
    )


# ============================================================
# A. situation 用例（单例）—— 覆盖 surplus_rate 四档 + 各分支
# ============================================================
SITUATION_CASES = [
    {
        "name": "situation_default",
        "source": "calc_engine __main__ 计算器2 (L2500)：30/二线/6000/合租/普通/无车/在职",
        "input": {"age": 30, "wagePretax": 6000, "tier": "二线", "housing": "合租单间",
                  "foodLevel": "普通", "hasCar": False, "insuranceMode": "在职（单位缴）",
                  "numChildren": 0, "supportElderly": False},
    },
    {
        "name": "situation_mid_surplus",
        "source": "结余率 10~20% 分支（⚠建议达20%）",
        "input": {"age": 30, "wagePretax": 6500, "tier": "二线", "housing": "一居室整租",
                  "foodLevel": "普通", "hasCar": True, "insuranceMode": "在职（单位缴）"},
    },
    {
        "name": "situation_low_surplus",
        "source": "结余率 <10% 分支（🔴抗风险极弱）",
        "input": {"age": 30, "wagePretax": 6000, "tier": "二线", "housing": "一居室整租",
                  "foodLevel": "普通", "hasCar": True, "insuranceMode": "在职（单位缴）"},
    },
    {
        "name": "situation_negative_surplus",
        "source": "负结余（入不敷出）分支",
        "input": {"age": 30, "wagePretax": 2800, "tier": "三线", "housing": "一居室整租",
                  "foodLevel": "宽裕", "hasCar": True, "insuranceMode": "灵活就业（全自缴）",
                  "supportFamilyMonthly": 500},
    },
    {
        "name": "situation_edge_no_insurance",
        "source": "不缴社保警告分支（_build_interpretation L475）",
        "input": {"age": 30, "wagePretax": 6000, "tier": "二线", "housing": "合租单间",
                  "foodLevel": "普通", "hasCar": False, "insuranceMode": "不缴社保"},
    },
    {
        "name": "situation_edge_children",
        "source": "多子女+赡养+专项扣除累加（子女按段/赡养/房贷/继教）",
        "input": {"age": 35, "wagePretax": 8000, "tier": "二线", "housing": "一居室整租",
                  "foodLevel": "普通", "hasCar": False, "insuranceMode": "在职（单位缴）",
                  "numChildren": 2,
                  "childrenByAge": {"3岁以下（婴幼儿）": 1, "中小学（6-18岁）": 1},
                  "supportElderly": True, "hasHousingDeduction": True,
                  "hasContinuingEducation": True},
    },
    {
        "name": "situation_edge_housing_loan",
        "source": "已购房还月供 + 住房贷款利息专项扣除",
        "input": {"age": 32, "wagePretax": 7000, "tier": "二线", "housing": "已购房（还月供）",
                  "foodLevel": "普通", "hasCar": False, "insuranceMode": "在职（单位缴）",
                  "hasHousingDeduction": True},
    },
    {
        "name": "situation_edge_overrides",
        "source": "overrides 按实际覆盖（饮食/交通）",
        "input": {"age": 30, "wagePretax": 6000, "tier": "二线", "housing": "合租单间",
                  "foodLevel": "普通", "hasCar": False, "insuranceMode": "在职（单位缴）",
                  "overrides": {"饮食": 800, "交通": 200}},
    },
    {
        "name": "situation_edge_freelance",
        "source": "灵活就业（全自缴）社保分支",
        "input": {"age": 30, "wagePretax": 6000, "tier": "二线", "housing": "合租单间",
                  "foodLevel": "普通", "hasCar": False, "insuranceMode": "灵活就业（全自缴）"},
    },
]

# 真实档案用例（若 last_profile.json 存在）
def add_last_profile_case():
    lp = PROJECT_ROOT / "data" / "last_profile.json"
    if not lp.exists():
        print(f"  [跳过] last_profile.json 不存在：{lp}")
        return None
    with open(lp, encoding="utf-8") as f:
        p = json.load(f)
    seg_map = [("3岁以下（婴幼儿）", "child_baby"), ("幼儿园（3-6岁）", "child_kg"),
               ("中小学（6-18岁）", "child_school"), ("大学在读（18岁+）", "child_uni")]
    children_by_age = {}
    for seg, pk in seg_map:
        n = int(p.get(pk) or 0)
        if n > 0:
            children_by_age[seg] = n
    inp = {
        "age": int(p.get("age") or 30),
        "wagePretax": int(float(p.get("wage") or 0)),
        "tier": p.get("tier") or "三线",
        "housing": p.get("housing") or "合租单间",
        "foodLevel": p.get("food") or "普通",
        "hasCar": bool(p.get("has_car")),
        "insuranceMode": p.get("insurance") or "在职（单位缴）",
        "numChildren": int(p.get("num_children") or 0),
        "childrenByAge": children_by_age or None,
        "supportElderly": bool(p.get("support_elderly")),
        "hasHousingDeduction": bool(p.get("has_housing_deduction")),
        "hasContinuingEducation": bool(p.get("has_continuing_education")),
        "supportFamilyMonthly": int(float(p.get("support_family") or 0)),
        "overrides": None,
    }
    return {"name": "situation_last_profile",
            "source": f"data/last_profile.json 真实档案（{inp['tier']}/{inp['wagePretax']}元）",
            "input": inp}


# ============================================================
# B. 子依赖批量基准
# ============================================================
def build_survival_cases():
    cases = []
    for tier in ["一线", "新一线", "二线", "三线", "四线", "五线"]:
        for ins in ["在职（单位缴）", "灵活就业（全自缴）", "不缴社保"]:
            cases.append({
                "note": f"{tier}/{ins}",
                "input": {"tier": tier, "insuranceMode": ins},
                "expected": CE.compute_survival_baseline(tier, ins),
            })
    return cases


def build_normalize_cases():
    NC = CE._normalize_children
    raw = [
        ("空+0孩", {}, 0),
        ("None+0孩", None, 0),
        ("空+2孩兜底中小学", {}, 2),
        ("过滤0值段", {"3岁以下（婴幼儿）": 1, "中小学（6-18岁）": 0}, 0),
        ("多段并存", {"大学在读（18岁+）": 2, "中小学（6-18岁）": 1}, 0),
    ]
    return [{"note": n, "input": {"childrenByAge": cba, "numChildren": nc},
             "expected": NC(cba, nc)} for n, cba, nc in raw]


def build_tax_cases():
    PT = D.calc_personal_income_tax
    raw = [0, 3000, 3001, 10000, 12000, 25000, 80000, 80001, 200000]
    return [{"note": f"taxable={v}", "input": {"taxableMonthly": v},
             "expected": list(PT(v))} for v in raw]


def build_city_factor_cases():
    CF = D.city_factor
    tiers = ["一线", "新一线", "二线", "三线", "四线", "五线"]
    cases = [{"note": t, "input": {"tier": t}, "expected": CF(t)} for t in tiers]
    cases.append({"note": "未知→默认1.0", "input": {"tier": "火星"}, "expected": CF("火星")})
    return cases


# ============================================================
# C. 数值敏感函数占位（本阶段不译，批次2直接用）
# ============================================================
def build_numeric_cases():
    debts = [
        {"name": "信用卡", "balance": 3000, "annual_rate": 0.18, "min_monthly": 300},
        {"name": "网贷", "balance": 10000, "annual_rate": 0.36, "min_monthly": 500},
    ]
    unpayable_debts = [{"name": "高息贷", "balance": 10000, "annual_rate": 0.36, "min_monthly": 200}]
    return [
        {"name": "loan_methods", "source": "__main__ 债务1",
         "input": {"principal": 10000, "nominalApr": 0.18, "periods": 12},
         "expected": CE.compare_loan_methods(10000, 0.18, 12)},
        {"name": "affordable_debt", "source": "__main__ 债务2",
         "input": {"monthlySurplus": 2000, "nominalApr": 0.18, "periods": 24},
         "expected": CE.compute_affordable_debt(2000, 0.18, 24)},
        {"name": "debt_payoff_snowball", "source": "__main__ 债务3",
         "input": {"debts": debts, "method": "snowball", "extraMonthly": 500},
         "expected": CE.simulate_debt_payoff(debts, "snowball", extra_monthly=500)},
        {"name": "debt_payoff_avalanche", "source": "__main__ 债务3",
         "input": {"debts": debts, "method": "avalanche", "extraMonthly": 500},
         "expected": CE.simulate_debt_payoff(debts, "avalanche", extra_monthly=500)},
        {"name": "debt_payoff_unpayable", "source": "__main__ 失控用例",
         "input": {"debts": unpayable_debts, "method": "avalanche", "extraMonthly": 0},
         "expected": CE.simulate_debt_payoff(unpayable_debts, "avalanche")},
        {"name": "loan_spiral", "source": "__main__ 债务4",
         "input": {"initialBalance": 10000, "annualRate": 0.24, "months": 24, "actualMonthlyPayment": 0},
         "expected": CE.simulate_loan_spiral(10000, 0.24, 24, 0)},
        # 真实年化反算（覆盖 正常/偏高/极高 评级）
        {"name": "loan_apr_normal", "source": "真实年化反算·正常档",
         "input": {"principal": 100000, "monthlyPayment": 3000, "periods": 36},
         "expected": CE.compute_loan_apr(100000, 3000, 36)},
        {"name": "loan_apr_high", "source": "真实年化反算·偏高/高利贷档",
         "input": {"principal": 10000, "monthlyPayment": 920, "periods": 12},
         "expected": CE.compute_loan_apr(10000, 920, 12)},
        {"name": "loan_apr_extreme", "source": "真实年化反算·极高档",
         "input": {"principal": 5000, "monthlyPayment": 500, "periods": 12},
         "expected": CE.compute_loan_apr(5000, 500, 12)},
        # 劳动权益（__main__ 权益1-3 + 边界）
        {"name": "overtime_basic", "source": "__main__ 权益1（6000/40h/16h/8h）",
         "input": {"monthlyWage": 6000, "weekdayOt": 40, "weekendOt": 16, "holidayOt": 8},
         "expected": CE.compute_overtime_pay(6000, 40, 16, 8)},
        {"name": "overtime_zero", "source": "加班费 total=0 分支",
         "input": {"monthlyWage": 6000, "weekdayOt": 0, "weekendOt": 0, "holidayOt": 0},
         "expected": CE.compute_overtime_pay(6000, 0, 0, 0)},
        {"name": "min_wage_ok", "source": "__main__ 权益2（3500/三线，高于最低）",
         "input": {"monthlyWage": 3500, "tier": "三线"},
         "expected": CE.compute_min_wage_check(3500, "三线")},
        {"name": "min_wage_illegal", "source": "__main__ 违法（1800/三线）",
         "input": {"monthlyWage": 1800, "tier": "三线"},
         "expected": CE.compute_min_wage_check(1800, "三线")},
        {"name": "claim_part_employed", "source": "__main__ 权益3（8000/在职/部分）",
         "input": {"owedAmount": 8000, "employed": True, "evidence": "部分"},
         "expected": CE.assess_overtime_claim(8000, True, "部分")},
        {"name": "claim_no_evidence", "source": "__main__ 对比（8000/在职/几乎没有→warn）",
         "input": {"owedAmount": 8000, "employed": True, "evidence": "几乎没有"},
         "expected": CE.assess_overtime_claim(8000, True, "几乎没有")},
        {"name": "claim_small_employed", "source": "__main__ 对比（1500/在职/部分→caution）",
         "input": {"owedAmount": 1500, "employed": True, "evidence": "部分"},
         "expected": CE.assess_overtime_claim(1500, True, "部分")},
        {"name": "claim_left_full", "source": "__main__ 对比（8000/离职/充分→good）",
         "input": {"owedAmount": 8000, "employed": False, "evidence": "充分"},
         "expected": CE.assess_overtime_claim(8000, False, "充分")},
        # 债务健康（覆盖 健康/警戒/失控）
        {"name": "debt_health_ok", "source": "债务健康·健康档",
         "input": {"totalDebt": 50000, "monthlyIncome": 8000, "monthlyPay": 2000, "avgApr": 0.18},
         "expected": CE.assess_debt_health(50000, 8000, 2000, 0.18)},
        {"name": "debt_health_warn", "source": "债务健康·警戒档",
         "input": {"totalDebt": 100000, "monthlyIncome": 8000, "monthlyPay": 3000, "avgApr": 0.18},
         "expected": CE.assess_debt_health(100000, 8000, 3000, 0.18)},
        {"name": "debt_health_runaway", "source": "债务健康·失控（月还<月利息）",
         "input": {"totalDebt": 50000, "monthlyIncome": 8000, "monthlyPay": 500, "avgApr": 0.36},
         "expected": CE.assess_debt_health(50000, 8000, 500, 0.36)},
        # 住房决策
        {"name": "buy_rent_basic", "source": "买vs租·二线默认10年",
         "input": {"tier": "二线"},
         "expected": CE.compare_buy_rent("二线")},
        {"name": "buy_rent_custom", "source": "买vs租·一线15年100㎡",
         "input": {"tier": "一线", "years": 15, "houseArea": 100, "downRatio": 0.3},
         "expected": CE.compare_buy_rent("一线", 15, 100, 0.3)},
        {"name": "housing_fund_basic", "source": "公积金·二线余额3万月缴800",
         "input": {"tier": "二线", "balance": 30000, "monthlyContribution": 800},
         "expected": CE.housing_fund_loan("二线", 30000, 800)},
        {"name": "housing_fund_no_contrib", "source": "公积金·三线余额2万无月缴",
         "input": {"tier": "三线", "balance": 20000},
         "expected": CE.housing_fund_loan("三线", 20000)},
        {"name": "rate_stress_basic", "source": "利率压力·贷50万30年",
         "input": {"principal": 500000, "baseRate": 0.0345, "years": 30},
         "expected": CE.rate_stress_test(500000, 0.0345, 30)},
        # 个税优化
        {"name": "bonus_tax_high", "source": "年终奖·高薪（年30万/奖10万）",
         "input": {"annualSalary": 300000, "bonus": 100000, "annualSpecial": 36000, "annualSocial": 18000},
         "expected": CE.bonus_tax_compare(300000, 100000, 36000, 18000)},
        {"name": "bonus_tax_low", "source": "年终奖·低薪（年10万/奖3万）",
         "input": {"annualSalary": 100000, "bonus": 30000},
         "expected": CE.bonus_tax_compare(100000, 30000)},
        {"name": "special_deduction_full", "source": "专项扣除·全有",
         "input": {"hasChildren": 2, "supportElderly": True, "hasLoan": True, "continuingEdu": True},
         "expected": CE.special_deduction_hints(2, True, True, True)},
        {"name": "special_deduction_empty", "source": "专项扣除·全无",
         "input": {"hasChildren": 0, "supportElderly": False, "hasLoan": False, "continuingEdu": False},
         "expected": CE.special_deduction_hints()},
        # 一生成本 + 家庭 + 风险 + 工资预估
        {"name": "life_cost_basic", "source": "__main__ 计算器1（三线·普惠）",
         "input": {"tier": "三线", "level": "普惠"},
         "expected": CE.compute_life_cost("三线", "普惠")},
        {"name": "life_cost_high", "source": "__main__ 计算器1（一线·高端）",
         "input": {"tier": "一线", "level": "高端"},
         "expected": CE.compute_life_cost("一线", "高端")},
        {"name": "life_cost_grad", "source": "一生成本·二线中产读研民办普惠机构",
         "input": {"tier": "二线", "level": "中产", "graduate": True, "uniType": "民办", "careMode": "普惠养老机构"},
         "expected": CE.compute_life_cost("二线", "中产", "公立·顺产", "普惠养老机构", "民办", True)},
        {"name": "family_basic", "source": "双收入·本人6000+伴侣5000/二线",
         "input": {"selfAge": 30, "selfWage": 6000, "selfTier": "二线", "partnerWage": 5000, "partnerTier": "二线", "partnerInsurance": "在职（单位缴）"},
         "expected": CE.compute_family_situation(
             CE.compute_current_situation(age=30, wage_pretax=6000, tier="二线", housing="合租单间", food_level="普通", insurance_mode="在职（单位缴）"),
             5000, "二线", "在职（单位缴）")},
        {"name": "family_no_partner", "source": "无伴侣·partnerWage=0",
         "input": {"selfAge": 30, "selfWage": 6000, "selfTier": "二线", "partnerWage": 0},
         "expected": CE.compute_family_situation(
             CE.compute_current_situation(age=30, wage_pretax=6000, tier="二线", housing="合租单间", food_level="普通"),
             0, "二线")},
        {"name": "risk_basic", "source": "抗风险·存款5万/底线2626",
         "input": {"savings": 50000, "survivalBaseline": 2626},
         "expected": CE.compute_risk_indicators(50000, 2626)},
        {"name": "risk_low_savings", "source": "抗风险·存款2万（大病high）",
         "input": {"savings": 20000, "survivalBaseline": 2626},
         "expected": CE.compute_risk_indicators(20000, 2626)},
        {"name": "target_wage_up", "source": "工资预估·三线→一线",
         "input": {"wage": 5000, "currentTier": "三线", "targetTier": "一线"},
         "expected": CE._estimate_target_wage(5000, "三线", "一线")},
        # 城市对比（批次3）
        {"name": "compare_cities_up", "source": "城市对比·三线→一线（升线）",
         "input": {"wage": 5000, "currentTier": "三线", "targetTier": "一线"},
         "expected": CE.compare_cities(5000, "三线", "一线")},
        {"name": "compare_cities_down", "source": "城市对比·一线→三线（降线）",
         "input": {"wage": 8500, "currentTier": "一线", "targetTier": "三线"},
         "expected": CE.compare_cities(8500, "一线", "三线")},
        {"name": "compare_cities_with_kids", "source": "城市对比·带娃+养车+赡养",
         "input": {"wage": 6000, "currentTier": "二线", "targetTier": "新一线", "hasCar": True,
                   "numChildren": 1, "childrenByAge": {"中小学（6-18岁）": 1}, "supportElderly": True},
         "expected": CE.compare_cities(6000, "二线", "新一线", "在职（单位缴）", "合租单间", "普通",
                                       True, 1, {"中小学（6-18岁）": 1}, True, 0)},
    ]


def build_prompt_cases():
    """提示词生成（批次4，纯字符串，对拍严格相等）。"""
    P = {"age": 30, "gender": "男", "health": "良好", "insurance": "在职（单位缴）",
         "has_partner": True, "partner_wage": 5000, "num_children": 1,
         "support_elderly": True, "savings": 50000, "mortgage_monthly": 2000, "car_loan_monthly": 0}
    return [
        {"name": "prompt_overtime", "source": "加班费维权",
         "input": {"wage": 6000, "weekdayOt": 40, "weekendOt": 16, "holidayOt": 8, "actual": 0, "months": 3, "employed": True, "evidence": "部分", "city": "北京"},
         "expected": CE.build_overtime_prompt(6000, 40, 16, 8, 0, 3, True, "部分", "北京")},
        {"name": "prompt_loan_apr", "source": "真实年化(带profile)",
         "input": {"principal": 10000, "monthly": 920, "periods": 12, "profile": P},
         "expected": CE.build_loan_apr_prompt(10000, 920, 12, P)},
        {"name": "prompt_compare_methods", "source": "还款方式对比",
         "input": {"principal": 10000, "aprPct": 18, "periods": 12, "profile": None},
         "expected": CE.build_compare_methods_prompt(10000, 18, 12, None)},
        {"name": "prompt_affordable_debt", "source": "可承受负债(带income)",
         "input": {"surplus": 2000, "aprPct": 18, "periods": 24, "income": 6000, "profile": None},
         "expected": CE.build_affordable_debt_prompt(2000, 18, 24, 6000, None)},
        {"name": "prompt_debt_payoff", "source": "多债雪球",
         "input": {"debtsDesc": "信用卡 3000 元（年化18%，月还300）\n网贷 10000 元（年化36%，月还500）", "extra": 500},
         "expected": CE.build_debt_payoff_prompt("信用卡 3000 元（年化18%，月还300）\n网贷 10000 元（年化36%，月还500）", 500)},
        {"name": "prompt_spiral", "source": "以贷养贷(带profile)",
         "input": {"init": 10000, "aprPct": 24, "months": 24, "pay": 0, "profile": P},
         "expected": CE.build_spiral_prompt(10000, 24, 24, 0, P)},
        {"name": "prompt_min_wage", "source": "最低工资(带profile)",
         "input": {"wage": 1800, "tier": "三线", "city": "临沂", "profile": P},
         "expected": CE.build_min_wage_prompt(1800, "三线", "临沂", P)},
        {"name": "prompt_unemployment", "source": "失业金(全参数)",
         "input": {"city": "成都", "years": "6", "wage": "6000", "reason": "公司辞退", "profile": None},
         "expected": CE.build_unemployment_prompt("成都", "6", "6000", "公司辞退", None)},
        {"name": "prompt_unemployment_sparse", "source": "失业金(空参数)",
         "input": {"city": "", "years": "", "wage": "", "reason": "", "profile": None},
         "expected": CE.build_unemployment_prompt("", "", "", "", None)},
        {"name": "prompt_subsidy", "source": "4050补贴",
         "input": {"city": "杭州", "profile": None},
         "expected": CE.build_subsidy_prompt("杭州", None)},
        {"name": "prompt_help", "source": "求助·欠薪",
         "input": {"sceneKey": "欠薪", "city": "广州"},
         "expected": CE.build_help_prompt("欠薪", "广州")},
        {"name": "prompt_help_unknown", "source": "求助·未知场景",
         "input": {"sceneKey": "不存在", "city": ""},
         "expected": CE.build_help_prompt("不存在", "")},
        {"name": "prompt_antifraud", "source": "反诈·刷单",
         "input": {"key": "task_rebate", "city": "深圳"},
         "expected": CE.build_antifraud_prompt("task_rebate", "深圳")},
        {"name": "prompt_current_situation", "source": "处境诊断(带娃+伴侣)",
         "input": {"age": 30, "tier": "二线", "wage": 6000, "ins": "在职（单位缴）", "housing": "合租单间", "food": "普通", "hasCar": False, "numKids": 1, "supportElderly": False, "savings": 50000, "city": "台州", "childrenByAge": {"中小学（6-18岁）": 1}, "familyMonthly": 0, "hasPartner": True, "partnerWage": 5000, "partnerIns": "在职（单位缴）"},
         "expected": CE.build_current_situation_prompt(30, "二线", 6000, "在职（单位缴）", "合租单间", "普通", False, 1, False, 50000, "台州", {"中小学（6-18岁）": 1}, 0, True, 5000, "在职（单位缴）")},
        {"name": "prompt_milestones", "source": "人生三座山(带profile)",
         "input": {"tier": "二线", "wage": 6000, "city": "台州", "profile": P},
         "expected": CE.build_milestones_prompt("二线", 6000, "台州", P)},
        {"name": "prompt_compare", "source": "城市加减法",
         "input": {"tierA": "三线", "tierB": "一线", "wage": 5000, "targetCity": "北京", "housing": "合租单间", "food": "普通", "hasCar": False, "insurance": "在职（单位缴）"},
         "expected": CE.build_compare_prompt("三线", "一线", 5000, "北京", "合租单间", "普通", False, "在职（单位缴）")},
        {"name": "prompt_injury", "source": "工伤赔偿(带profile)",
         "input": {"city": "苏州", "grade": 7, "monthlyWage": 6000, "profile": P},
         "expected": CE.build_injury_prompt("苏州", 7, 6000, P)},
        {"name": "prompt_buy_rent", "source": "买房vs租房",
         "input": {"tier": "二线", "years": 10, "area": 90, "downRatio": 0.3, "city": "台州", "profile": None},
         "expected": CE.build_buy_rent_prompt("二线", 10, 90, 0.3, "台州", None)},
        {"name": "prompt_fund", "source": "公积金(带缴存)",
         "input": {"tier": "二线", "balance": 30000, "contrib": 800, "years": 30, "city": "台州", "profile": None},
         "expected": CE.build_fund_prompt("二线", 30000, 800, 30, "台州", None)},
        {"name": "prompt_rate_stress", "source": "利率压力",
         "input": {"principal": 500000, "baseRate": 0.0345, "years": 30, "city": "台州", "profile": None},
         "expected": CE.build_rate_stress_prompt(500000, 0.0345, 30, "台州", None)},
        {"name": "prompt_tax", "source": "个税优化(带家庭)",
         "input": {"annualSalary": 120000, "bonus": 30000, "city": "台州", "special": 4000, "social": 1500, "kids": 1, "elderly": True, "loan": True, "edu": False, "profile": None},
         "expected": CE.build_tax_prompt(120000, 30000, "台州", 4000, 1500, 1, True, True, False, None)},
        {"name": "prompt_assistance", "source": "本地救助(带资产)",
         "input": {"city": "台州", "perCapitaIncome": 800, "familyInfo": "一家三口，本人有慢性病", "asset": 5000, "profile": None},
         "expected": CE.build_assistance_prompt("台州", 800, "一家三口，本人有慢性病", 5000, None)},
        {"name": "prompt_medical", "source": "医保(退休异地已备案)",
         "input": {"city": "广州", "identity": "职工", "cost": 50000, "retired": True, "remote": "filed", "profile": None},
         "expected": CE.build_medical_prompt("广州", "职工", 50000, True, "filed", None)},
        {"name": "prompt_debt_health", "source": "债务健康(带profile)",
         "input": {"totalDebt": 50000, "monthlyIncome": 8000, "monthlyPay": 2000, "avgApr": 0.18, "profile": P},
         "expected": CE.build_debt_health_prompt(50000, 8000, 2000, 0.18, P)},
    ]


def build_data_cases():
    """数据模块查询函数 + 薄封装（批次5），batch 格式。"""
    return [
        {"name": "data_min_wage", "source": "最低工资·多城", "batch": True, "cases": [
            {"note": "北京", "input": {"city": "北京"}, "expected": RD.get_min_wage_for_city("北京")},
            {"note": "成都", "input": {"city": "成都"}, "expected": RD.get_min_wage_for_city("成都")},
            {"note": "未知", "input": {"city": "火星"}, "expected": RD.get_min_wage_for_city("火星")},
        ]},
        {"name": "data_unemployment", "source": "失业金·多城", "batch": True, "cases": [
            {"note": "北京", "input": {"city": "北京"}, "expected": RD.estimate_unemployment_pay("北京")},
            {"note": "广州", "input": {"city": "广州"}, "expected": RD.estimate_unemployment_pay("广州")},
            {"note": "成都", "input": {"city": "成都"}, "expected": RD.estimate_unemployment_pay("成都")},
            {"note": "未知", "input": {"city": "火星"}, "expected": RD.estimate_unemployment_pay("火星")},
        ]},
        {"name": "data_unemploy_duration", "source": "失业金领取月数", "batch": True, "cases": [
            {"note": "6年", "input": {"years": 6}, "expected": RD.unemploy_duration(6)},
            {"note": "15年", "input": {"years": 15}, "expected": RD.unemploy_duration(15)},
            {"note": "0年", "input": {"years": 0}, "expected": RD.unemploy_duration(0)},
        ]},
        {"name": "data_injury_one_time", "source": "一次性伤残补助金", "batch": True, "cases": [
            {"note": "7级6000", "input": {"grade": 7, "monthlyWage": 6000}, "expected": RD.calc_injury_one_time(7, 6000)},
            {"note": "10级3000", "input": {"grade": 10, "monthlyWage": 3000}, "expected": RD.calc_injury_one_time(10, 3000)},
        ]},
        {"name": "data_injury_pension", "source": "伤残津贴", "batch": True, "cases": [
            {"note": "3级6000", "input": {"grade": 3, "monthlyWage": 6000}, "expected": RD.calc_injury_pension(3, 6000)},
            {"note": "8级6000(无)", "input": {"grade": 8, "monthlyWage": 6000}, "expected": RD.calc_injury_pension(8, 6000)},
        ]},
        {"name": "data_injury_extra", "source": "各省工伤医疗/就业补助", "batch": True, "cases": [
            {"note": "广东7级", "input": {"province": "广东", "grade": 7}, "expected": RD.get_province_injury_extra("广东", 7)},
            {"note": "未知省", "input": {"province": "火星省", "grade": 7}, "expected": RD.get_province_injury_extra("火星省", 7)},
        ]},
        {"name": "data_dibao", "source": "低保·多城(四级fallback)", "batch": True, "cases": [
            {"note": "上海(精确)", "input": {"city": "上海"}, "expected": RLF.get_dibao_for_city("上海")},
            {"note": "深圳(②含括号)", "input": {"city": "深圳"}, "expected": RLF.get_dibao_for_city("深圳")},
            {"note": "长沙(③省)", "input": {"city": "长沙"}, "expected": RLF.get_dibao_for_city("长沙")},
            {"note": "拉萨(④tier)", "input": {"city": "拉萨"}, "expected": RLF.get_dibao_for_city("拉萨")},
            {"note": "未知", "input": {"city": "火星"}, "expected": RLF.get_dibao_for_city("火星")},
        ]},
        {"name": "data_tekun", "source": "特困", "batch": True, "cases": [
            {"note": "深圳(override)", "input": {"city": "深圳"}, "expected": RLF.get_tekun_for_city("深圳")},
            {"note": "上海(×1.3)", "input": {"city": "上海"}, "expected": RLF.get_tekun_for_city("上海")},
            {"note": "未知", "input": {"city": "火星"}, "expected": RLF.get_tekun_for_city("火星")},
        ]},
        {"name": "data_inpatient", "source": "住院报销估算", "batch": True, "cases": [
            {"note": "广州职工5万", "input": {"city": "广州", "identity": "职工", "cost": 50000, "remote": "none", "retired": False}, "expected": MD.estimate_inpatient("广州", "职工", 50000, "none", False)},
            {"note": "台州居民3万", "input": {"city": "台州", "identity": "居民", "cost": 30000, "remote": "none", "retired": False}, "expected": MD.estimate_inpatient("台州", "居民", 30000, "none", False)},
            {"note": "成都职工异地未备案", "input": {"city": "成都", "identity": "职工", "cost": 80000, "remote": "unfiled", "retired": False}, "expected": MD.estimate_inpatient("成都", "职工", 80000, "unfiled", False)},
            {"note": "北京退休6万", "input": {"city": "北京", "identity": "职工", "cost": 60000, "remote": "none", "retired": True}, "expected": MD.estimate_inpatient("北京", "职工", 60000, "none", True)},
        ]},
        {"name": "data_check_relief", "source": "本地救助对照", "batch": True, "cases": [
            {"note": "上海800(符合)", "input": {"city": "上海", "perCapitaIncome": 800, "familySize": 3, "asset": 5000}, "expected": CE.check_relief("上海", 800, 3, 5000)},
            {"note": "长沙1500(边缘)", "input": {"city": "长沙", "perCapitaIncome": 1500, "familySize": 3, "asset": None}, "expected": CE.check_relief("长沙", 1500, 3, None)},
            {"note": "台州3000(不符)", "input": {"city": "台州", "perCapitaIncome": 3000, "familySize": 1, "asset": None}, "expected": CE.check_relief("台州", 3000, 1, None)},
        ]},
        {"name": "data_medical_cost", "source": "住院估算(薄封装)", "batch": True, "cases": [
            {"note": "广州职工5万", "input": {"city": "广州", "identity": "职工", "cost": 50000, "remote": "none", "retired": False}, "expected": CE.estimate_medical_cost("广州", "职工", 50000, "none", False)},
        ]},
    ]


def build_datamodel_cases():
    """数据模型层（profile/tracking/report）。"""
    prof_raw = {"age": 30, "gender": "男", "wage": "6000", "tier": "二线", "city": "台州",
                "housing": "合租单间", "food": "普通", "has_car": False, "insurance": "在职（单位缴）",
                "num_children": 1, "child_school": 1, "support_elderly": True,
                "savings": "50000", "mortgage_monthly": "2000"}
    prof = P.validate_profile(prof_raw)
    cur = CE.compute_current_situation(age=30, wage_pretax=6000, tier="二线", housing="合租单间",
                                       food_level="普通", has_car=False, insurance_mode="在职（单位缴）",
                                       num_children=1, children_by_age={"中小学（6-18岁）": 1}, support_elderly=True)
    cmp = CE.compare_cities(6000, "二线", "一线")
    ms = {"marriage": "结婚（二线）：彩礼+婚礼+婚房首付约 30 万，按你当前结余攒需约 12 年。",
          "child": "养娃（普惠·二线）：0-18岁约 50 万，几乎耗尽你的结余能力。",
          "retire": "养老（60岁退休）：按当前结余，60岁前需储备约 80 万。"}
    prof_metrics = {"age": 30, "wage": "6000", "tier": "二线", "housing": "合租单间",
                    "food": "普通", "insurance": "在职（单位缴）",
                    "savings": "50000", "mortgage_monthly": "2000", "car_loan_monthly": ""}
    snap = {"time": "2026-06-27 20:40", "metrics": {"surplus": 2052, "savings": 50000,
            "cost_total": 3472, "debt_monthly": 2000, "surplus_rate": 37.1}, "profile": {}}
    return [
        {"name": "data_profile", "source": "档案校验/迁移/映射", "batch": True, "cases": [
            {"note": "默认", "input": {}, "expected": P.default_profile()},
            {"note": "往返", "input": {"raw": {"age": 25, "wage": "8000", "has_partner": True, "partner_wage": "7000"}},
             "expected": P.validate_profile({"age": 25, "wage": "8000", "has_partner": True, "partner_wage": "7000"})},
            {"note": "补全", "input": {"raw": {"age": 25}}, "expected": P.validate_profile({"age": 25})},
            {"note": "丢弃多余", "input": {"raw": {"age": 25, "nonexistent": 999}},
             "expected": P.validate_profile({"age": 25, "nonexistent": 999})},
            {"note": "旧版迁移", "input": {"raw": {"child_age_group": "3岁以下（婴幼儿）", "num_children": 2}},
             "expected": P.validate_profile({"child_age_group": "3岁以下（婴幼儿）", "num_children": 2})},
            {"note": "autoMapTier(台州)", "input": {"profile": {"city": "台州", "tier": "三线"}},
             "expected": P.auto_map_tier({"city": "台州", "tier": "三线"})},
            {"note": "autoMapTier(未知)", "input": {"profile": {"city": "火星", "tier": "三线"}},
             "expected": P.auto_map_tier({"city": "火星", "tier": "三线"})},
        ]},
        {"name": "data_metrics", "source": "跟踪指标", "batch": True, "cases": [
            {"note": "带last_result", "input": {"profile": prof_metrics, "lastResult": {"surplus": 2052, "cost_total": 3472, "surplus_rate": 37.1}},
             "expected": T.metrics_from(prof_metrics, {"surplus": 2052, "cost_total": 3472, "surplus_rate": 37.1})},
            {"note": "现算", "input": {"profile": prof_metrics}, "expected": T.metrics_from(prof_metrics)},
        ]},
        {"name": "data_render", "source": "跟踪文本", "batch": True, "cases": [
            {"note": "空", "input": {"name": "张三", "snapshots": []}, "expected": T.render_txt("张三", [])},
            {"note": "有记录", "input": {"name": "张三", "snapshots": [snap]}, "expected": T.render_txt("张三", [snap])},
        ]},
        {"name": "data_report", "source": "综合报告(完整)",
         "input": {"profile": prof_raw,
                   "curInput": {"age": 30, "wagePretax": 6000, "tier": "二线", "housing": "合租单间",
                                "foodLevel": "普通", "hasCar": False, "insuranceMode": "在职（单位缴）",
                                "numChildren": 1, "childrenByAge": {"中小学（6-18岁）": 1}, "supportElderly": True},
                   "cmpInput": {"wage": 6000, "currentTier": "二线", "targetTier": "一线"},
                   "ms": ms},
         "expected": RP.build_full_report(prof, cur, cmp, ms)},
    ]


def main():
    written = []

    # A. situation 单例
    for c in SITUATION_CASES:
        expected = call_situation(c["input"])
        write_fixture(c["name"], {"name": c["name"], "source": c["source"],
                                  "input": c["input"], "expected": expected})
        written.append((c["name"], "situation",
                        f"cost_total={expected['cost_total']} surplus={expected['surplus']} rate={expected['surplus_rate']}"))
    lp = add_last_profile_case()
    if lp:
        expected = call_situation(lp["input"])
        write_fixture(lp["name"], {"name": lp["name"], "source": lp["source"],
                                   "input": lp["input"], "expected": expected})
        written.append((lp["name"], "situation",
                        f"cost_total={expected['cost_total']} surplus={expected['surplus']} rate={expected['surplus_rate']}"))

    # B. 子依赖批量
    for name, cases in [
        ("survival_baseline", build_survival_cases()),
        ("normalize_children", build_normalize_cases()),
        ("tax_brackets", build_tax_cases()),
        ("city_factor", build_city_factor_cases()),
    ]:
        write_fixture(name, {"name": name, "source": "子依赖基准", "batch": True, "cases": cases})
        written.append((name, "batch", f"{len(cases)} 例"))

    # C. 债务/贷款计算族（批次2，已译 + 对拍）
    for c in build_numeric_cases():
        write_fixture(c["name"], {"name": c["name"], "source": c["source"],
                                  "input": c["input"], "expected": c["expected"]})
        written.append((c["name"], "numeric", "数值族对拍"))

    # D. 提示词生成（批次4，纯字符串严格对拍）
    for c in build_prompt_cases():
        write_fixture(c["name"], {"name": c["name"], "source": c["source"],
                                  "input": c["input"], "expected": c["expected"]})
        written.append((c["name"], "prompt", "提示词对拍"))

    # E. 数据模块查询函数 + 薄封装（批次5，batch 格式）
    for c in build_data_cases():
        write_fixture(c["name"], c)
        written.append((c["name"], "data", "数据族对拍"))

    # F. 数据模型层（profile/tracking/report）
    for c in build_datamodel_cases():
        write_fixture(c["name"], c)
        written.append((c["name"], "datamodel", "数据模型对拍"))

    # 汇总
    print(f"基准 dump 完成 → {FIX_DIR}（共 {len(written)} 个 fixture）\n")
    for name, kind, detail in written:
        tag = {"situation": "[situation]", "batch": "[batch]  ", "numeric": "[numeric] ", "prompt": "[prompt]   ", "data": "[data]    ", "datamodel": "[datamodel]"}[kind]
        print(f"  {tag} {name}: {detail}")


if __name__ == "__main__":
    main()
