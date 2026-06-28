// calc/interpretation.ts —— _build_interpretation (calc_engine.py:461-545)
// 生成处境白话解读长文本（纯字符串拼接，逐分支对照）。survival_baseline 由调用方传入。
import { group, signGroup, fix0, fix1 } from '../fmt';
import { cityFactor } from '../data/cost';
import { normalizeChildrenByAge } from './normalizeChildren';
import costRaw from '../data/cost.json';

const C = costRaw as unknown as Record<string, any>;
const HOUSE_PURCHASE = C.HOUSE_PURCHASE;
const CHILD_CARE_MONTHLY_BASE = C.CHILD_CARE_MONTHLY_BASE;
const MIN_WAGE = C.MIN_WAGE;
const TYPICAL_WAGE = C.TYPICAL_WAGE;
const HOUSING = C.HOUSING;

/** 17 参数 → options 对象（与 Python 位置参数一一对应） */
export interface InterpretationInput {
  age: number;
  wage: number;
  tier: string;
  costTotal: number;
  socialIns: number;
  tax: number;
  incomeNet: number;
  surplus: number;
  surplusRate: number;
  houseSavingYears: number | null;
  survivalBaseline: number;
  specialDetail: string[];
  numChildren: number;
  foodLevel: string;
  insuranceMode: string;
  childrenByAge: Record<string, number> | null;
  supportFamilyMonthly?: number;
}

export function buildSituationInterpretation(o: InterpretationInput): string {
  const {
    age, wage, tier, costTotal, socialIns, tax, incomeNet, surplus, surplusRate,
    houseSavingYears, survivalBaseline, specialDetail, numChildren, foodLevel,
    insuranceMode, childrenByAge, supportFamilyMonthly = 0,
  } = o;

  const cf = cityFactor(tier);
  const lines: string[] = [];

  lines.push(`你 ${age} 岁，在【${tier}】城市，税前月薪 ${group(wage)} 元。`);
  lines.push(`扣除五险一金 ${group(socialIns)} 元、个税 ${group(tax)} 元后，每月到手约 ${group(incomeNet)} 元。`);
  if (specialDetail.length) {
    lines.push('（个税已扣除专项附加：' + specialDetail.join('；') + '）');
  }

  // 不缴社保的风险警告
  if (insuranceMode === '不缴社保') {
    lines.push('');
    lines.push('⚠️ 你选择了【不缴社保】：眼下每月到手看似多了，但这意味着');
    lines.push('   你未来【没有养老金、看病不能医保报销】，生病和养老的全部费用都要自担。');
    lines.push('   一次大病就可能耗尽多年积蓄，请务必重视这个隐患。');
  }

  lines.push('');
  lines.push(
    `你的【基本生存成本】约 ${group(costTotal)} 元/月（含住房、${foodLevel}饮食、交通、通讯日用、社保${
      supportFamilyMonthly > 0 ? '、给老家生活费' : ''
    }）。`,
  );

  // 结余率分析
  lines.push('');
  lines.push(`👉 每月到手 ${group(incomeNet)} 元 - 生存成本 ${group(costTotal)} 元 = 结余 ${signGroup(surplus)} 元`);
  if (surplus >= 0) {
    const suffix =
      surplusRate >= 20 ? '（✅ 超过20%健康线）'
      : surplusRate >= 10 ? '（⚠️ 建议至少达20%以备急用）'
      : '（🔴 低于10%，抗风险能力极弱）';
    lines.push(`   结余率 ${fix0(surplusRate)}%${suffix}`);
  } else {
    lines.push(`   已入不敷出，每月缺口约 ${group(-surplus)} 元。`);
  }

  // 城市生存底线
  lines.push('');
  lines.push(`█ 城市生存底线`);
  lines.push(`   在【${tier}】如果极度节俭（合租+自己做饭+公交），每月最低约 ${group(survivalBaseline)} 元能活。`);
  if (surplus > 0 && survivalBaseline > 0) {
    const ratio = surplus / survivalBaseline;
    lines.push(
      `   你每月结余 ${group(surplus)} 元 ÷ 底线月开支 ${group(survivalBaseline)} 元 ≈ ${fix1(ratio)}：每攒下一个月的结余，够按底线生活标准撑约 ${fix1(ratio)} 个月。`,
    );
  }

  // 购房年限
  if (houseSavingYears !== null && houseSavingYears < 100) {
    const hp = HOUSE_PURCHASE[tier];
    lines.push('');
    lines.push(`█ 攒够婚房首付（${fix0(hp.downpayment / 10000)}万）需约 ${fix0(houseSavingYears)} 年。`);
    lines.push(`   如果月结余增加 500 元，可缩短至 ${fix0(hp.downpayment / ((surplus + 500) * 12))} 年。`);
  } else if (surplus > 0) {
    lines.push('');
    lines.push('█ 按当前结余，攒首付几乎不可能（需要>100年）。');
  }

  // 孩子抚养成本提示（按各年龄段分别累加）
  const kids = normalizeChildrenByAge(childrenByAge, numChildren);
  if (Object.keys(kids).length) {
    const totalKids = Object.values(kids).reduce((s, n) => s + n, 0);
    let childMonth = 0;
    for (const [seg, n] of Object.entries(kids)) {
      childMonth += (CHILD_CARE_MONTHLY_BASE[seg] ?? 1500) * cf * n;
    }
    const segDesc = Object.entries(kids).map(([seg, n]) => `${seg}${n}人`).join('、');
    lines.push('');
    lines.push(`█ 你有 ${totalKids} 个孩子（${segDesc}）：`);
    lines.push(`   孩子每月基本支出约 ${group(childMonth)} 元（不包含辅导班、兴趣班）。`);
    const realSurplus = surplus - childMonth;
    lines.push(
      `   扣掉孩子抚养后，你每月真实可支配约 ${signGroup(realSurplus)} 元${
        realSurplus >= 0 ? '（有结余）' : '（已入不敷出）'
      }。`,
    );
  }

  // 参考对比
  lines.push('');
  lines.push(`█ 参考对比`);
  lines.push(`   当地最低工资    ${group(MIN_WAGE[tier])} 元/月`);
  lines.push(`   城镇私营平均    ${group(TYPICAL_WAGE[tier])} 元/月`);
  lines.push(`   全市房租中位    ${group(HOUSING['合租单间'].base * cf * 1.5)} 元/月（合租估算）`);
  lines.push(
    `   你的到手收入    ${group(incomeNet)} 元/月${
      incomeNet > TYPICAL_WAGE[tier] ? '（高于平均 ✓）' : '（低于平均）'
    }`,
  );

  return lines.join('\n');
}
