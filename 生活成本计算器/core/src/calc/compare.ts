// calc/compare.ts —— 城市加减法（calc_engine.py:679-738）
// 两次 compute_current_situation 对比 + diff + 富文本段。依赖都已就绪。
import { estimateTargetWage } from './family';
import { computeCurrentSituation } from './situation';
import { moneyFmt } from './money';
import { group } from '../fmt';
import type { SituationResult } from '../types';

export function compareCities(
  wage: number,
  currentTier: string,
  targetTier: string,
  insuranceMode: string = '在职（单位缴）',
  housing: string = '合租单间',
  foodLevel: string = '普通',
  hasCar: boolean = false,
  numChildren: number = 0,
  childrenByAge: Record<string, number> | null = null,
  supportElderly: boolean = false,
  supportFamilyMonthly: number = 0,
): {
  current: SituationResult;
  target: SituationResult;
  estimated_wage: number;
  income_diff: number;
  cost_diff: number;
  surplus_diff: number;
  comparison_text: string;
  rich: any[];
} {
  const estimated_wage = estimateTargetWage(wage, currentTier, targetTier);

  const common = {
    housing,
    foodLevel,
    hasCar,
    insuranceMode,
    numChildren,
    childrenByAge,
    supportElderly,
    supportFamilyMonthly,
  };
  const current = computeCurrentSituation({ age: 30, wagePretax: wage, tier: currentTier, ...common });
  const target = computeCurrentSituation({ age: 30, wagePretax: estimated_wage, tier: targetTier, ...common });

  const income_diff = target.income_net - current.income_net;
  const cost_diff = target.cost_total - current.cost_total;
  const surplus_diff = target.surplus - current.surplus;

  const lines: string[] = [`▶ 对比【${currentTier}】vs【${targetTier}】：`];
  if (surplus_diff > 0) {
    const income_word =
      income_diff < 0 ? `收入少了 ${group(Math.abs(income_diff))} 元` : `收入多了 ${group(income_diff)} 元`;
    const cost_word =
      cost_diff < 0 ? `生活成本低了 ${group(Math.abs(cost_diff))} 元` : `生活成本高了 ${group(cost_diff)} 元`;
    lines.push(`移到【${targetTier}】后，虽然${income_word}，但${cost_word}，`);
    lines.push(`每月结余反而增加 ${group(surplus_diff)} 元 ✅`);
  } else if (surplus_diff === 0) {
    lines.push(`移到【${targetTier}】后，收支基本不变。`);
  } else {
    lines.push(`⚠️ 移到【${targetTier}】后结余会减少 ${group(-surplus_diff)} 元，当前【${currentTier}】更优。`);
    if (income_diff < 0 && cost_diff > 0) lines.push('（收入下降的同时生活成本反而上升，不建议搬迁。）');
    else if (income_diff < 0) lines.push('（主要原因是收入下降幅度超过生活成本降低。）');
  }

  const rich: any[] = [{ t: `对比【${currentTier}】vs【${targetTier}】\n`, tag: 'h' }];
  if (surplus_diff > 0) {
    const inc = income_diff < 0 ? `少了 ${moneyFmt(Math.abs(income_diff))}` : `多了 ${moneyFmt(income_diff)}`;
    const cst = cost_diff < 0 ? `低了 ${moneyFmt(Math.abs(cost_diff))}` : `高了 ${moneyFmt(cost_diff)}`;
    rich.push({ t: `移到【${targetTier}】每月结余增加 ${moneyFmt(surplus_diff)} ✅\n`, tag: 'big' });
    rich.push({ t: `（收入${inc}，生活成本${cst}）\n`, tag: 'muted' });
  } else if (surplus_diff === 0) {
    rich.push({ t: `移到【${targetTier}】收支基本不变\n`, tag: 'normal' });
  } else {
    rich.push({ t: `移到【${targetTier}】每月结余减少 ${moneyFmt(-surplus_diff)} ⚠\n`, tag: 'bigbad' });
    rich.push({ t: '（当前城市更优）\n', tag: 'muted' });
  }
  rich.push({ t: `\n预设目标城市工资：按比例估算约 ${moneyFmt(estimated_wage)}/月`, tag: 'normal' });

  return {
    current,
    target,
    estimated_wage: Math.round(estimated_wage),
    income_diff: Math.round(income_diff),
    cost_diff: Math.round(cost_diff),
    surplus_diff: Math.round(surplus_diff),
    comparison_text: lines.join('\n'),
    rich,
  };
}
