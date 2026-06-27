// calc/situation.ts —— compute_current_situation (calc_engine.py:252-450)
// 处境页主入口：月度生存成本 / 到手收入 / 结余。试点核心。
import type { SituationInput, SituationResult, CostRow } from '../types';
import { cityFactor, calcPersonalIncomeTax } from '../data/cost';
import { normalizeChildrenByAge } from './normalizeChildren';
import { survivalBaseline } from './survival';
import { buildSituationInterpretation } from './interpretation';
import { group, pyFloatStr } from '../fmt';
import costRaw from '../data/cost.json';

const C = costRaw as unknown as Record<string, any>;
const HOUSE_PURCHASE = C.HOUSE_PURCHASE;
const HOUSING = C.HOUSING;
const FOOD = C.FOOD;
const LIFESTYLE_FACTOR = C.LIFESTYLE_FACTOR;
const TRANSPORT = C.TRANSPORT;
const OTHER_MONTHLY = C.OTHER_MONTHLY;
const SOCIAL_INSURANCE_MONTHLY = C.SOCIAL_INSURANCE_MONTHLY;
const FREELANCE_INSURANCE_MONTHLY = C.FREELANCE_INSURANCE_MONTHLY;
const SPECIAL_DEDUCTIONS = C.SPECIAL_DEDUCTIONS;
const TAX_THRESHOLD = C.TAX_THRESHOLD;
const MIN_WAGE = C.MIN_WAGE;
const TYPICAL_WAGE = C.TYPICAL_WAGE;

export function computeCurrentSituation(input: SituationInput): SituationResult {
  const {
    age,
    wagePretax,
    tier,
    housing,
    foodLevel,
    hasCar = false,
    insuranceMode = '在职（单位缴）',
    numChildren = 0,
    childrenByAge = null,
    supportElderly = false,
    hasHousingDeduction = false,
    hasContinuingEducation = false,
    supportFamilyMonthly = 0,
    overrides = null,
  } = input;

  const cf = cityFactor(tier);
  const cost_rows: CostRow[] = [];
  const breakdown: Record<string, number> = {};

  // 内部闭包 add_cost（Python L293）：append 成本行 + 累加 breakdown[category]
  const add_cost = (item: string, amount: number, note = '', category: string | null = null) => {
    cost_rows.push({ item, amount: Math.round(amount), note, _cat: category });
    if (category) breakdown[category] = (breakdown[category] ?? 0) + Math.round(amount);
  };

  // ---------- 月度生存成本 ----------
  // 住房
  let utility: number;
  if (housing === '已购房（还月供）') {
    const house_cost = HOUSE_PURCHASE[tier].monthly_loan;
    add_cost('住房（房贷月供）', house_cost, '90㎡贷款70%、30年、约3.05%利率估算', '住房');
    utility = HOUSING['含水电物业网费'].base * cf;
  } else if (housing === '与父母同住（免租）') {
    add_cost('住房（与父母同住）', 0, '免房租；水电与父母分摊', '住房');
    utility = HOUSING['含水电物业网费'].base * cf * 0.5; // 水电减半
  } else {
    const house_cost = HOUSING[housing].base * cf;
    add_cost(`住房（${housing}）`, house_cost, HOUSING[housing].note, '住房');
    utility = HOUSING['含水电物业网费'].base * cf;
  }
  add_cost('水电燃气物业宽带', utility, HOUSING['含水电物业网费'].note, '住房');

  // 饮食
  const food = FOOD.base * cf * LIFESTYLE_FACTOR[foodLevel];
  add_cost(
    `饮食（${foodLevel}档）`,
    food,
    `三线普通基准${FOOD.base}×城市${pyFloatStr(cf)}×${foodLevel}系数${pyFloatStr(LIFESTYLE_FACTOR[foodLevel])}`,
    '饮食',
  );

  // 交通
  if (hasCar) {
    const transport = TRANSPORT['养车'].base * cf;
    add_cost('交通（养车）', transport, TRANSPORT['养车'].note, '交通');
  } else {
    const transport = TRANSPORT['公交地铁通勤'].base * cf;
    add_cost('交通（公交地铁）', transport, TRANSPORT['公交地铁通勤'].note, '交通');
  }

  // 通讯、日用、衣物（先逐项 add_cost 累加 breakdown，再整体覆盖为合并值）
  const other_total = Object.values(OTHER_MONTHLY).reduce((s: number, v: any) => s + v.base, 0) * cf;
  for (const [key, info] of Object.entries(OTHER_MONTHLY) as [string, any][]) {
    add_cost(key, info.base * cf, '', '通讯日用');
  }
  breakdown['通讯日用'] = Math.round(other_total); // 合并为一项（覆盖逐项累加）

  // 社保（作为成本计入）
  let social_ins: number;
  if (insuranceMode === '在职（单位缴）') social_ins = SOCIAL_INSURANCE_MONTHLY[tier];
  else if (insuranceMode === '灵活就业（全自缴）') social_ins = FREELANCE_INSURANCE_MONTHLY[tier];
  else social_ins = 0;
  if (social_ins > 0) {
    const note_map: Record<string, string> = {
      '在职（单位缴）': SOCIAL_INSURANCE_MONTHLY.note,
      '灵活就业（全自缴）': FREELANCE_INSURANCE_MONTHLY.note,
    };
    add_cost(`社保公积金（${insuranceMode}）`, social_ins, note_map[insuranceMode], '社保');
  }

  // 给老家生活费
  if (supportFamilyMonthly > 0) {
    add_cost('给老家生活费', supportFamilyMonthly, `在外务工给父母/家庭的生活费，月 ${group(supportFamilyMonthly)} 元`, '给老家');
  }

  // —— overrides：用户实际值覆盖估算（val===null 或类别不存在则跳过；0 是合法值）——
  if (overrides) {
    for (const [cat, val] of Object.entries(overrides)) {
      if (val === null || !(cat in breakdown)) continue;
      // 移除该类别所有旧行（倒序 splice 避免索引错位）
      for (let i = cost_rows.length - 1; i >= 0; i--) {
        if (cost_rows[i]._cat === cat) cost_rows.splice(i, 1);
      }
      cost_rows.push({ item: `${cat}（按实际）`, amount: Math.round(val as number), note: '你填的实际金额', _cat: cat });
      breakdown[cat] = Math.round(val as number);
    }
  }

  const cost_total = cost_rows.reduce((s, r) => s + r.amount, 0);

  // ---------- 收入端：个税 ----------
  // 专项附加扣除
  let special = 0;
  const special_detail: string[] = [];
  // 子女专项：按各年龄段分别累加（3岁以下→婴幼儿照护，其余→子女教育）
  for (const [seg, n] of Object.entries(normalizeChildrenByAge(childrenByAge, numChildren))) {
    const dedu_key = seg.startsWith('3岁以下') ? '3岁以下婴幼儿照护' : '子女教育（3岁至博士）';
    const amt = SPECIAL_DEDUCTIONS[dedu_key].amount * n;
    special += amt;
    special_detail.push(`${dedu_key} ${n}孩 = ${group(amt)}`);
  }
  if (supportElderly) {
    const amt = SPECIAL_DEDUCTIONS['赡养老人'].amount;
    special += amt;
    special_detail.push(`赡养老人 ${group(amt)}`);
  }
  if (hasContinuingEducation) {
    const amt = SPECIAL_DEDUCTIONS['继续教育'].amount;
    special += amt;
    special_detail.push(`继续教育 ${group(amt)}`);
  }
  if (hasHousingDeduction) {
    let amt: number;
    let name: string;
    if (housing === '已购房（还月供）') {
      amt = SPECIAL_DEDUCTIONS['住房贷款利息'].amount;
      name = '住房贷款利息';
    } else if (tier === '一线' || tier === '新一线' || tier === '二线') {
      amt = SPECIAL_DEDUCTIONS['住房租金（直辖市/省会）'].amount;
      name = '住房租金';
    } else {
      amt = SPECIAL_DEDUCTIONS['住房租金（≤100万人口城市）'].amount;
      name = '住房租金';
    }
    special += amt;
    special_detail.push(`${name} ${group(amt)}`);
  }

  const taxable = wagePretax - social_ins - TAX_THRESHOLD - special;
  const [tax, tax_rate] = calcPersonalIncomeTax(Math.max(taxable, 0));
  const income_net = wagePretax - social_ins - tax;
  const surplus = income_net - cost_total;

  // 结余率
  const surplus_rate = income_net > 0 ? (surplus / income_net) * 100 : 0;

  // 买房攒首付年限
  let house_saving_years: number | null = null;
  if (surplus > 0) {
    const hp = HOUSE_PURCHASE[tier];
    const downpayment = hp.downpayment;
    const annual_surplus = surplus * 12;
    if (annual_surplus > 0) house_saving_years = downpayment / annual_surplus;
  }

  // 城市生存底线（计算一次，解读与页面共用）
  const survival_baseline = survivalBaseline(tier, insuranceMode);

  // 白话解读
  const interpretation = buildSituationInterpretation({
    age,
    wage: wagePretax,
    tier,
    costTotal: cost_total,
    socialIns: social_ins,
    tax,
    incomeNet: income_net,
    surplus,
    surplusRate: surplus_rate,
    houseSavingYears: house_saving_years,
    survivalBaseline: survival_baseline,
    specialDetail: special_detail,
    numChildren: numChildren,
    foodLevel: foodLevel,
    insuranceMode: insuranceMode,
    childrenByAge: childrenByAge,
    supportFamilyMonthly: supportFamilyMonthly,
  });

  const assumptions = [
    `城市成本系数：${tier} = ${pyFloatStr(cf)}（以三线/全国城镇平均=1.0）`,
    `社保：${insuranceMode}` + (social_ins ? `，月缴 ${group(social_ins)} 元` : '，未计入'),
    `个税：起征点5,000元/月` + (special ? ` + 专项附加扣除合计 ${group(special)} 元` : '，无专项附加扣除'),
    `当地最低工资约 ${group(MIN_WAGE[tier])} 元/月，城镇私营单位典型月薪约 ${group(TYPICAL_WAGE[tier])} 元。`,
    '生存成本仅含基本吃住行+社保，未含人情、娱乐、储蓄、意外、大病等。',
  ];

  return {
    cost_rows,
    breakdown,
    cost_total: Math.round(cost_total),
    survival_baseline,
    social_ins: Math.round(social_ins),
    tax: Math.round(tax),
    tax_rate,
    income_net: Math.round(income_net),
    surplus: Math.round(surplus),
    surplus_rate: Math.round(surplus_rate * 10) / 10, // Python round(x, 1)
    house_saving_years: house_saving_years ? Math.round(house_saving_years * 10) / 10 : null,
    special_total: special,
    interpretation,
    assumptions,
  };
}
