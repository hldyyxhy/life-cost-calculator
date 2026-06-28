// calc/housing.ts —— 住房决策（买vs租/公积金额度/利率压力测试）（calc_engine.py:1987-2135）
// 依赖 loan.ts 的 monthlyPayment/remainingPrincipal + money.ts 的 moneyFmt。
import { moneyFmt } from './money';
import { monthlyPayment, remainingPrincipal } from './loan';
import { cityFactor } from '../data/cost';
import { group, pct0, pct2 } from '../fmt';
import costRaw from '../data/cost.json';

const C = costRaw as unknown as Record<string, any>;
const TIER_PROFILE = C.TIER_PROFILE;
const HOUSING_FUND = C.HOUSING_FUND;
const HOUSING = C.HOUSING;

/** compare_buy_rent (1987)：买 vs 租 N 年成本（房价不变中性估算，买房代价≈利息）。 */
export function compareBuyRent(
  tier: string,
  years: number = 10,
  houseArea: number = 90,
  downRatio: number = 0.3,
  commercialRate: number | null = null,
  fundRate: number | null = null,
  rentMonthly: number | null = null,
  loanYears: number = 30,
): any {
  const prof = TIER_PROFILE[tier] ?? TIER_PROFILE['三线'];
  const cf = cityFactor(tier);
  const house_price = prof.house_price * houseArea;
  const downpay = house_price * downRatio;
  const loan = house_price - downpay;
  const cr = commercialRate !== null ? commercialRate : HOUSING_FUND.commercial_rate;
  const fr = fundRate !== null ? fundRate : HOUSING_FUND.first_rate;
  const fund_max = HOUSING_FUND.max_loan[tier] ?? 400000;
  const fund_part = Math.min(loan, fund_max); // 组合贷：公积金用满
  const comm_part = loan - fund_part;
  const loan_months = loanYears * 12;
  const live_months = years * 12;

  const m_fund = fund_part > 0 ? monthlyPayment(fund_part, fr, loan_months) : 0;
  const m_comm = comm_part > 0 ? monthlyPayment(comm_part, cr, loan_months) : 0;
  const monthly = m_fund + m_comm;
  const total_paid = downpay + monthly * live_months; // N 年现金流出
  const rem_fund = fund_part > 0 ? remainingPrincipal(fund_part, fr, loan_months, live_months) : 0;
  const rem_comm = comm_part > 0 ? remainingPrincipal(comm_part, cr, loan_months, live_months) : 0;
  const remaining = rem_fund + rem_comm;
  const paid_principal = loan - remaining;
  const interest_paid = monthly * live_months - paid_principal; // N 年还的利息 = 买房净成本
  const buy_net = interest_paid;

  const rent_monthly = rentMonthly !== null ? rentMonthly : HOUSING['一居室整租'].base * cf;
  const rent_total = rent_monthly * 12 * years;
  const rent_net = rent_total;
  const diff = buy_net - rent_net;

  const note =
    `【买】${houseArea}㎡ 总价约 ${group(house_price)}，首付 ${group(downpay)}（${pct0(downRatio)}），` +
    `贷款 ${group(loan)}（${loanYears} 年，公积金 ${group(fund_part)}@${pct2(fr)} + 商贷 ${group(comm_part)}@${pct2(cr)}），月供约 ${group(monthly)}。\n` +
    `   住 ${years} 年共还月供 ${group(monthly * live_months)}，其中利息约 ${group(interest_paid)}（本金通过房子按买时价收回，不预测房价涨跌，所以买房的代价 ≈ 利息）。\n` +
    `【租】${tier} 一居室月租约 ${group(rent_monthly)}，${years} 年共付租金 ${group(rent_total)}。\n` +
    `→ 房价不涨不跌时，${diff < 0 ? '买房（利息成本）更低' : '租房更低'}约 ${group(Math.abs(diff))} 元。` +
    '\n\n⚠️ 关键提醒：这是「房价不涨不跌」的中性估算。当前多数城市房价在跌（除一线城市核心），' +
    '若你买的房子跌了，买房还要额外亏掉跌幅——跌幅可能远超利息。务必用「问 AI」查你关注小区的真实行情再决定。';

  const concl =
    diff < 0
      ? { t: `房价不跌时 买房省 ${moneyFmt(Math.abs(diff))}\n`, tag: 'big' }
      : { t: `房价不跌时 租房省 ${moneyFmt(Math.abs(diff))}\n`, tag: 'bigbad' };
  const rich = [
    { t: `买房成本（买 vs 租 · ${years} 年）\n`, tag: 'h' },
    { t: `总价 ${moneyFmt(house_price)} · 首付 ${moneyFmt(downpay)} · 贷款 ${moneyFmt(loan)}\n`, tag: 'normal' },
    { t: `月供 ${moneyFmt(monthly)}/月\n`, tag: 'buy' },
    { t: `住 ${years} 年还利息 ≈ ${moneyFmt(interest_paid)}  ← 买房真代价\n`, tag: 'buy' },
    { t: '\n租房成本\n', tag: 'h' },
    { t: `月租 ${moneyFmt(rent_monthly)}/月\n`, tag: 'rent' },
    { t: `${years} 年租金 ≈ ${moneyFmt(rent_total)}\n`, tag: 'rent' },
    { t: '\n', tag: 'normal' },
    concl,
    { t: '（房价若跌，买房还要额外亏掉跌幅）\n', tag: 'muted' },
    { t: '\n⚠ 当前房价波动剧烈，以上为粗算估算（未含税费/维修/空置），点「问 AI」结合最新行情再判断。', tag: 'warn' },
  ];

  return {
    tier, years, house_price, downpay, loan, monthly, buy_total_paid: total_paid,
    interest_paid, remaining, residual: house_price, buy_net, rent_monthly, rent_total,
    rent_net, diff, note, rich,
  };
}

/** housing_fund_loan (2067)：公积金可贷额度（三重取小）+ 月供。 */
export function housingFundLoan(tier: string, balance: number = 0, monthlyContribution: number = 0, years: number = 30): any {
  const fund = HOUSING_FUND;
  const max_by_tier = fund.max_loan[tier] ?? 400000;
  const by_balance = balance * fund.balance_multiplier;
  const by_contribution = monthlyContribution > 0 ? monthlyContribution * 12 * years * 0.45 : null;
  const limits = [max_by_tier, by_balance];
  if (by_contribution !== null) limits.push(by_contribution);
  const eligible = Math.max(0, Math.min(...limits));
  const rate = fund.first_rate;
  const months = years * 12;
  const monthly = eligible > 0 ? monthlyPayment(eligible, rate, months) : 0;
  const total_interest = eligible > 0 ? monthly * months - eligible : 0;

  const note =
    `公积金可贷额 = min(当地上限 ${group(max_by_tier)}，余额 ${group(balance)}×${fund.balance_multiplier} = ${group(by_balance)}` +
    (by_contribution !== null ? `，月缴存 ${monthlyContribution}×12×${years}×0.45 = ${group(by_contribution)}` : '') +
    `) = ${group(eligible)} 元。\n` +
    `按首套利率 ${pct2(rate)}、${years} 年等额本息：月供约 ${group(monthly)}，总利息约 ${group(total_interest)}。` +
    '\n⚠️ 各地公积金政策差异大（上限/倍数/缴存要求不同），以上是估算。用「问 AI」查你所在城市的最新公积金贷款政策更准。';

  const rich = [
    { t: '公积金可贷额度\n', tag: 'h' },
    { t: `可贷约 ${moneyFmt(eligible)}\n`, tag: 'big' },
    { t: `按首套利率 ${pct2(rate)}、${years} 年等额本息\n`, tag: 'normal' },
    { t: `月供约 ${moneyFmt(monthly)}/月 · 总利息约 ${moneyFmt(total_interest)}\n`, tag: 'buy' },
    { t: '\n⚠ 各地公积金政策差异大（上限/倍数/缴存要求不同），以上为估算，点「问 AI」查当地最新政策更准。', tag: 'warn' },
  ];

  return { tier, eligible, rate, years, monthly, total_interest, max_by_tier, by_balance, by_contribution, note, rich };
}

/** rate_stress_test (2106)：利率压力测试（基准/+0.5%/+1% 月供对比）。 */
export function rateStressTest(principal: number, baseRate: number = 0.0345, years: number = 30): any {
  const months = years * 12;
  const rows: { rate: number; monthly: number; total_interest: number }[] = [];
  for (const delta of [0, 0.005, 0.01]) {
    const rate = baseRate + delta;
    const m = monthlyPayment(principal, rate, months);
    rows.push({ rate, monthly: m, total_interest: m * months - principal });
  }
  const base_m = rows[0].monthly;

  const note =
    `贷款 ${group(principal)}、${years} 年等额本息：\n` +
    `· 利率 ${pct2(baseRate)}：月供 ${group(rows[0].monthly)}，总利息 ${group(rows[0].total_interest)}\n` +
    `· 利率 ${pct2(baseRate + 0.005)}（+0.5%）：月供 ${group(rows[1].monthly)}\n` +
    `· 利率 ${pct2(baseRate + 0.01)}（+1%）：月供 ${group(rows[2].monthly)}\n` +
    `→ 利率每涨 1%，月供多约 ${group(rows[2].monthly - base_m)} 元，${years} 年多付利息 ${group(rows[2].total_interest - rows[0].total_interest)} 元。` +
    '\n⚠️ 实际利率以你签贷款时的 LPR + 加点为准，会随央行调整变动。';

  const rich = [
    { t: `利率压力测试（贷 ${moneyFmt(principal)} / ${years} 年）\n`, tag: 'h' },
    { t: `· 利率 ${pct2(baseRate)}：月供 ${moneyFmt(rows[0].monthly)}\n`, tag: 'normal' },
    { t: `· 利率 ${pct2(baseRate + 0.005)}（+0.5%）：月供 ${moneyFmt(rows[1].monthly)}\n`, tag: 'normal' },
    { t: `· 利率 ${pct2(baseRate + 0.01)}（+1%）：月供 ${moneyFmt(rows[2].monthly)}\n`, tag: 'buy' },
    { t: '\n', tag: 'normal' },
    { t: `利率每涨 1%，月供多约 ${moneyFmt(rows[2].monthly - base_m)}，${years} 年多付利息 ${moneyFmt(rows[2].total_interest - rows[0].total_interest)}\n`, tag: 'bigbad' },
    { t: '\n⚠ 实际利率以签贷款时的 LPR + 加点为准，会随央行调整变动。', tag: 'warn' },
  ];

  return { principal, base_rate: baseRate, years, rows, note, rich };
}
