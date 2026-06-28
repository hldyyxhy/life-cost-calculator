// calc/lifeCost.ts —— 计算器1：从生到死的一生成本（calc_engine.py:30-245）
// 六阶段汇总（孕育→养育→结婚→工作→养老→丧葬）。依赖大量 cost.json 常量 + pyFloatStr。
import { cityFactor, raiseFactor, calcPersonalIncomeTax } from '../data/cost';
import { fix0, group, pyFloatStr } from '../fmt';
import costRaw from '../data/cost.json';

const C = costRaw as unknown as Record<string, any>;
const PREGNANCY_STAGE = C.PREGNANCY_STAGE as any[];
const DELIVERY_MODES = C.DELIVERY_MODES as Record<string, any>;
const AGE_STAGE = C.AGE_STAGE as Record<string, any>;
const UNI_TYPE_FACTOR = C.UNI_TYPE_FACTOR as Record<string, number>;
const EDUCATION_EXTRA = C.EDUCATION_EXTRA as Record<string, any>;
const EDUCATION_HIGH_BOOST = C.EDUCATION_HIGH_BOOST as number;
const MOON_HIGH_BOOST = C.MOON_HIGH_BOOST as number;
const MARRIAGE_COST = C.MARRIAGE_COST as Record<string, any>;
const HOUSE_PURCHASE = C.HOUSE_PURCHASE as Record<string, any>;
const ADULT_ANNUAL = C.ADULT_ANNUAL as any[];
const TYPICAL_WAGE = C.TYPICAL_WAGE as Record<string, number>;
const SOCIAL_INSURANCE_MONTHLY = C.SOCIAL_INSURANCE_MONTHLY as Record<string, any>;
const TAX_THRESHOLD = C.TAX_THRESHOLD as number;
const HOUSING = C.HOUSING as Record<string, any>;
const FOOD = C.FOOD as any;
const TRANSPORT = C.TRANSPORT as Record<string, any>;
const OTHER_MONTHLY = C.OTHER_MONTHLY as Record<string, any>;
const ADULT_LIVING_FACTOR = C.ADULT_LIVING_FACTOR as Record<string, number>;
const LIFE_EXPECTANCY = C.LIFE_EXPECTANCY as number;
const RETIREMENT = C.RETIREMENT as any;
const FUNERAL = C.FUNERAL as Record<string, any>;

// 养老方式：GUI 短名 → cost_data 里 RETIREMENT.care_monthly 的 key
const CARE_MODE_MAP: Record<string, string> = {
  居家养老: '居家养老（基本生活费）',
  普惠养老机构: '普惠养老机构',
  '中高端养老机构': '中高端养老机构',
};

export function computeLifeCost(
  tier: string,
  level: string,
  birthMode: string = '公立·顺产',
  careMode: string = '居家养老',
  uniType: string = '公办',
  graduate: boolean = false,
  retireAge: number = 60,
  purchaseMode: string = '贷款',
): any {
  const cf = cityFactor(tier);
  const rf = raiseFactor(level);
  const high = level === '高端';

  const rows: any[] = [];
  const add = (stage: string, item: string, amount: number, note: string = '', isIncome = false) => {
    rows.push({ stage, item, amount: Math.round(amount), note, is_income: isIncome });
  };

  // ---------- 阶段1：孕育与生育 ----------
  for (const item of PREGNANCY_STAGE) {
    const base = item.base;
    const amount = item.moon_factor && high ? base * cf * rf * MOON_HIGH_BOOST : base * cf * rf;
    add('一、孕育与生育', item.key, amount, item.note);
  }
  // 分娩方式按倍数调整
  const dm = DELIVERY_MODES[birthMode] ?? DELIVERY_MODES['公立·顺产'];
  for (const r of rows) {
    if (r.item.startsWith('分娩')) {
      r.amount = Math.round(r.amount * dm.mult);
      r.note = dm.note;
      r.item = `分娩（${birthMode}）`;
      break;
    }
  }

  // ---------- 阶段2：0-22 岁逐年养育 + 教育额外 ----------
  const uni_factor = UNI_TYPE_FACTOR[uniType] ?? 1.0;
  const ages = Object.keys(AGE_STAGE).sort((a, b) => Number(a) - Number(b)); // JSON 键为字符串，按数值排序
  for (const ageKey of ages) {
    const info = AGE_STAGE[ageKey];
    if (info.grad && !graduate) continue; // 硕士阶段仅读研时计入
    const stage_name = info.stage;
    const base_cost = stage_name === '大学' || stage_name === '硕士' ? info.base * cf * rf * uni_factor : info.base * cf * rf;
    const edu = EDUCATION_EXTRA[stage_name] ?? { base: 0, note: '' };
    const edu_base = edu.base;
    let edu_cost = 0;
    if (edu_base > 0) {
      const edu_boost = high ? EDUCATION_HIGH_BOOST : 1.0;
      edu_cost = level !== '普惠' ? edu_base * cf * rf * edu_boost : edu_base * cf * 0.5;
    }
    const total_year = base_cost + edu_cost;
    let note: string = info.label;
    if (edu_cost > 0 && level !== '普惠') note += `（含课外/兴趣约 ${group(edu_cost)}）`;
    add(`二、${stage_name}（${info.label}）`, `${Number(ageKey)}岁当年`, total_year, note);
  }

  // ---------- 阶段3：结婚 ----------
  const cai = MARRIAGE_COST['彩礼'][tier];
  add('三、结婚', '彩礼', cai, MARRIAGE_COST['彩礼'].note);
  const wedding = MARRIAGE_COST['婚礼'].base * cf;
  add('三、结婚', '婚礼婚宴婚庆', wedding, MARRIAGE_COST['婚礼'].note);
  const hp = HOUSE_PURCHASE[tier];
  if (purchaseMode === '全款') {
    add('三、结婚', '婚房（全款）', hp.total, `90㎡全款总价约 ${fix0(hp.total / 10000)} 万（${group(hp.total)} 元）`);
  } else {
    const house_dp = MARRIAGE_COST['婚房首付'].base * cf;
    add(
      '三、结婚',
      '婚房首付',
      house_dp,
      `${MARRIAGE_COST['婚房首付'].note}；月供约 ${group(hp.monthly_loan)} 元/月×30年（已近似含于成年居住成本）`,
    );
  }

  // ---------- 阶段4：成年工作期（22/24 岁~退休） ----------
  const work_start = graduate ? 24 : 22;
  const work_years = retireAge - work_start;
  const months = work_years * 12;
  const lf = ADULT_LIVING_FACTOR[level] ?? 1.0;
  const typical_wage = TYPICAL_WAGE[tier] ?? 5000;
  const typical_social = SOCIAL_INSURANCE_MONTHLY[tier] ?? 580;
  for (const item of ADULT_ANNUAL) {
    let amount: number;
    let note: string;
    if (item.key.includes('个人所得税')) {
      const taxable = Math.max(typical_wage - typical_social - TAX_THRESHOLD, 0);
      const [month_tax] = calcPersonalIncomeTax(taxable);
      amount = month_tax * 12 * work_years;
      note = `按${tier}典型月薪 ${group(typical_wage)} 元实算（应纳税所得 ${group(taxable)}，月税 ${fix0(month_tax)}），累计${work_years}年`;
    } else {
      amount = item.base * cf * work_years;
      note = `${item.note}（按工作${work_years}年累计）`;
    }
    add('四、成年工作期', `${item.key}（累计${work_years}年）`, amount, note);
  }
  // 成年人日常生存成本
  const living_items: [string, number][] = [
    ['住房与水电（合租/等额居住）', HOUSING['合租单间'].base + HOUSING['含水电物业网费'].base],
    ['饮食', FOOD.base],
    ['交通（公交地铁）', TRANSPORT['公交地铁通勤'].base],
    ['通讯+日用品+衣物', Object.values(OTHER_MONTHLY).reduce((s: number, v: any) => s + v.base, 0)],
  ];
  for (const [name, base] of living_items) {
    const amt = base * cf * lf * months;
    add('四、成年工作期', `${name}（累计${work_years}年）`, amt, `月约 ${group(base * cf * lf)} 元 ×12 ×${work_years}年`);
  }

  // ---------- 阶段5：养老（退休~死亡） ----------
  const years = LIFE_EXPECTANCY - retireAge;
  const pension = RETIREMENT.pension_monthly[tier] * 12 * years;
  const care_table = RETIREMENT.care_monthly[CARE_MODE_MAP[careMode]];
  const care = care_table[tier] * 12 * years;
  let medical_old = 0;
  for (const item of ADULT_ANNUAL) {
    if (item.key.includes('医疗')) {
      medical_old = (item.base_old ?? item.base) * cf * years;
      break;
    }
  }
  add('五、养老期', `养老金收入（${years}年）`, -pension, `企业职工养老金月约${group(RETIREMENT.pension_monthly[tier])}元，作为退休后收入。`, true);
  add('五、养老期', `${careMode}支出（${years}年）`, care, `月约${group(care_table[tier])}元 ×12 ×${years}年`);
  add('五、养老期', `老年医疗保健（${years}年）`, medical_old, '老年慢性病支出显著高于均值');

  // ---------- 阶段6：丧葬 ----------
  const funeral = FUNERAL[tier];
  add('六、丧葬', '殡葬（含墓地）', funeral, FUNERAL.note);

  // ---------- 汇总 ----------
  const gross_cost = rows.filter((r) => !r.is_income).reduce((s, r) => s + r.amount, 0);
  const pension_offset = rows.filter((r) => r.is_income).reduce((s, r) => s + -r.amount, 0);
  const grand_total = gross_cost - pension_offset;

  let education_total = 0;
  const other_subtotals: Record<string, number> = {};
  for (const r of rows) {
    if (r.is_income) continue;
    const st = r.stage;
    if (st.startsWith('二、')) education_total += r.amount;
    else other_subtotals[st] = (other_subtotals[st] ?? 0) + r.amount;
  }

  const ordered: [string, number][] = [
    ['一、孕育与生育', other_subtotals['一、孕育与生育'] ?? 0],
    ['二、0-22岁养育（含教育）', education_total],
    ['三、结婚（彩礼+婚礼+婚房首付）', other_subtotals['三、结婚'] ?? 0],
    ['四、成年工作期（生存+社保+个税+医疗）', other_subtotals['四、成年工作期'] ?? 0],
    ['五、养老期（养老+老年医疗）', other_subtotals['五、养老期'] ?? 0],
    ['六、丧葬', other_subtotals['六、丧葬'] ?? 0],
  ];
  const stage_subtotals = ordered.map(([name, amt]) => {
    const pct = gross_cost ? (amt / gross_cost) * 100 : 0;
    return { stage: name, amount: Math.round(amt), pct: Math.round(pct * 10) / 10 };
  });

  let edu_desc = `大学${uniType}`;
  if (graduate) edu_desc += ' + 硕士（22-23岁）';
  const assumptions = [
    `城市成本系数：${tier} = ${pyFloatStr(cf)}（以三线/全国城镇平均=1.0）`,
    `养育档位系数：${level} = ${pyFloatStr(rf)}（普惠=1.0）`,
    `分娩方式：${birthMode}`,
    `教育：${edu_desc}`,
    `购房方式：${purchaseMode}（${purchaseMode === '贷款' ? '首付20%，月供另计' : '全款总价'}）`,
    `养老方式：${careMode}，${retireAge}岁退休、预期寿命${LIFE_EXPECTANCY}岁（养老${years}年）`,
    `工作年限：${work_start}~${retireAge}岁，共${work_years}年`,
    '养老金按企业职工中位数估算（机关事业更高、城乡居民更低），作为退休后收入，已从净成本中抵减。',
    '未成年阶段成本含食宿日用+教育；工作期含独立生活的吃住行用+社保+个税+医疗。',
    '未计入失业、大病、意外、通货膨胀等风险与时间价值。',
    '所有数字为公开调研的中值估算，个体实际可能差异很大，仅供了解量级。',
  ];

  return {
    rows,
    stage_subtotals,
    grand_total: Math.round(grand_total),
    gross_cost: Math.round(gross_cost),
    pension_offset: Math.round(pension_offset),
    assumptions,
  };
}
