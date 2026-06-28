// calc/survival.ts —— _survival_baseline (calc_engine.py:548)
// 城市生存底线：极度节俭下的最低月度成本。
import { cityFactor } from '../data/cost';
import costRaw from '../data/cost.json';

const C = costRaw as unknown as Record<string, any>;
const HOUSING = C.HOUSING;
const FOOD = C.FOOD;
const LIFESTYLE_FACTOR = C.LIFESTYLE_FACTOR;
const TRANSPORT = C.TRANSPORT;
const OTHER_MONTHLY = C.OTHER_MONTHLY;
const SOCIAL_INSURANCE_MONTHLY = C.SOCIAL_INSURANCE_MONTHLY;
const FREELANCE_INSURANCE_MONTHLY = C.FREELANCE_INSURANCE_MONTHLY;

export function survivalBaseline(tier: string, insuranceMode: string): number {
  const cf = cityFactor(tier);
  let total = 0;
  total += HOUSING['合租单间'].base * cf * 0.85; // 偏远地区更便宜
  total += HOUSING['含水电物业网费'].base * cf * 0.7; // 水电减半
  total += FOOD.base * cf * LIFESTYLE_FACTOR['节俭']; // 节俭饮食
  total += TRANSPORT['公交地铁通勤'].base * cf; // 公交
  total += Object.values(OTHER_MONTHLY).reduce((s: number, v: any) => s + v.base, 0) * cf * 0.8; // 通讯日用减量
  if (insuranceMode === '在职（单位缴）') total += SOCIAL_INSURANCE_MONTHLY[tier];
  else if (insuranceMode === '灵活就业（全自缴）') total += FREELANCE_INSURANCE_MONTHLY[tier];
  return Math.round(total);
}
