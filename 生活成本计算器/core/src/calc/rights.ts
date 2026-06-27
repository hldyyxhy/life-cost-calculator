// calc/rights.ts —— 劳动权益（加班费/最低工资/维权评估）（calc_engine.py:1243-1428）
// 法定标准全国统一（不依赖各地数据）。常量 MONTH_WORK_DAYS_PAY/DAILY_HENTS 见文件内。
import { fix2, group, pct1 } from '../fmt';
import costRaw from '../data/cost.json';

const C = costRaw as unknown as Record<string, any>;
const MIN_WAGE = C.MIN_WAGE;
const TIER_KEYS = C.TIER_KEYS as string[];

// 月计薪天数（劳社部发[2008]3号）：(365-104)÷12 = 21.75；法定每日 8 小时
const MONTH_WORK_DAYS_PAY = 21.75;
const DAILY_HOURS = 8;

/** compute_overtime_pay (1243)：依法反算加班费（工作日1.5/休息日2/节假日3倍）。 */
export function computeOvertimePay(monthlyWage: number, weekdayOt = 0, weekendOt = 0, holidayOt = 0): any {
  if (monthlyWage <= 0) return { error: '月工资必须为正数。' };
  if (weekdayOt < 0 || weekendOt < 0 || holidayOt < 0) return { error: '加班小时不能为负。' };

  const hourly = monthlyWage / MONTH_WORK_DAYS_PAY / DAILY_HOURS; // 法定时薪
  const weekday_pay = hourly * 1.5 * weekdayOt;
  const weekend_pay = hourly * 2.0 * weekendOt;
  const holiday_pay = hourly * 3.0 * holidayOt;
  const total = weekday_pay + weekend_pay + holiday_pay;

  const detail: { type: string; hours: number; rate: number; pay: number }[] = [];
  if (weekdayOt > 0) detail.push({ type: '工作日延时', hours: weekdayOt, rate: 1.5, pay: weekday_pay });
  if (weekendOt > 0) detail.push({ type: '休息日', hours: weekendOt, rate: 2.0, pay: weekend_pay });
  if (holidayOt > 0) detail.push({ type: '法定节假日', hours: holidayOt, rate: 3.0, pay: holiday_pay });

  let note: string;
  if (total === 0) {
    note =
      `你的法定时薪约 ${fix2(hourly)} 元/小时（月工资 ÷ 21.75 天 ÷ 8 小时）。` +
      '还没填加班时长——把每月各类加班小时填上，就能算出依法应得的加班费。\n' +
      '提示：企业常以「包薪」「综合工时」或只给调休为由不给加班费，这不合法；只要你加了班且企业没依法付钱，差额就是被克扣的。';
  } else {
    note =
      `你的法定时薪约 ${fix2(hourly)} 元/小时，本月加班费依法应得约 ${group(total)} 元` +
      '（工作日1.5倍、休息日2倍、法定节假日3倍）——这是你应得的钱。\n' +
      '争取它需要花些时间、备好证据，在职期间也要考虑周全。下方「维权现实评估」会结合你的实际情况，帮你看看怎么处理对你最有利。';
  }

  return { hourly_wage: hourly, weekday_pay, weekend_pay, holiday_pay, total_overtime: total, detail, note };
}

/** compute_min_wage_check (1298)：对照当地最低工资标准。 */
export function computeMinWageCheck(monthlyWage: number, tier: string): any {
  if (monthlyWage <= 0) return { error: '月薪必须为正数。' };
  if (!(tier in MIN_WAGE)) {
    const tiersPy = `[${TIER_KEYS.map((t) => `'${t}'`).join(', ')}]`; // 模拟 Python str(list)
    return { error: `城市等级无效（应为 ${tiersPy} 之一）。` };
  }

  const min_wage = MIN_WAGE[tier];
  const below = monthlyWage < min_wage;
  const ratio = monthlyWage / min_wage;

  let note: string;
  if (below) {
    const gap = min_wage - monthlyWage;
    note =
      `你所在地区（${tier}城市）现行最低工资标准约 ${group(min_wage)} 元/月，` +
      `你的月薪 ${group(monthlyWage)} 元低于最低工资 ${group(gap)} 元，这是违法的——` +
      '即便试用期、学徒期，工资也不得低于当地最低工资。\n' +
      '维权：拨打 12333 或到当地劳动监察大队投诉，可要求补足差额。\n' +
      '（注：此处最低工资是按城市等级的概值，精确标准以当地人社局公布为准。）';
  } else if (ratio < 1.2) {
    note =
      `你所在地区（${tier}城市）最低工资约 ${group(min_wage)} 元/月，` +
      `你的月薪 ${group(monthlyWage)} 元刚好在最低工资线上方（是最低工资的 ${pct1(ratio)}），勉强合法，议价空间很小。`;
  } else {
    note =
      `你所在地区（${tier}城市）最低工资约 ${group(min_wage)} 元/月，` +
      `你的月薪 ${group(monthlyWage)} 元是最低工资的 ${pct1(ratio)}，高于最低线，合法。`;
  }

  return { min_wage, below, ratio, monthly_wage: monthlyWage, tier, note };
}

/** assess_overtime_claim (1346)：维权现实评估（胜算/成本/风险/分级建议）。不煽动，按实际利益最大化。 */
export function assessOvertimeClaim(owedAmount: number, employed = true, evidence = '部分'): any {
  if (owedAmount <= 0) return { error: '被欠金额必须为正数（若实际已拿到全部加班费，就没有被欠部分）。' };
  if (!['充分', '部分', '几乎没有'].includes(evidence)) {
    return { error: '证据情况应选：充分 / 部分 / 几乎没有。' };
  }

  const win_chance: Record<string, string> = {
    充分: '中高（证据是关键，齐全则胜算较大）',
    部分: '中等（部分证据可补强；企业若拿不出考勤反而对你有利）',
    几乎没有: '偏低（证据较少，先把证据备齐会更稳妥）',
  };
  const winChance = win_chance[evidence];

  const time_cost =
    '劳动仲裁一审通常 2-4 个月；企业不服起诉到法院，一审再加 3-6 个月，走完一审二审可能大半年到一年。期间要准备材料、跑立案、出庭。';
  const money_cost =
    '劳动仲裁本身不收费。请律师多为风险代理（胜诉后抽 10-30%），小额案件律师往往不愿接；收入低可申请 12348 法律援助（免费）。';
  const risk = employed
    ? '在职期间主张，可能面临调岗、降薪等压力；已离职则没有这个顾虑，但仲裁时效从离职起算 1 年。'
    : '你已离职，没有在职方面的顾虑；注意仲裁时效从离职起算 1 年，别拖过。';

  let verdict: string;
  let verdict_level: string;
  let note: string;

  if (evidence === '几乎没有') {
    verdict = '建议先收集证据';
    verdict_level = 'warn';
    note =
      `你被欠约 ${group(owedAmount)} 元，这笔钱是该给你的，目前证据还比较少。` +
      '加班费需要由劳动者一方举证，所以现阶段先把证据备齐，要回来的把握会大很多。\n' +
      '建议悄悄收集：排班表拍照、加班通知/群消息截图、打卡记录、跟主管确认加班的聊天记录。' +
      '证据备齐后（或离职时）再主张，仲裁时效从离职起算 1 年，时间够用——准备做足，成功把握更大。';
  } else if (owedAmount < 3000 && employed && evidence !== '充分') {
    verdict = '先留证，离职时一并主张更划算';
    verdict_level = 'caution';
    note =
      `你被欠约 ${group(owedAmount)} 元，金额不算大、还在职。` +
      '更划算的做法是先把证据留好（排班、加班通知、打卡、沟通记录），' +
      '等离职时把加班费和经济补偿等一次性主张——这样 1 年时效能用足，金额累积起来更可观，离职后也没有后顾之忧。';
  } else if (owedAmount >= 10000 || !employed || evidence === '充分') {
    verdict = '值得争取';
    verdict_level = 'good';
    const reasons: string[] = [];
    if (owedAmount >= 10000) reasons.push('金额较大');
    if (!employed) reasons.push('已离职无后顾之忧');
    if (evidence === '充分') reasons.push('证据较齐全');
    note =
      `你被欠约 ${group(owedAmount)} 元（${reasons.join('、')}），这笔钱值得争取回来。\n` +
      `胜算：${winChance}\n` +
      '可以先打 12333 咨询，或申请 12348 法律援助（低收入免费），也可以找风险代理律师（胜诉才抽成，不赢不花钱）。\n' +
      '小提示：万一企业拖欠，还能申请强制执行，给自己留足时间预期。';
  } else {
    verdict = '可以争取，选稳妥的方式';
    verdict_level = 'caution';
    note =
      `你被欠约 ${group(owedAmount)} 元，金额中等、证据一般${employed ? '、还在职' : ''}。\n` +
      `胜算：${winChance}\n` +
      '两条路都行：一是现在就把证据补强（排班、加班通知、打卡、沟通记录）去主张；' +
      '二是先留好证据，等离职时再一并提（时效 1 年）。结合自己的情况，选更稳妥的那条。';
  }

  return {
    owed_amount: owedAmount,
    employed,
    evidence,
    win_chance: winChance,
    time_cost,
    money_cost,
    risk,
    verdict,
    verdict_level,
    note,
  };
}
