// data/medical.ts —— medical_data.py 查询函数（职工住院报销率/住院估算）
import medicalRaw from './medical.json';
import rightsRaw from './rights.json';
import costRaw from './cost.json';
import { group, pct0 } from '../fmt';

const M = medicalRaw as unknown as Record<string, any>;
const R = rightsRaw as unknown as Record<string, any>;
const C = costRaw as unknown as Record<string, any>;
const EMPLOYEE_INPATIENT = M.EMPLOYEE_INPATIENT;
const RESIDENT_INPATIENT = M.RESIDENT_INPATIENT;
const EMPLOYEE_TIER_FALLBACK = M.EMPLOYEE_TIER_FALLBACK;
const REMOTE_DROP = M.REMOTE_DROP as Record<string, number>;
const BIGILLNESS = M.BIGILLNESS as Record<string, any>;
const BIGILLNESS_DEFAULT_TIERS = M.BIGILLNESS_DEFAULT_TIERS as any[];
const BIGILLNESS_DEDUCTIBLE_RANGE = M.BIGILLNESS_DEDUCTIBLE_RANGE as [number, number];
const DRG_NOTE = M.DRG_NOTE as string;
const CITY_TO_PROVINCE = R.CITY_TO_PROVINCE as Record<string, string>;
const CITY_TO_TIER = C.CITY_TO_TIER as Record<string, string>;
// _PROVINCE_ALIAS 是私有未导出，这里硬编码（深圳归广东）
const PROVINCE_ALIAS: Record<string, string> = { 深圳: '广东' };

/** _resolve_province (162)：城市 → 省名（深圳归广东）。 */
function resolveProvince(city: string): string | null {
  if (city in EMPLOYEE_INPATIENT) return city;
  const prov = CITY_TO_PROVINCE[city];
  return PROVINCE_ALIAS[prov] ?? prov ?? null;
}

/** get_employee_rate (170)：查职工住院报销。返回 [在职比, 退休比, 起付, 封顶, 说明, 是否估算]。 */
export function getEmployeeRate(city: string): [number | null, number | null, number | null, number | null, string, boolean] {
  const prov = resolveProvince(city);
  if (prov && prov in EMPLOYEE_INPATIENT) {
    const d = EMPLOYEE_INPATIENT[prov];
    const emp = d['在职'];
    const ret = d['退休'] !== null ? d['退休'] : Math.min(emp + 0.04, 0.97);
    return [emp, ret, d['起付'], d['封顶'], `${prov}（${d['城市']}）标准`, d.ret_est ?? false];
  }
  const tier = CITY_TO_TIER[city];
  if (tier) {
    const fb = EMPLOYEE_TIER_FALLBACK[tier];
    const emp = (fb['报销比'][0] + fb['报销比'][1]) / 2;
    const ret = emp + 0.04;
    const ded = (fb['起付'][0] + fb['起付'][1]) / 2;
    const cap = fb['封顶'][1] || fb['封顶'][0];
    return [emp, ret, ded, cap, `${tier} 城市估算（${city}）`, true];
  }
  return [null, null, null, null, '未找到该地数据', true];
}

/** estimate_inpatient (189)：住院报销估算（基本医保 + 大病 + 异地调整）。 */
export function estimateInpatient(city: string, identity: string = '职工', cost: number = 50000, remote: string = 'none', retired: boolean = false): any {
  if (cost <= 0) return { error: '住院费用需大于 0。' };

  let rate: number;
  let ded: number | null;
  let cap: number | null;
  let note: string;
  let est: boolean;
  if (identity === '职工') {
    const [emp, ret, dedR, capR, noteR, estR] = getEmployeeRate(city);
    if (emp === null) return { error: noteR };
    rate = retired ? (ret as number) : emp;
    ded = dedR;
    cap = capR;
    note = noteR;
    est = estR;
  } else {
    const tier = CITY_TO_TIER[city] || '三线';
    const fb = RESIDENT_INPATIENT[tier] ?? RESIDENT_INPATIENT['三线'];
    rate = (fb['报销比'][0] + fb['报销比'][1]) / 2;
    ded = (fb['起付'][0] + fb['起付'][1]) / 2;
    cap = (fb['封顶'][0] + fb['封顶'][1]) / 2;
    note = `${tier} 城市居民估算`;
    est = true;
  }

  let remoteNote = '';
  if (remote in REMOTE_DROP) {
    rate = Math.max(rate - REMOTE_DROP[remote], 0.3);
    remoteNote = `异地${remote === 'filed' ? '已备案降 10' : '未备案降 20'} 个百分点；`;
  }

  const deductible = ded || 800;
  const capLine = cap || 99999999;
  const basePay = Math.min(Math.max(cost - deductible, 0) * rate, capLine);

  // 大病：基本医保后自付超起付触发（简化按首段比例）
  let bigPay = 0.0;
  let bigNote = '';
  const selfAfterBase = cost - basePay;
  const prov = resolveProvince(city);
  const big = BIGILLNESS[prov ?? ''] ?? {};
  const bigDed = big['起付线'] || BIGILLNESS_DEDUCTIBLE_RANGE[0];
  if (selfAfterBase > bigDed) {
    const tiers = big['分段'] || BIGILLNESS_DEFAULT_TIERS;
    const ratio = tiers[0]['比例'];
    bigPay = Math.min((selfAfterBase - bigDed) * ratio, big['封顶'] || 400000);
    bigNote = `基本报销后自付 ${group(selfAfterBase)} 超大病起付线 ${group(bigDed)}，大病再报约 ${group(bigPay)}（按首段 ${pct0(ratio)} 估，精确分段以结算为准）。\n`;
  }

  const totalPay = basePay + bigPay;
  const selfFinal = cost - totalPay;
  const capStr = cap ? group(cap) : '无上限';
  let text =
    `假设 ${city} ${identity}${retired ? '退休' : ''}，三级医院住院 ${group(cost)} 元：\n` +
    `· 报销比约 ${pct0(rate)}，起付线 ${group(deductible)}，封顶 ${capStr}。\n` +
    `${remoteNote}` +
    `· 基本医保报销约 ${group(basePay)} 元。\n` +
    `${bigNote}` +
    `→ 合计报销约 ${group(totalPay)} 元（约 ${pct0(totalPay / cost)}），个人自付约 ${group(selfFinal)} 元。\n` +
    `· DRG 影响：${DRG_NOTE}`;
  text += '\n⚠️ 粗算：未含乙类药先行自付、各地起付线差异、大病分段累进等细节；实际以就诊医院结算为准，可用「问 AI」查精确。';
  if (est) text += `\n（${note}，数据为估算）`;

  return { base_pay: basePay, big_pay: bigPay, total_pay: totalPay, self_pay: selfFinal, rate, note: text, estimated: est };
}
