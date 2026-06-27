// calc/debt.ts —— 多笔债还清模拟 + 以贷养贷螺旋（calc_engine.py:1005-1231）
// 数值敏感：月度迭代、0.005 容差、free_pool 滚动、pickTarget 复合键。
import { fix0, fix1, group, pct0 } from '../fmt';

/** simulate_debt_payoff (1005)：雪球法 / 雪崩法多笔债还清模拟。 */
export function simulateDebtPayoff(
  debts: any[],
  method: string = 'avalanche',
  extraMonthly: number = 0,
): any {
  if (!debts || debts.length === 0) return { error: '请至少输入一笔债。' };

  // 解析 + 校验
  const parsed: { name: string; balance: number; annual_rate: number; min_monthly: number }[] = [];
  for (let i = 0; i < debts.length; i++) {
    const d = debts[i];
    const bal = parseFloat(d.balance);
    const rate = parseFloat(d.annual_rate);
    const mn = parseFloat(d.min_monthly);
    if (isNaN(bal) || isNaN(rate) || isNaN(mn)) {
      return { error: `第 ${i + 1} 笔债的输入有误（金额/年化/月还必须是数字）。` };
    }
    if (bal <= 0) return { error: `第 ${i + 1} 笔债的余额必须为正数。` };
    if (rate < 0) return { error: `第 ${i + 1} 笔债的年化不能为负。` };
    if (mn <= 0) return { error: `第 ${i + 1} 笔债的最低月还款必须为正数。` };
    parsed.push({ name: String(d.name || `债${i + 1}`), balance: bal, annual_rate: rate, min_monthly: mn });
  }

  // 失控预检：某笔最低还款 ≤ 当月利息 → 永远还不清
  for (const d of parsed) {
    const monthly_interest = (d.balance * d.annual_rate) / 12;
    if (d.min_monthly <= monthly_interest) {
      const need = monthly_interest + 1;
      return {
        method,
        unpayable: true,
        unpayable_reason:
          `「${d.name}」按当前最低月还款 ${fix0(d.min_monthly)} 元永远还不清：` +
          `它每月新增利息就有 ${fix0(monthly_interest)} 元（年化 ${fix0(d.annual_rate * 100)}%），` +
          `最低还款连利息都盖不住，本金只会越滚越多。要压住这笔，每月至少得还 ${fix0(need)} 元。\n` +
          `这是信用卡最低还款（通常只有账单的 10% 左右）的真实陷阱——你以为在还钱，其实大部分在还利息、本金纹丝不动。`,
        note: '',
        payoff_order: [],
        total_months: null,
        total_payment: 0,
        total_interest: 0,
        monthly_snapshots: [],
      };
    }
  }

  const rates: Record<string, number> = {};
  const mins: Record<string, number> = {};
  let balances: Record<string, number> = {};
  for (const d of parsed) {
    rates[d.name] = d.annual_rate;
    mins[d.name] = d.min_monthly;
    balances[d.name] = d.balance;
  }

  let total_interest = 0.0;
  let total_payment = 0.0;
  const payoff_order: { name: string; payoff_month: number }[] = [];
  const snapshots: any[] = [];
  let month = 0;

  // pickTarget：snowball 取 (balance,-rate) 最小；avalanche 取 (rate,-balance) 最大。
  // 并列时保留遍历顺序第一个（与 Python min/max 一致）。
  const pickTarget = (bals: Record<string, number>): string => {
    const names = Object.keys(bals);
    let best = names[0];
    for (const nm of names) {
      if (method === 'snowball') {
        const d = bals[nm] - bals[best];
        if (d < 0 || (d === 0 && rates[nm] > rates[best])) best = nm;
      } else {
        const d = rates[nm] - rates[best];
        if (d > 0 || (d === 0 && bals[nm] < bals[best])) best = nm;
      }
    }
    return best;
  };

  while (Object.keys(balances).length > 0 && month < 1200) {
    month += 1;
    const balances_prev = { ...balances }; // 月初（=上月末）

    // 1) 计息
    const interest: Record<string, number> = {};
    for (const nm of Object.keys(balances)) {
      interest[nm] = (balances[nm] * rates[nm]) / 12;
      total_interest += interest[nm];
    }

    // 2) 每笔先付最低还款（不超过本息合计）
    let free_pool = extraMonthly;
    const new_balances: Record<string, number> = {};
    for (const nm of Object.keys(balances)) {
      const owed = balances[nm] + interest[nm];
      const pay_min = Math.min(mins[nm], owed);
      total_payment += pay_min;
      const remaining = owed - pay_min;
      if (remaining <= 0.005) {
        payoff_order.push({ name: nm, payoff_month: month });
        free_pool += mins[nm] - owed; // 本笔最低额的富余滚入自由池
      } else {
        new_balances[nm] = remaining;
      }
    }
    balances = new_balances;

    // 3) 自由池集中砸向目标债，结清则顺延下一个
    let main_target: string | null = null;
    while (free_pool > 0.005 && Object.keys(balances).length > 0) {
      const target = pickTarget(balances);
      if (main_target === null) main_target = target;
      const owed = balances[target];
      const pay = Math.min(free_pool, owed);
      total_payment += pay;
      free_pool -= pay;
      if (owed - pay <= 0.005) {
        payoff_order.push({ name: target, payoff_month: month });
        delete balances[target];
      } else {
        balances[target] = owed - pay;
      }
    }

    snapshots.push({ month, balances: balances_prev, target: main_target !== null ? main_target : '', extra: extraMonthly });
  }

  if (Object.keys(balances).length > 0) {
    return {
      method,
      unpayable: true,
      unpayable_reason: '模拟超过 100 年仍未还清，请检查输入（最低还款可能偏低）。',
      note: '',
      payoff_order,
      total_months: month,
      total_payment,
      total_interest,
      monthly_snapshots: snapshots,
    };
  }

  const method_cn = method === 'snowball' ? '雪球法' : '雪崩法';
  const action =
    method === 'snowball'
      ? '余额最小的那笔（雪球法：先尝到结清的甜头，靠成就感撑下去）'
      : '利率最高的那笔（雪崩法：数学最优，总利息最少）';
  const note =
    `按「${method_cn}」：${month} 个月还清全部债务，总共付出 ${group(total_payment)} 元，其中利息 ${group(total_interest)} 元。\n` +
    `核心动作：每笔债只还最低还款（避免违约催收），把所有挤得出的余钱集中砸向${action}。`;

  return {
    method,
    payoff_order,
    total_months: month,
    total_payment,
    total_interest,
    monthly_snapshots: snapshots,
    unpayable: false,
    unpayable_reason: '',
    note,
  };
}

/** simulate_loan_spiral (1160)：以贷养贷/只还最低时的利滚利演示。 */
export function simulateLoanSpiral(
  initialBalance: number,
  annualRate: number,
  months: number,
  actualMonthlyPayment: number = 0,
): any {
  if (initialBalance <= 0) return { error: '初始债务必须为正数。' };
  if (annualRate <= 0) return { error: '年化必须为正数（演示利滚利才有意义）。' };
  if (months <= 0) return { error: '演示月数必须为正数。' };
  if (actualMonthlyPayment < 0) return { error: '每月实际还款不能为负。' };

  const r = annualRate / 12;
  let balance = initialBalance;
  const snapshots: { month: number; balance: number; interest_accrued: number }[] = [];
  let doubled = false;
  let doubling_month: number | null = null;

  for (let m = 1; m <= months; m++) {
    const interest = balance * r;
    balance = balance + interest - actualMonthlyPayment;
    if (balance < 0) balance = 0;
    snapshots.push({ month: m, balance, interest_accrued: interest });
    if (!doubled && balance >= initialBalance * 2) {
      doubled = true;
      doubling_month = m;
    }
  }

  const breakeven = initialBalance * r; // 每月至少还这么多才能压住利息
  const years_72 = 72 / (annualRate * 100); // 72 法则估算翻倍年数

  let trend: string;
  if (actualMonthlyPayment < breakeven) {
    trend =
      `每月实还 ${fix0(actualMonthlyPayment)} 元 < 每月新增利息 ${fix0(breakeven)} 元，` +
      `差额持续滚进本金——${months} 个月后债务从 ${group(initialBalance)} 涨到 ${group(balance)} 元。`;
  } else {
    trend =
      `每月实还 ${fix0(actualMonthlyPayment)} 元 ≥ 每月利息 ${fix0(breakeven)} 元，` +
      `债务在下降（${months} 个月后 ${group(balance)} 元）。保持这个力度就能逐步脱困。`;
  }

  let spiral_warn: string;
  if (doubled) {
    spiral_warn = `仅 ${doubling_month} 个月就翻倍（72 法则估算约 ${fix0(years_72)} 年翻倍）。`;
  } else if (actualMonthlyPayment < breakeven) {
    spiral_warn = `本期间未翻倍，但按 72 法则约 ${fix0(years_72)} 年会翻倍。`;
  } else {
    spiral_warn = '';
  }

  const note =
    `「借新还旧、只还最低、以贷养贷」是债务失控的标准路径：利息按复利指数增长，你还的钱不够覆盖利息，缺口就滚进本金再生利息。\n` +
    `${trend}\n${spiral_warn}\n` +
    `要止血，每月至少得还 ${fix0(breakeven)} 元（= 初始债务的月利息）才能让债务不再增长，之后再往上加码还本金。\n` +
    `⚠️ 若这笔债真实年化超 36%，超过部分约定无效、可主张返还（见「反算真实年化」）。`;

  return {
    final_balance: balance,
    doubled,
    doubling_month,
    monthly_snapshots: snapshots,
    breakeven_monthly: breakeven,
    note,
  };
}

/** assess_debt_health (2415)：债务健康评估（负债率/月供比/还清月数/风险等级）。 */
export function assessDebtHealth(totalDebt: number, monthlyIncome: number, monthlyPay: number, avgApr = 0.18): any {
  if (totalDebt <= 0) return { error: '总负债需大于 0。' };
  if (monthlyIncome <= 0) return { error: '月收入需大于 0。' };

  const annual_income = monthlyIncome * 12;
  const debt_ratio = totalDebt / annual_income; // 负债 / 年收入
  const pay_ratio = monthlyPay / monthlyIncome; // 月供 / 月收入
  const r = avgApr / 12;
  const monthly_interest = totalDebt * r;
  const runaway = monthlyPay <= monthly_interest; // 还款盖不住利息 = 失控

  let months: number | null = null;
  let level: string;
  let color: string;
  if (runaway) {
    level = '危险：还款盖不住利息，越还越多';
    color = 'deficit';
  } else {
    months = Math.ceil(-Math.log(1 - (totalDebt * r) / monthlyPay) / Math.log(1 + r));
    if (debt_ratio > 0.5 || pay_ratio > 0.5) {
      level = '危险（负债/月供占收入过高）';
      color = 'deficit';
    } else if (debt_ratio > 0.3 || pay_ratio > 0.3) {
      level = '警戒';
      color = 'accent';
    } else {
      level = '健康';
      color = 'surplus';
    }
  }

  const parts: string[] = [
    `负债收入比：${pct0(debt_ratio)}（总负债 ${group(totalDebt)} ÷ 年收入 ${group(annual_income)}）——${
      debt_ratio > 0.3 ? '偏高' : '可控'
    }（经验线：<30% 健康、30~50% 警戒、>50% 危险）。`,
    `月供占收入：${pct0(pay_ratio)}——${pay_ratio > 0.3 ? '吃紧' : '可承受'}（月还款最好不超月收入 30%，超 50% 一笔意外就断供）。`,
  ];
  if (runaway) {
    parts.push(
      `⚠️ 你每月还 ${group(monthlyPay)}，但月利息约 ${group(monthly_interest)}——还款盖不住利息，债务会越滚越多、永远还不清。必须增收或协商减免/债务重组。`,
    );
  } else if (months !== null) {
    parts.push(
      `按每月还 ${group(monthlyPay)}（年化 ${pct0(avgApr)}），约 ${months} 个月（${fix1(months / 12)} 年）还清，总利息约 ${group(
        monthlyPay * months - totalDebt,
      )} 元。`,
    );
  }
  parts.push('建议：优先还高息债（雪崩法）、必要时和债权方协商分期/减免、砍非必要开支、考虑债务重组；千万别以贷养贷。');

  return { debt_ratio, pay_ratio, months, runaway, monthly_interest, level, color, note: parts.join('\n') };
}
