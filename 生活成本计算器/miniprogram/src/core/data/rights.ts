// data/rights.ts —— rights_data.py 查询函数（最低工资/失业金/工伤）
import rightsRaw from './rights.json';
import { pct0 } from '../fmt';

const R = rightsRaw as unknown as Record<string, any>;
const PROVINCE_MIN_WAGE = R.PROVINCE_MIN_WAGE as Record<string, number>;
const CITY_TO_PROVINCE = R.CITY_TO_PROVINCE as Record<string, string>;
const UNEMPLOYMENT_INSURANCE = R.UNEMPLOYMENT_INSURANCE as Record<string, any>;
const UNEMPLOYMENT_FALLBACK = R.UNEMPLOYMENT_FALLBACK as Record<string, any>;
const UNEMPLOYMENT_DURATION = R.UNEMPLOYMENT_DURATION as [number, number][];
const INJURY_ONE_TIME = R.INJURY_ONE_TIME as Record<string, number>;
const INJURY_PENSION_RATIO = R.INJURY_PENSION_RATIO as Record<string, number>;
const PROVINCE_INJURY_EXTRA = R.PROVINCE_INJURY_EXTRA as Record<string, any>;

/** get_min_wage_for_city (466)：城市 → 所在省最低工资（第一档）。 */
export function getMinWageForCity(cityName: string): number | null {
  const prov = CITY_TO_PROVINCE[cityName];
  if (!prov) return null;
  return PROVINCE_MIN_WAGE[prov] ?? null;
}

/** estimate_unemployment_pay (474)：估算失业金月标准，返回 [元/月|null, 说明]。 */
export function estimateUnemploymentPay(provinceOrCity: string): [number | null, string] {
  const prov = CITY_TO_PROVINCE[provinceOrCity] ?? provinceOrCity;
  if (!prov) return [null, '未找到该地区数据'];

  if (prov in UNEMPLOYMENT_INSURANCE) {
    const val = UNEMPLOYMENT_INSURANCE[prov];
    if (val.amount) return [val.amount, `${prov}标准`];
    if (val.ratio) {
      const mw = PROVINCE_MIN_WAGE[prov];
      if (mw) return [Math.round(mw * val.ratio), `按${prov}最低工资${mw}×${pct0(val.ratio)}估算`];
    }
  }
  // 模糊匹配：带括号的键（如"湖北（一类）"）
  let bestKey: string | null = null;
  for (const key of Object.keys(UNEMPLOYMENT_INSURANCE)) {
    if (key.startsWith(prov + '（') || key.startsWith(prov + '(')) {
      bestKey = key;
      break;
    }
  }
  if (bestKey) {
    const val = UNEMPLOYMENT_INSURANCE[bestKey];
    if (val.amount) return [val.amount, `${bestKey}标准`];
    if (val.ratio) {
      const mw = PROVINCE_MIN_WAGE[prov];
      if (mw) return [Math.round(mw * val.ratio), `按${prov}最低工资${mw}×${pct0(val.ratio)}估算`];
    }
  }
  // fallback
  const fb = UNEMPLOYMENT_FALLBACK[prov];
  if (fb) {
    if (fb.ratio === null) return [null, fb.note ?? '需查阅当地人社局公告'];
    const mw = PROVINCE_MIN_WAGE[fb.province];
    if (mw && fb.ratio) return [Math.round(mw * fb.ratio), `按${fb.province}最低工资${mw}×${pct0(fb.ratio)}估算`];
  }
  return [null, '需查阅当地人社局公告'];
}

/** unemploy_duration (517)：累计缴费年限 → 最长领取月数。 */
export function unemployDuration(yearsOfInsurance: number): number {
  if (yearsOfInsurance < 1) return 0;
  const sorted = [...UNEMPLOYMENT_DURATION].sort((a, b) => b[0] - a[0]);
  for (const [minYears, months] of sorted) {
    if (yearsOfInsurance >= minYears) return months;
  }
  return 0;
}

/** calc_injury_one_time (530)：一次性伤残补助金。返回 [月数, 金额]。 */
export function calcInjuryOneTime(grade: number, monthlyWage: number): [number, number] {
  const months = INJURY_ONE_TIME[grade] ?? 0;
  return [months, months * monthlyWage];
}

/** calc_injury_pension (541)：伤残津贴月标准（1-6 级）。返回 [比例, 月金额, 支付方]。 */
export function calcInjuryPension(grade: number, monthlyWage: number): [number | null, number, string] {
  const ratio = INJURY_PENSION_RATIO[grade];
  if (!ratio) return [null, 0, '无（7-10级不享受按月伤残津贴）'];
  const payer = grade <= 4 ? '工伤保险基金' : '用人单位';
  return [ratio, monthlyWage * ratio, payer];
}

/** get_province_injury_extra (553)：各省一次性工伤医疗/就业补助金。返回 [医疗, 就业, 基数说明]。 */
export function getProvinceInjuryExtra(province: string, grade: number): [number | null, number | null, string] {
  const data = PROVINCE_INJURY_EXTRA[province];
  if (!data) return [null, null, '数据未收录，请查阅当地公告'];
  const levelData = data.levels[grade];
  if (!levelData) return [null, null, '该等级数据未收录'];
  return [levelData[0], levelData[1], data.base];
}
