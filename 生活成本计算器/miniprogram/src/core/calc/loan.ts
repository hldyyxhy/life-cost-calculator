// calc/loan.ts —— 借贷真实年化反算 + 还款方式对比 + 可承受负债（calc_engine.py:748-1002）
// 数值敏感：IRR 二分法、等额本息月供。返回 dict 键名保持蛇形以便对拍。
import { fix1, group } from '../fmt';

/** _solve_monthly_irr (748)：二分法解月 IRR，使 Σ monthly/(1+r)^t = principal。200次迭代。
 *  非正输入或总还款≤本金返回 0.0。封顶 100%/月。 */
export function solveMonthlyIrr(principal: number, monthlyPayment: number, periods: number): number {
  if (principal <= 0 || monthlyPayment <= 0 || periods <= 0) return 0.0;
  if (monthlyPayment * periods <= principal) return 0.0; // 无利息甚至负利息

  const npv = (r: number): number => {
    let s = 0.0;
    for (let t = 1; t <= periods; t++) {
      s += monthlyPayment / (1 + r) ** t;
    }
    return s - principal;
  };

  let lo = 0.0;
  let hi = 1.0; // 月 IRR 搜索区间 0~100%
  if (npv(hi) > 0) return hi; // 利息高得离谱，封顶
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2;
    if (npv(mid) > 0) lo = mid;
    else hi = mid;
  }
  return (lo + hi) / 2;
}

/** _annual_irr_from_monthly (774)：月 IRR → 真实年化 (1+m)^12 - 1 */
export function annualIrrFromMonthly(monthlyIrr: number): number {
  return (1 + monthlyIrr) ** 12 - 1;
}

/** _level_from_annual_irr (779)：真实年化 → [评级, 颜色]。阈值沿用借贷司法解释口径。 */
export function levelFromAnnualIrr(annualIrr: number): [string, string] {
  if (annualIrr >= 0.36) return ['极高', 'deficit'];
  if (annualIrr >= 0.24) return ['高利贷', 'deficit'];
  if (annualIrr >= 0.15) return ['偏高', 'warn'];
  return ['正常', 'surplus'];
}

/** _monthly_payment (850)：等额本息月供 M = P·r·(1+r)^n / ((1+r)^n − 1) */
export function monthlyPayment(principal: number, annualRate: number, months: number): number {
  const r = annualRate / 12;
  if (r === 0) return principal / months;
  return (principal * r * (1 + r) ** months) / ((1 + r) ** months - 1);
}

/** _remaining_principal (858)：等额本息贷 totalMonths、已还 paidMonths 后的剩余本金。 */
export function remainingPrincipal(principal: number, annualRate: number, totalMonths: number, paidMonths: number): number {
  if (paidMonths >= totalMonths) return 0.0;
  const r = annualRate / 12;
  if (r === 0) return (principal * (totalMonths - paidMonths)) / totalMonths;
  return (principal * ((1 + r) ** totalMonths - (1 + r) ** paidMonths)) / ((1 + r) ** totalMonths - 1);
}

/** compute_loan_apr (790)：反算借贷真实年化（IRR 口径）。返回 dict 或 {error}。 */
export function computeLoanApr(
  principal: number,
  monthlyPayment: number,
  periods: number,
): { monthly_irr: number; annual_irr: number; nominal_apr: number; total_payment: number; interest: number; interest_ratio: number; level: string; note: string } | { error: string } {
  if (principal <= 0 || monthlyPayment <= 0 || periods <= 0) {
    return { error: '借款本金、每月还款、期数都必须为正数。' };
  }
  const total = monthlyPayment * periods;
  if (total <= principal) {
    return { error: '总还款（月还×期数）≤ 本金，这不可能是贷款，请检查输入。' };
  }

  const monthly_irr = solveMonthlyIrr(principal, monthlyPayment, periods);
  const annual_irr = annualIrrFromMonthly(monthly_irr);
  const nominal_apr = monthly_irr * 12;
  const interest = total - principal;
  const interest_ratio = interest / principal;
  const [level] = levelFromAnnualIrr(annual_irr);

  let note: string;
  if (level === '极高') {
    note = `真实年化 ${fix1(annual_irr * 100)}%，超过 36% 红线。按司法解释，超过 36% 的利息约定无效，已还的超额部分可主张返还。`;
  } else if (level === '高利贷') {
    note = `真实年化 ${fix1(annual_irr * 100)}%，处于 24%~36% 区间。这部分利息法院不予保护，未还部分可以拒绝支付。`;
  } else if (level === '偏高') {
    note = `真实年化 ${fix1(annual_irr * 100)}%，超过民间借贷利率上限（LPR 的 4 倍，约 14%~15%）。不算高利贷，但成本明显偏高。`;
  } else {
    note = `真实年化 ${fix1(annual_irr * 100)}%，处于正常区间。`;
  }

  return { monthly_irr, annual_irr, nominal_apr, total_payment: total, interest, interest_ratio, level, note };
}

/** compare_loan_methods (869)：等额本息 vs 等本等息对比（揭穿分期陷阱）。 */
export function compareLoanMethods(
  principal: number,
  nominalApr: number,
  periods: number,
): { equal_payment: any; equal_principal_flat: any; nominal_apr: number; interest_diff: number; note: string } | { error: string } {
  if (principal <= 0) return { error: '借款本金必须为正数。' };
  if (periods <= 0) return { error: '期数必须为正数。' };
  if (nominalApr < 0) return { error: '名义年化不能为负数。' };

  const r = nominalApr / 12;
  const n = periods;

  // 等额本息：月供恒定
  const ep_monthly = monthlyPayment(principal, nominalApr, n);
  const ep_total = ep_monthly * n;
  const ep_interest = ep_total - principal;
  const ep_irr = annualIrrFromMonthly(solveMonthlyIrr(principal, ep_monthly, n));

  // 等本等息（固定手续费制）：每月本金=P/n，每月手续费=P*r（固定不递减）
  const epf_fee_monthly = principal * r;
  const epf_monthly = principal / n + epf_fee_monthly;
  const epf_total = epf_monthly * n;
  const epf_interest = epf_total - principal; // = P*r*n
  const epf_irr = annualIrrFromMonthly(solveMonthlyIrr(principal, epf_monthly, n));

  const interest_diff = epf_interest - ep_interest;
  const [level_epf] = levelFromAnnualIrr(epf_irr);

  let note: string;
  if (nominalApr === 0) {
    note = '名义年化 0%，两种方式都无利息。但务必确认没有「服务费/手续费/担保费」——很多无息分期正是靠这些隐形收费赚钱。';
  } else {
    const parts = [
      `机构报价的名义年化 ${fix1(nominalApr * 100)}%，但等本等息（消费分期/信用卡分期常用）的真实年化高达 ${fix1(epf_irr * 100)}%，是名义的 ${fix1(epf_irr / nominalApr)} 倍。`,
      '原因：等本等息的手续费按初始本金固定收，你越还本金越少、实际占用的钱越少，利息却不降——所谓「月费率0.7%」折成真实年化不是 8.4%，而是约 15%+。',
      `等额本息（银行房贷口径）真实年化约 ${fix1(ep_irr * 100)}%，更接近名义。同一笔本金、同一期数，等本等息比等额本息多付利息 ${group(interest_diff)} 元。`,
    ];
    if (level_epf === '极高' || level_epf === '高利贷') {
      parts.push('⚠️ 等本等息真实年化越过 24%/36% 红线：24%~36% 区间法院不予保护，超 36% 部分约定无效、可主张返还。');
    }
    note = parts.join('');
  }

  return {
    equal_payment: { monthly: ep_monthly, total_interest: ep_interest, total_payment: ep_total, annual_irr: ep_irr },
    equal_principal_flat: { monthly: epf_monthly, monthly_fee: epf_fee_monthly, total_interest: epf_interest, total_payment: epf_total, annual_irr: epf_irr },
    nominal_apr: nominalApr,
    interest_diff,
    note,
  };
}

/** compute_affordable_debt (947)：按月结余反算可承受负债上限（等额本息口径）。 */
export function computeAffordableDebt(
  monthlySurplus: number,
  nominalApr: number,
  periods: number,
  income: number | null = null,
): { max_monthly: number; max_principal: number; safe_principal: number; ratio_used: number; monthly_surplus: number; note: string } | { error: string } {
  if (monthlySurplus <= 0) {
    return { error: '你目前月结余 ≤ 0（入不敷出），暂时不具备新增负债的能力。建议先把收入提上去、或削减一些非必要开支，等情况好转再考虑借钱。' };
  }
  if (nominalApr < 0) return { error: '名义年化不能为负数。' };
  if (periods <= 0) return { error: '期数必须为正数。' };

  let cap = monthlySurplus * 0.5; // 50% 档（激进）
  if (income !== null && income > 0) cap = Math.min(cap, income * 0.5);
  const safe_cap = cap * 0.6; // 30% 档（保守）

  const r = nominalApr / 12;
  const n = periods;

  // 月供反推本金（_monthly_payment 的代数逆）
  const principalFromMonthly = (m: number): number => {
    if (r === 0) return m * n;
    return (m * ((1 + r) ** n - 1)) / (r * (1 + r) ** n);
  };

  const max_principal = principalFromMonthly(cap);
  const safe_principal = principalFromMonthly(safe_cap);

  const note =
    `按经验线，月还款别超过你能自由支配的钱（月结余）的一半，也就是每月最多还 ${group(cap)} 元。` +
    `按名义年化 ${fix1(nominalApr * 100)}%、${n} 期等额本息反推，你能承受的借款本金上限约 ${group(max_principal)} 元（50%档），更稳一点按 30% 档约 ${group(safe_principal)} 元。\n` +
    `注意：这是按等额本息算的。若你借的是消费分期（等本等息），同样月供能借的本金更少，因为它的真实利息更贵（见「还款方式对比」）。\n` +
    `⚠️「先借了再说」是绝大多数债务雪崩的起点：一旦收入波动或生病变失业，月还款就成了压垮你的最后一根稻草。`;

  return { max_monthly: cap, max_principal, safe_principal, ratio_used: 0.5, monthly_surplus: monthlySurplus, note };
}
