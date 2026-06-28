// data/relief.ts —— relief_data.py 查询函数（低保/特困）
import reliefRaw from './relief.json';
import rightsRaw from './rights.json';
import costRaw from './cost.json';

const RL = reliefRaw as unknown as Record<string, any>;
const R = rightsRaw as unknown as Record<string, any>;
const C = costRaw as unknown as Record<string, any>;
const DIBAO_STANDARD = RL.DIBAO_STANDARD as Record<string, number>;
const TEKUN_CITY_OVERRIDE = RL.TEKUN_CITY_OVERRIDE as Record<string, [number, number]>;
const TEKUN_RATIO_DEFAULT = RL.TEKUN_RATIO_DEFAULT as number;
const DIBAO_TIER_RANGE = RL.DIBAO_TIER_RANGE as Record<string, [number, number]>;
const CITY_TO_PROVINCE = R.CITY_TO_PROVINCE as Record<string, string>;
const CITY_TO_TIER = C.CITY_TO_TIER as Record<string, string>;

/** get_dibao_for_city (230)：查城市低保。返回 [金额|null, 说明, 是否估算]。四级 fallback。 */
export function getDibaoForCity(city: string): [number | null, string, boolean] {
  if (!city) return [null, '请选择城市', true];
  // ① 城市精确
  if (city in DIBAO_STANDARD) return [DIBAO_STANDARD[city], `${city} 标准`, false];
  // ② 含「（{city}」的键
  const prefix = `（${city}`;
  for (const [key, val] of Object.entries(DIBAO_STANDARD)) {
    if (key.includes(prefix)) return [val, `${key} 标准`, false];
  }
  // ③ 省名兜底
  const prov = CITY_TO_PROVINCE[city];
  if (prov && prov in DIBAO_STANDARD && prov !== '深圳') {
    const hasSub = Object.keys(DIBAO_STANDARD).some((k) => k.startsWith(`${prov}（`));
    if (hasSub) return [DIBAO_STANDARD[prov], `${prov} 省级最低（${city} 按省估算）`, true];
    return [DIBAO_STANDARD[prov], `${prov} 全省统一（含 ${city}）`, false];
  }
  // ④ tier fallback
  const tier = CITY_TO_TIER[city];
  if (tier) {
    const range = DIBAO_TIER_RANGE[tier] ?? [700, 850];
    return [Math.floor((range[0] + range[1]) / 2), `${tier}城市估算（${city} 暂无精确数据，按等级中值）`, true];
  }
  return [null, '未找到该地数据，请咨询当地民政（街道/12345）', true];
}

/** get_tekun_for_city (260)：特困人员基本生活标准。返回 [金额|null, 说明]。 */
export function getTekunForCity(city: string): [number | null, string] {
  if (city in TEKUN_CITY_OVERRIDE) {
    const [amt, ratio] = TEKUN_CITY_OVERRIDE[city];
    return [amt, `${city} 特困标准 ${amt} 元/月（低保 × ${ratio}）`];
  }
  const [dibao] = getDibaoForCity(city);
  if (dibao) {
    const amt = Math.round(dibao * TEKUN_RATIO_DEFAULT);
    return [amt, `${city} 特困 ≈ 低保 × 1.3 ≈ ${amt} 元/月（估算）`];
  }
  return [null, '未找到该地数据'];
}
