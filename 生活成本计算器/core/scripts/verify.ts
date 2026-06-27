// verify.ts —— 交叉验证：TS 翻译输出 vs Python 黄金基准（__fixtures__）
// 用法：npm run verify
// 容差：金额 ≤1 元（round 差异兜底）、tax_rate/比率 0.001、surplus_rate/house_saving_years 0.1、
//       interpretation 文本严格相等、结构字段逐项比对。
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { computeCurrentSituation } from '../src/calc/situation';
import { survivalBaseline } from '../src/calc/survival';
import { normalizeChildrenByAge } from '../src/calc/normalizeChildren';
import { computeLoanApr, compareLoanMethods, computeAffordableDebt } from '../src/calc/loan';
import { simulateDebtPayoff, simulateLoanSpiral, assessDebtHealth } from '../src/calc/debt';
import { computeOvertimePay, computeMinWageCheck, assessOvertimeClaim } from '../src/calc/rights';
import { compareBuyRent, housingFundLoan, rateStressTest } from '../src/calc/housing';
import { bonusTaxCompare, specialDeductionHints } from '../src/calc/tax';
import { computeLifeCost } from '../src/calc/lifeCost';
import { computeFamilySituation, computeRiskIndicators, estimateTargetWage } from '../src/calc/family';
import { compareCities } from '../src/calc/compare';
import { checkRelief, estimateMedicalCost } from '../src/calc/relief';
import { getMinWageForCity, estimateUnemploymentPay, unemployDuration, calcInjuryOneTime, calcInjuryPension, getProvinceInjuryExtra } from '../src/data/rights';
import { estimateInpatient } from '../src/data/medical';
import { getDibaoForCity, getTekunForCity } from '../src/data/relief';
import {
  buildOvertimePrompt, buildLoanAprPrompt, buildCompareMethodsPrompt, buildAffordableDebtPrompt,
  buildDebtPayoffPrompt, buildSpiralPrompt, buildMinWagePrompt, buildUnemploymentPrompt,
  buildSubsidyPrompt, buildHelpPrompt, buildAntifraudPrompt, buildCurrentSituationPrompt,
  buildMilestonesPrompt, buildComparePrompt, buildInjuryPrompt, buildBuyRentPrompt,
  buildFundPrompt, buildRateStressPrompt, buildTaxPrompt, buildAssistancePrompt,
  buildMedicalPrompt, buildDebtHealthPrompt,
} from '../src/calc/prompts';
import { cityFactor, calcPersonalIncomeTax } from '../src/data/cost';

const FIX_DIR = join(import.meta.dirname, '..', '__fixtures__');
const TOL = { money: 1, rate: 0.001, pct: 0.1 };

let pass = 0;
let fail = 0;
const failures: string[] = [];

function numEq(a: number, b: number, tol: number): boolean {
  return Math.abs(a - b) <= tol;
}

function firstDiff(a: string, b: string): string {
  const len = Math.min(a.length, b.length);
  let i = 0;
  while (i < len && a[i] === b[i]) i++;
  const ctx = (s: string) => JSON.stringify(s.slice(Math.max(0, i - 20), i + 20));
  return `idx=${i} 实际=${ctx(a)} 期望=${ctx(b)}`;
}

function load(name: string): any {
  return JSON.parse(readFileSync(join(FIX_DIR, name), 'utf-8'));
}

// ---------- situation 单例对拍 ----------
function verifySituation(file: string): void {
  const fx = load(file);
  const actual: any = computeCurrentSituation(fx.input);
  const exp: any = fx.expected;
  const e: string[] = [];
  const ck = (field: string, tol: number) => {
    if (!numEq(actual[field], exp[field], tol)) e.push(`${field}: ${actual[field]} ≠ ${exp[field]}`);
  };
  ck('cost_total', TOL.money);
  ck('social_ins', TOL.money);
  ck('tax', TOL.money);
  ck('income_net', TOL.money);
  ck('surplus', TOL.money);
  ck('survival_baseline', TOL.money);
  ck('special_total', TOL.money);
  ck('surplus_rate', TOL.pct);
  ck('tax_rate', TOL.rate);
  if (exp.house_saving_years === null) {
    if (actual.house_saving_years !== null) e.push('house_saving_years: 应为 null');
  } else if (actual.house_saving_years === null) {
    e.push('house_saving_years: 应非 null');
  } else if (!numEq(actual.house_saving_years, exp.house_saving_years, TOL.pct)) {
    e.push(`house_saving_years: ${actual.house_saving_years} ≠ ${exp.house_saving_years}`);
  }
  // cost_rows 逐项
  if (actual.cost_rows.length !== exp.cost_rows.length) {
    e.push(`cost_rows 行数: ${actual.cost_rows.length} ≠ ${exp.cost_rows.length}`);
  } else {
    for (let i = 0; i < exp.cost_rows.length; i++) {
      const a = actual.cost_rows[i];
      const x = exp.cost_rows[i];
      if (a.item !== x.item) e.push(`cost_rows[${i}].item: "${a.item}" ≠ "${x.item}"`);
      if (a.note !== x.note) e.push(`cost_rows[${i}].note: 实际"${a.note}" ≠ 期望"${x.note}"`);
      if (a._cat !== x._cat) e.push(`cost_rows[${i}]._cat: ${a._cat} ≠ ${x._cat}`);
      if (!numEq(a.amount, x.amount, TOL.money)) e.push(`cost_rows[${i}].amount: ${a.amount} ≠ ${x.amount}`);
    }
  }
  // breakdown 逐 key
  for (const k of Object.keys(exp.breakdown)) {
    const av = actual.breakdown[k];
    if (av === undefined || !numEq(av, exp.breakdown[k], TOL.money)) {
      e.push(`breakdown[${k}]: ${av} ≠ ${exp.breakdown[k]}`);
    }
  }
  // interpretation 严格相等（最强回归捕捉器）
  if (actual.interpretation !== exp.interpretation) {
    e.push(`interpretation 文本不一致\n    ${firstDiff(actual.interpretation, exp.interpretation)}`);
  }
  // assumptions 逐项严格相等
  if (actual.assumptions.length !== exp.assumptions.length) {
    e.push(`assumptions 行数: ${actual.assumptions.length} ≠ ${exp.assumptions.length}`);
  } else {
    for (let i = 0; i < exp.assumptions.length; i++) {
      if (actual.assumptions[i] !== exp.assumptions[i]) {
        e.push(`assumptions[${i}]:\n    实际: ${actual.assumptions[i]}\n    期望: ${exp.assumptions[i]}`);
      }
    }
  }
  report(file, e);
}

// ---------- 批量对拍 ----------
function verifyBatch(file: string, fn: (input: any) => any, tol: (av: any, exp: any) => string[]): void {
  const fx = load(file);
  const e: string[] = [];
  for (const c of fx.cases) {
    const actual = fn(c.input);
    const sub = tol(actual, c.expected);
    for (const s of sub) e.push(`[${c.note}] ${s}`);
  }
  report(file, e);
}

function report(file: string, errs: string[]): void {
  if (errs.length === 0) {
    console.log(`  ✓ ${file}`);
    pass++;
  } else {
    console.log(`  ✗ ${file}`);
    for (const er of errs) console.log(`      ${er}`);
    fail++;
    failures.push(file);
  }
}

/** 递归深比对：数值容差（默认 1e-6，应对浮点末位差）、字符串/布尔/null 严格、数组/对象逐项。 */
function deepCmp(av: any, exp: any, path: string, errs: string[], numTol = 1e-6): void {
  if (typeof exp === 'number' && typeof av === 'number') {
    if (!Object.is(av, exp) && Math.abs(av - exp) > numTol) {
      errs.push(`${path}: ${av} ≠ ${exp} (Δ${(av - exp).toExponential(2)})`);
    }
  } else if (typeof exp === 'string' || typeof exp === 'boolean') {
    if (av !== exp) errs.push(`${path}: 实际${JSON.stringify(av)} ≠ 期望${JSON.stringify(exp)}`);
  } else if (exp === null) {
    if (av !== null) errs.push(`${path}: 应为 null，实际 ${JSON.stringify(av)}`);
  } else if (Array.isArray(exp)) {
    if (!Array.isArray(av)) {
      errs.push(`${path}: 应为数组`);
    } else if (av.length !== exp.length) {
      errs.push(`${path}: 数组长度 ${av.length} ≠ ${exp.length}`);
    } else {
      for (let i = 0; i < exp.length; i++) deepCmp(av[i], exp[i], `${path}[${i}]`, errs, numTol);
    }
  } else if (typeof exp === 'object') {
    if (typeof av !== 'object' || av === null) {
      errs.push(`${path}: 应为对象`);
      return;
    }
    for (const k of Object.keys(exp)) {
      if (!(k in av)) errs.push(`${path}.${k}: 缺失`);
      else deepCmp(av[k], exp[k], `${path}.${k}`, errs, numTol);
    }
  }
}

/** 债务/贷款族对拍（结构各异，统一走 deepCmp） */
function verifyNumeric(file: string, fn: (input: any) => any): void {
  const fx = load(file);
  const e: string[] = [];
  deepCmp(fn(fx.input), fx.expected, '', e);
  report(file, e);
}

// ---------- 主流程 ----------
const situationFiles = [
  'situation_default.json',
  'situation_mid_surplus.json',
  'situation_low_surplus.json',
  'situation_negative_surplus.json',
  'situation_edge_no_insurance.json',
  'situation_edge_children.json',
  'situation_edge_housing_loan.json',
  'situation_edge_overrides.json',
  'situation_edge_freelance.json',
  'situation_last_profile.json',
];

console.log('交叉验证：TS vs Python 黄金基准\n');

for (const f of situationFiles) verifySituation(f);

verifyBatch('survival_baseline.json', (i) => survivalBaseline(i.tier, i.insuranceMode), (av, exp) =>
  numEq(av, exp, TOL.money) ? [] : [`survivalBaseline: ${av} ≠ ${exp}`],
);

verifyBatch('normalize_children.json', (i) => normalizeChildrenByAge(i.childrenByAge, i.numChildren), (av, exp) =>
  JSON.stringify(av) === JSON.stringify(exp) ? [] : [`normalize: 实际${JSON.stringify(av)} ≠ 期望${JSON.stringify(exp)}`],
);

verifyBatch('tax_brackets.json', (i) => calcPersonalIncomeTax(i.taxableMonthly), (av, exp) => {
  const e: string[] = [];
  if (!numEq(av[0], exp[0], TOL.money)) e.push(`tax: ${av[0]} ≠ ${exp[0]}`);
  if (!numEq(av[1], exp[1], TOL.rate)) e.push(`rate: ${av[1]} ≠ ${exp[1]}`);
  if (av[2] !== exp[2]) e.push(`quick: ${av[2]} ≠ ${exp[2]}`);
  return e;
});

verifyBatch('city_factor.json', (i) => cityFactor(i.tier), (av, exp) =>
  numEq(av, exp, TOL.rate) ? [] : [`cityFactor: ${av} ≠ ${exp}`],
);

console.log('\n债务/贷款计算族（批次2）：');
const numericCases: Record<string, (input: any) => any> = {
  loan_methods: (i) => compareLoanMethods(i.principal, i.nominalApr, i.periods),
  affordable_debt: (i) => computeAffordableDebt(i.monthlySurplus, i.nominalApr, i.periods),
  loan_apr_normal: (i) => computeLoanApr(i.principal, i.monthlyPayment, i.periods),
  loan_apr_high: (i) => computeLoanApr(i.principal, i.monthlyPayment, i.periods),
  loan_apr_extreme: (i) => computeLoanApr(i.principal, i.monthlyPayment, i.periods),
  debt_payoff_snowball: (i) => simulateDebtPayoff(i.debts, i.method, i.extraMonthly),
  debt_payoff_avalanche: (i) => simulateDebtPayoff(i.debts, i.method, i.extraMonthly),
  debt_payoff_unpayable: (i) => simulateDebtPayoff(i.debts, i.method, i.extraMonthly),
  loan_spiral: (i) => simulateLoanSpiral(i.initialBalance, i.annualRate, i.months, i.actualMonthlyPayment),
  overtime_basic: (i) => computeOvertimePay(i.monthlyWage, i.weekdayOt, i.weekendOt, i.holidayOt),
  overtime_zero: (i) => computeOvertimePay(i.monthlyWage, i.weekdayOt, i.weekendOt, i.holidayOt),
  min_wage_ok: (i) => computeMinWageCheck(i.monthlyWage, i.tier),
  min_wage_illegal: (i) => computeMinWageCheck(i.monthlyWage, i.tier),
  claim_part_employed: (i) => assessOvertimeClaim(i.owedAmount, i.employed, i.evidence),
  claim_no_evidence: (i) => assessOvertimeClaim(i.owedAmount, i.employed, i.evidence),
  claim_small_employed: (i) => assessOvertimeClaim(i.owedAmount, i.employed, i.evidence),
  claim_left_full: (i) => assessOvertimeClaim(i.owedAmount, i.employed, i.evidence),
  debt_health_ok: (i) => assessDebtHealth(i.totalDebt, i.monthlyIncome, i.monthlyPay, i.avgApr),
  debt_health_warn: (i) => assessDebtHealth(i.totalDebt, i.monthlyIncome, i.monthlyPay, i.avgApr),
  debt_health_runaway: (i) => assessDebtHealth(i.totalDebt, i.monthlyIncome, i.monthlyPay, i.avgApr),
  buy_rent_basic: (i) => compareBuyRent(i.tier, i.years, i.houseArea, i.downRatio, i.commercialRate, i.fundRate, i.rentMonthly, i.loanYears),
  buy_rent_custom: (i) => compareBuyRent(i.tier, i.years, i.houseArea, i.downRatio, i.commercialRate, i.fundRate, i.rentMonthly, i.loanYears),
  housing_fund_basic: (i) => housingFundLoan(i.tier, i.balance, i.monthlyContribution, i.years),
  housing_fund_no_contrib: (i) => housingFundLoan(i.tier, i.balance, i.monthlyContribution, i.years),
  rate_stress_basic: (i) => rateStressTest(i.principal, i.baseRate, i.years),
  bonus_tax_high: (i) => bonusTaxCompare(i.annualSalary, i.bonus, i.annualSpecial, i.annualSocial),
  bonus_tax_low: (i) => bonusTaxCompare(i.annualSalary, i.bonus, i.annualSpecial, i.annualSocial),
  special_deduction_full: (i) => specialDeductionHints(i.hasChildren, i.supportElderly, i.hasLoan, i.continuingEdu),
  special_deduction_empty: (i) => specialDeductionHints(i.hasChildren, i.supportElderly, i.hasLoan, i.continuingEdu),
  life_cost_basic: (i) => computeLifeCost(i.tier, i.level, i.birthMode, i.careMode, i.uniType, i.graduate, i.retireAge, i.purchaseMode),
  life_cost_high: (i) => computeLifeCost(i.tier, i.level, i.birthMode, i.careMode, i.uniType, i.graduate, i.retireAge, i.purchaseMode),
  life_cost_grad: (i) => computeLifeCost(i.tier, i.level, i.birthMode, i.careMode, i.uniType, i.graduate, i.retireAge, i.purchaseMode),
  risk_basic: (i) => computeRiskIndicators(i.savings, i.survivalBaseline),
  risk_low_savings: (i) => computeRiskIndicators(i.savings, i.survivalBaseline),
  target_wage_up: (i) => estimateTargetWage(i.wage, i.currentTier, i.targetTier),
  compare_cities_up: (i) => compareCities(i.wage, i.currentTier, i.targetTier, i.insuranceMode, i.housing, i.foodLevel, i.hasCar, i.numChildren, i.childrenByAge, i.supportElderly, i.supportFamilyMonthly),
  compare_cities_down: (i) => compareCities(i.wage, i.currentTier, i.targetTier, i.insuranceMode, i.housing, i.foodLevel, i.hasCar, i.numChildren, i.childrenByAge, i.supportElderly, i.supportFamilyMonthly),
  compare_cities_with_kids: (i) => compareCities(i.wage, i.currentTier, i.targetTier, i.insuranceMode, i.housing, i.foodLevel, i.hasCar, i.numChildren, i.childrenByAge, i.supportElderly, i.supportFamilyMonthly),
};
for (const [name, fn] of Object.entries(numericCases)) verifyNumeric(`${name}.json`, fn);

console.log('\n提示词生成（批次4，纯字符串严格对拍）：');
const promptCases: Record<string, (i: any) => string> = {
  prompt_overtime: (i) => buildOvertimePrompt(i.wage, i.weekdayOt, i.weekendOt, i.holidayOt, i.actual, i.months, i.employed, i.evidence, i.city),
  prompt_loan_apr: (i) => buildLoanAprPrompt(i.principal, i.monthly, i.periods, i.profile),
  prompt_compare_methods: (i) => buildCompareMethodsPrompt(i.principal, i.aprPct, i.periods, i.profile),
  prompt_affordable_debt: (i) => buildAffordableDebtPrompt(i.surplus, i.aprPct, i.periods, i.income, i.profile),
  prompt_debt_payoff: (i) => buildDebtPayoffPrompt(i.debtsDesc, i.extra),
  prompt_spiral: (i) => buildSpiralPrompt(i.init, i.aprPct, i.months, i.pay, i.profile),
  prompt_min_wage: (i) => buildMinWagePrompt(i.wage, i.tier, i.city, i.profile),
  prompt_unemployment: (i) => buildUnemploymentPrompt(i.city, i.years, i.wage, i.reason, i.profile),
  prompt_unemployment_sparse: (i) => buildUnemploymentPrompt(i.city, i.years, i.wage, i.reason, i.profile),
  prompt_subsidy: (i) => buildSubsidyPrompt(i.city, i.profile),
  prompt_help: (i) => buildHelpPrompt(i.sceneKey, i.city),
  prompt_help_unknown: (i) => buildHelpPrompt(i.sceneKey, i.city),
  prompt_antifraud: (i) => buildAntifraudPrompt(i.key, i.city),
  prompt_current_situation: (i) => buildCurrentSituationPrompt(i.age, i.tier, i.wage, i.ins, i.housing, i.food, i.hasCar, i.numKids, i.supportElderly, i.savings, i.city, i.childrenByAge, i.familyMonthly, i.hasPartner, i.partnerWage, i.partnerIns),
  prompt_milestones: (i) => buildMilestonesPrompt(i.tier, i.wage, i.city, i.profile),
  prompt_compare: (i) => buildComparePrompt(i.tierA, i.tierB, i.wage, i.targetCity, i.housing, i.food, i.hasCar, i.insurance),
  prompt_injury: (i) => buildInjuryPrompt(i.city, i.grade, i.monthlyWage, i.profile),
  prompt_buy_rent: (i) => buildBuyRentPrompt(i.tier, i.years, i.area, i.downRatio, i.city, i.profile),
  prompt_fund: (i) => buildFundPrompt(i.tier, i.balance, i.contrib, i.years, i.city, i.profile),
  prompt_rate_stress: (i) => buildRateStressPrompt(i.principal, i.baseRate, i.years, i.city, i.profile),
  prompt_tax: (i) => buildTaxPrompt(i.annualSalary, i.bonus, i.city, i.special, i.social, i.kids, i.elderly, i.loan, i.edu, i.profile),
  prompt_assistance: (i) => buildAssistancePrompt(i.city, i.perCapitaIncome, i.familyInfo, i.asset, i.profile),
  prompt_medical: (i) => buildMedicalPrompt(i.city, i.identity, i.cost, i.retired, i.remote, i.profile),
  prompt_debt_health: (i) => buildDebtHealthPrompt(i.totalDebt, i.monthlyIncome, i.monthlyPay, i.avgApr, i.profile),
};
for (const [name, fn] of Object.entries(promptCases)) {
  const fx = load(`${name}.json`);
  const e: string[] = [];
  deepCmp(fn(fx.input), fx.expected, '', e);
  report(`${name}.json`, e);
}

console.log('\n数据模块 + 薄封装（批次5）：');
const dataTol = (av: any, exp: any): string[] => {
  const e: string[] = [];
  deepCmp(av, exp, '', e);
  return e;
};
verifyBatch('data_min_wage.json', (i) => getMinWageForCity(i.city), dataTol);
verifyBatch('data_unemployment.json', (i) => estimateUnemploymentPay(i.city), dataTol);
verifyBatch('data_unemploy_duration.json', (i) => unemployDuration(i.years), dataTol);
verifyBatch('data_injury_one_time.json', (i) => calcInjuryOneTime(i.grade, i.monthlyWage), dataTol);
verifyBatch('data_injury_pension.json', (i) => calcInjuryPension(i.grade, i.monthlyWage), dataTol);
verifyBatch('data_injury_extra.json', (i) => getProvinceInjuryExtra(i.province, i.grade), dataTol);
verifyBatch('data_dibao.json', (i) => getDibaoForCity(i.city), dataTol);
verifyBatch('data_tekun.json', (i) => getTekunForCity(i.city), dataTol);
verifyBatch('data_inpatient.json', (i) => estimateInpatient(i.city, i.identity, i.cost, i.remote, i.retired), dataTol);
verifyBatch('data_check_relief.json', (i) => checkRelief(i.city, i.perCapitaIncome, i.familySize, i.asset), dataTol);
verifyBatch('data_medical_cost.json', (i) => estimateMedicalCost(i.city, i.identity, i.cost, i.remote, i.retired), dataTol);

console.log('\n家庭/双收入（需重建 self_result）：');
for (const file of ['family_basic.json', 'family_no_partner.json']) {
  const fx = load(file);
  const selfResult = computeCurrentSituation({
    age: fx.input.selfAge,
    wagePretax: fx.input.selfWage,
    tier: fx.input.selfTier,
    housing: '合租单间',
    foodLevel: '普通',
    insuranceMode: fx.input.selfInsurance ?? '在职（单位缴）',
  });
  const actual = computeFamilySituation(
    selfResult,
    fx.input.partnerWage,
    fx.input.partnerTier ?? fx.input.selfTier,
    fx.input.partnerInsurance ?? '在职（单位缴）',
  );
  const e: string[] = [];
  deepCmp(actual, fx.expected, '', e);
  report(file, e);
}

console.log(`\n${pass} passed, ${fail} failed`);
if (fail > 0) {
  console.log(`失败: ${failures.join(', ')}`);
  process.exit(1);
}
