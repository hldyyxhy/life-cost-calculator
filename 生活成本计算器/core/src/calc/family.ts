// calc/family.ts —— 家庭双收入/抗风险/工资预估/轻量结余（calc_engine.py:575-676, 589-599）
import { cityFactor, calcPersonalIncomeTax } from '../data/cost';
import { computeCurrentSituation } from './situation';
import type { SituationResult } from '../types';
import costRaw from '../data/cost.json';

const C = costRaw as unknown as Record<string, any>;
const TYPICAL_WAGE = C.TYPICAL_WAGE as Record<string, number>;
const SOCIAL_INSURANCE_MONTHLY = C.SOCIAL_INSURANCE_MONTHLY as Record<string, any>;
const FREELANCE_INSURANCE_MONTHLY = C.FREELANCE_INSURANCE_MONTHLY as Record<string, any>;
const TAX_THRESHOLD = C.TAX_THRESHOLD as number;
const PARTNER_PERSONAL_MONTHLY = C.PARTNER_PERSONAL_MONTHLY as number;

/** _estimate_target_wage (575)：按目标城市相对当前城市典型工资等比例缩放。 */
export function estimateTargetWage(wage: number, currentTier: string, targetTier: string): number {
  const cur = TYPICAL_WAGE[currentTier] ?? 5000;
  const tgt = TYPICAL_WAGE[targetTier] ?? 5000;
  return cur ? wage * (tgt / cur) : wage;
}

/** compute_surplus (589)：轻量月结余（避免跑完整 situation 拿 surplus）。 */
export function computeSurplus(
  wage: number,
  tier: string,
  housing: string = '合租单间',
  foodLevel: string = '普通',
  insuranceMode: string = '在职（单位缴）',
): number {
  return computeCurrentSituation({ age: 30, wagePretax: wage, tier, housing, foodLevel, insuranceMode }).surplus;
}

/** compute_family_situation (602)：双收入家庭结余（伴侣净增收口径）。 */
export function computeFamilySituation(
  selfResult: SituationResult,
  partnerWage: number,
  tier: string,
  partnerInsurance: string = '在职（单位缴）',
): { partner_income_net: number; partner_surplus: number; family_surplus: number; family_surplus_rate: number } {
  const self_surplus = selfResult.surplus;
  const self_income_net = selfResult.income_net;

  if (!partnerWage || partnerWage <= 0) {
    const rate = self_income_net > 0 ? (self_surplus / self_income_net) * 100 : 0;
    return {
      partner_income_net: 0,
      partner_surplus: 0,
      family_surplus: Math.round(self_surplus),
      family_surplus_rate: Math.round(rate * 10) / 10,
    };
  }

  let p_social: number;
  if (partnerInsurance === '在职（单位缴）') p_social = SOCIAL_INSURANCE_MONTHLY[tier] ?? 0;
  else if (partnerInsurance === '灵活就业（全自缴）') p_social = FREELANCE_INSURANCE_MONTHLY[tier] ?? 0;
  else p_social = 0;

  const p_taxable = Math.max(partnerWage - p_social - TAX_THRESHOLD, 0);
  const [p_tax] = calcPersonalIncomeTax(p_taxable);
  const p_income_net = partnerWage - p_social - p_tax;
  const p_personal = PARTNER_PERSONAL_MONTHLY * cityFactor(tier);
  const p_surplus = p_income_net - p_personal;

  const family = self_surplus + p_surplus;
  const family_income = self_income_net + p_income_net;
  const rate = family_income > 0 ? (family / family_income) * 100 : 0;
  return {
    partner_income_net: Math.round(p_income_net),
    partner_surplus: Math.round(p_surplus),
    family_surplus: Math.round(family),
    family_surplus_rate: Math.round(rate * 10) / 10,
  };
}

/** compute_risk_indicators (647)：抗风险指标（失业月数/应急金/大病风险）。 */
export function computeRiskIndicators(
  savings: number,
  survivalBaseline: number,
): { unemployment_months: number; emergency_fund_low: number; emergency_fund_high: number; emergency_gap: number; severe_illness_risk: string } {
  savings = savings || 0;
  const baseline = survivalBaseline || 1;
  const unemp = baseline > 0 ? savings / baseline : 0;
  const fund_low = baseline * 3;
  const fund_high = baseline * 6;
  const gap = fund_low - savings;
  const severe_low = 50000;
  const severe_high = 100000;
  let severe_risk: string;
  if (savings < severe_low) severe_risk = 'high';
  else if (savings < severe_high) severe_risk = 'medium';
  else severe_risk = 'low';
  return {
    unemployment_months: Math.round(unemp * 10) / 10,
    emergency_fund_low: Math.round(fund_low),
    emergency_fund_high: Math.round(fund_high),
    emergency_gap: Math.round(gap),
    severe_illness_risk: severe_risk,
  };
}
