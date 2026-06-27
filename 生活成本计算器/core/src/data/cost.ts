// data/cost.ts —— 读取 cost.json 常量 + 批次0 逻辑函数（翻译自 cost_data.py）
// 数据由 scripts/export_data.py 导出；逻辑函数与 cost_data.py 逐行对照。
import costRaw from './cost.json';

// 常量结构多样，本阶段用宽类型访问；后续可补精确接口
const C = costRaw as unknown as Record<string, any>;

const COST_FACTOR = C.COST_FACTOR as Record<string, number>;
const RAISE_LEVELS = C.RAISE_LEVELS as Record<string, { factor: number }>;
// 末档 upper 在 JSON 里是 null（export_data.py 的 sanitize 把 float('inf')→null），这里还原 Infinity
const TAX_BRACKETS = (C.TAX_BRACKETS as [number | null, number, number][]).map(
  (b) => [b[0] === null ? Infinity : b[0], b[1], b[2]] as [number, number, number],
);
// 末档 upper 为 Infinity（float('inf') → JSON Infinity，JSON.parse 原生支持）

/** 取城市成本系数（cost_data.city_factor:485）—— 未知 tier 返回 1.0 */
export function cityFactor(tier: string): number {
  return COST_FACTOR[tier] ?? 1.0;
}

/** 取养育档位系数（cost_data.raise_factor:490）—— 未知档返回 1.0 */
export function raiseFactor(level: string): number {
  return (RAISE_LEVELS[level] ?? { factor: 1.0 }).factor;
}

/** 基准值 × 城市系数（cost_data.adjust_by_tier:495） */
export function adjustByTier(base: number, tier: string): number {
  return base * cityFactor(tier);
}

/** 基准值 × 城市系数 × 养育档位（cost_data.adjust_by_tier_level:500） */
export function adjustByTierLevel(base: number, tier: string, level: string): number {
  return base * cityFactor(tier) * raiseFactor(level);
}

/**
 * 月度个税（cost_data.calc_personal_income_tax:505）。
 * 返回 [税额, 税率, 速算扣除数]。
 * taxable<=0 返回 [0,0,0]；遍历 TAX_BRACKETS，命中 upper 即 tax=taxable*rate-quick（≥0）。
 */
export function calcPersonalIncomeTax(taxableMonthly: number): [number, number, number] {
  if (taxableMonthly <= 0) return [0.0, 0.0, 0];
  for (const [upper, rate, quick] of TAX_BRACKETS) {
    if (taxableMonthly <= upper) {
      const tax = taxableMonthly * rate - quick;
      return [Math.max(tax, 0.0), rate, quick];
    }
  }
  return [0.0, 0.0, 0];
}

// 年度综合所得累进税率表（末档 upper 同样为 null→Infinity）
const TAX_BRACKETS_ANNUAL = (C.TAX_BRACKETS_ANNUAL as [number | null, number, number][]).map(
  (b) => [b[0] === null ? Infinity : b[0], b[1], b[2]] as [number, number, number],
);

/** calc_annual_income_tax (cost_data.py:520)：年度综合所得个税。返回 [税额, 税率, 速算扣除数]。 */
export function calcAnnualIncomeTax(taxableAnnual: number): [number, number, number] {
  if (taxableAnnual <= 0) return [0.0, 0.0, 0];
  for (const [upper, rate, quick] of TAX_BRACKETS_ANNUAL) {
    if (taxableAnnual <= upper) {
      const tax = taxableAnnual * rate - quick;
      return [Math.max(tax, 0.0), rate, quick];
    }
  }
  return [0.0, 0.0, 0];
}

/** bonus_monthly_rate (cost_data.py:531)：年终奖单独计税，按 amountMonthly(=奖金÷12) 找 [税率, 速算扣除数]。 */
export function bonusMonthlyRate(amountMonthly: number): [number, number] {
  for (const [upper, rate, quick] of TAX_BRACKETS) {
    if (amountMonthly <= upper) return [rate, quick];
  }
  return [0.45, 15160];
}

// fmt_money 暂未译（结果富文本用 calc/money.ts 的 moneyFmt，口径不同）
