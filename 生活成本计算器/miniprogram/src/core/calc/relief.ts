// calc/relief.ts —— check_relief（本地救助对照）+ estimate_medical_cost（薄封装）
import { getDibaoForCity } from '../data/relief';
import { estimateInpatient } from '../data/medical';
import rightsRaw from '../data/rights.json';
import reliefRaw from '../data/relief.json';
import { group } from '../fmt';

const R = rightsRaw as unknown as Record<string, any>;
const RL = reliefRaw as unknown as Record<string, any>;
const CITY_TO_PROVINCE = R.CITY_TO_PROVINCE as Record<string, string>;
const DIBAO_EDGE_RATIO = RL.DIBAO_EDGE_RATIO as number;
const DIBAO_EDGE_RATIO_MAX = RL.DIBAO_EDGE_RATIO_MAX as number;
const DIBAO_EDGE_ASSISTANCE = RL.DIBAO_EDGE_ASSISTANCE as string[];
const PROPERTY_LIMIT = RL.PROPERTY_LIMIT as Record<string, any>;
const PROPERTY_LIMIT_COMMON = RL.PROPERTY_LIMIT_COMMON as Record<string, any>;

/** check_relief (2311)：对照当地低保/边缘/特困，判断符合/接近/不符。 */
export function checkRelief(city: string, perCapitaIncome: number, familySize: number = 1, asset: number | null = null): any {
  const [dibao, dbNote, dbEst] = getDibaoForCity(city);
  if (dibao === null) return { error: dbNote };

  const income = perCapitaIncome;
  const edge = dibao * DIBAO_EDGE_RATIO;
  const edgeMax = dibao * DIBAO_EDGE_RATIO_MAX;

  let matched: string;
  let head: string;
  let color: string;
  let detail: string;

  if (income < dibao) {
    matched = '符合低保';
    head = `✅ 人均月收入 ${group(income)} 元 < 当地低保 ${dibao} 元/月（${dbNote}）`;
    color = 'surplus';
    detail = `→ 大概率符合低保，可领差额补助（补到 ${dibao} 元/月）。\n申请：户籍地街道/乡镇民政，或 12345 转民政；带身份证、收入/财产证明。`;
  } else if (income < edge) {
    matched = '低保边缘家庭';
    head = `⚠️ 人均收入 ${group(income)} 在低保边缘区间（${dibao} ~ ${group(edge)} 元）`;
    color = 'accent';
    detail = `→ 属低保边缘家庭，可享专项救助：${DIBAO_EDGE_ASSISTANCE.join('、')}\n（边缘线 = 低保 × 1.5 = ${group(edge)}，部分地区放宽至 2 倍 = ${group(edgeMax)}）`;
  } else if (income < edgeMax) {
    matched = '距边缘线较近';
    head = `人均收入 ${group(income)}，距低保边缘线（${group(edge)}）差 ${group(income - edge)} 元`;
    color = 'neutral';
    detail = '→ 暂不符合，但若收入下降或遇大病/失业，可申请临时救助（低保 × 2~12 倍）。';
  } else {
    matched = '不符合';
    head = `人均收入 ${group(income)} 明显高于低保边缘线（${group(edge)}），不符合低保。`;
    color = 'deficit';
    detail = '→ 工具只是粗算，最终以当地民政认定为准。';
  }

  let propHint = '';
  if (asset !== null && asset > 0) {
    const prov = CITY_TO_PROVINCE[city] ?? city;
    const limit = PROPERTY_LIMIT[prov] ?? PROPERTY_LIMIT_COMMON;
    const fin = limit['金融资产人均'] || limit['金融资产'] || '人均不超过当地年低保×2~4倍';
    const over = asset > dibao * 36;
    propHint = `\n\n【财产提醒】当地金融资产限制：${fin}。你填的人均金融资产 ${group(asset)} 元，${over ? '可能因财产超标影响认定，以民政核实为准。' : '未明显超标。'}`;
  }

  let note = head + '\n' + detail + propHint + '\n\n【临时救助】遇急难（大病/意外）可申请，约低保月标准 × 2~12 倍。';
  if (dbEst) note += `\n\n⚠️ ${dbNote}（数据为估算，请用「问 AI」查当地最新标准）。`;

  return { dibao, edge, edge_max: edgeMax, tier_matched: matched, head, color, note, estimated: dbEst };
}

/** estimate_medical_cost (2385)：住院报销估算（薄封装 medical_data.estimate_inpatient）。 */
export function estimateMedicalCost(city: string, identity: string = '职工', cost: number = 50000, remote: string = 'none', retired: boolean = false): any {
  return estimateInpatient(city, identity, cost, remote, retired);
}
