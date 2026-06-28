// calc/tax.ts —— 个税优化（年终奖计税对比 + 专项扣除提示）（calc_engine.py:2199-2268）
import { calcAnnualIncomeTax, bonusMonthlyRate } from '../data/cost';
import { group, pct0 } from '../fmt';

/** bonus_tax_compare (2199)：年终奖单独计税 vs 合并计税对比，给省税建议。 */
export function bonusTaxCompare(
  annualSalary: number,
  bonus: number,
  annualSpecial: number = 0,
  annualSocial: number = 0,
): any {
  if (bonus <= 0) return { error: '年终奖金额需大于 0。' };

  const base_taxable = Math.max(0, annualSalary - 60000 - annualSocial - annualSpecial);
  const [base_tax] = calcAnnualIncomeTax(base_taxable);

  // 单独计税：奖金÷12 找月度税率
  const monthly_eq = bonus / 12;
  const [sep_rate, sep_quick] = bonusMonthlyRate(monthly_eq);
  const separate_tax = Math.max(0, bonus * sep_rate - sep_quick);

  // 合并计税：奖金并入综合所得
  const combined_taxable = base_taxable + bonus;
  const [combined_total_tax] = calcAnnualIncomeTax(combined_taxable);
  const combined_tax = combined_total_tax - base_tax;

  const saving = separate_tax - combined_tax; // 正=合并更省
  let recommend: string;
  if (saving > 0) recommend = '并入综合所得（合并计税）更省';
  else if (saving < 0) recommend = '单独计税更省';
  else recommend = '两种计税一样';

  const note =
    `假设年工资 ${group(annualSalary)}、年终奖 ${group(bonus)}、` +
    `年专项扣除 ${group(annualSpecial)}、年社保 ${group(annualSocial)}：\n` +
    `· 单独计税：奖金÷12=${group(monthly_eq)} 对应税率 ${pct0(sep_rate)}，年终奖纳税 ${group(separate_tax)}。\n` +
    `· 合并计税：奖金并入年薪，全年综合所得纳税 ${group(combined_total_tax)}（其中奖金部分约 ${group(combined_tax)}）。\n` +
    `→ ${recommend}约 ${group(Math.abs(saving))} 元。` +
    '\n⚠️ 年终奖单独计税优惠目前执行到 2027 年底，之后是否延续以当年政策为准；最终以个税 APP 年度汇算为准，或用「问 AI」结合最新政策确认。';

  return { separate_tax, combined_tax, combined_total_tax, base_tax, saving, recommend, note };
}

/** special_deduction_hints (2245)：按用户情况提示可用/可能漏报的专项附加扣除（每条一句）。 */
export function specialDeductionHints(
  hasChildren: number = 0,
  supportElderly: boolean = false,
  hasLoan: boolean = false,
  continuingEdu: boolean = false,
): string[] {
  const hints: string[] = [];
  if (hasChildren) {
    hints.push(
      `子女教育：每个孩子 2000 元/月（你有 ${hasChildren} 个 = ${hasChildren * 2000} 元/月），孩子满 3 岁起就能申报，别漏。`,
    );
    hints.push('3 岁以下婴幼儿照护：每个 2000 元/月（孩子没满 3 岁的走这项，别和子女教育混）。');
  } else {
    hints.push('子女教育 / 婴幼儿照护：有孩子的话每孩 2000 元/月，很多人没申报。');
  }
  if (supportElderly) {
    hints.push('赡养老人：独生子女 3000 元/月、非独生按分摊（每人≤1500）。父母满 60 岁即可。');
  } else {
    hints.push('赡养老人：父母任一方满 60 岁就能扣（独生 3000 元/月），达标了别忘报。');
  }
  if (hasLoan) {
    hints.push('住房贷款利息：首套 1000 元/月（最长 240 个月）。和住房租金二选一，不能同扣。');
  } else {
    hints.push('住房租金：按城市 800~1500 元/月（和房贷利息二选一）。租房的别漏。');
  }
  if (continuingEdu) {
    hints.push('继续教育：学历教育 400 元/月（最长 48 个月），职业资格证书取得当年扣 3600 元。');
  } else {
    hints.push('继续教育：在考证/在读学历的话，可扣 400 元/月 或 取证当年 3600 元。');
  }
  hints.push('大病医疗：年度医保目录内自付超 1.5 万的部分，最高扣 8 万/年（汇算时申报，留好票据）。');
  return hints;
}
