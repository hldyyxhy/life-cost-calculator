// calc/prompts.ts —— 「问 AI」提示词生成（calc_engine.py:1431-2477 的 build_*_prompt + _profile_brief）
// 纯字符串拼接，零数值风险。依赖 fmt 格式化 + normalizeChildrenByAge。
import { group, fix0, fix1, pct0, pct1, pct2 } from '../fmt';
import { normalizeChildrenByAge } from './normalizeChildren';

// 求助场景库（按钮墙用）—— calc_engine.py:1670
export const HELP_SCENARIOS: Record<string, { title: string; role: string; situation: string; law: string }> = {
  欠薪: { title: '被拖欠工资 / 加班费', role: '资深劳动法律师', situation: '我的工资 / 加班费被拖欠了', law: '《劳动法》《劳动合同法》《保障农民工工资支付条例》' },
  社保: { title: '公司不缴社保 / 公积金', role: '资深社保与劳动法律师', situation: '公司没给我缴社保，或没缴公积金', law: '《社会保险法》《住房公积金管理条例》' },
  辞退: { title: '违法辞退 / 没给经济补偿', role: '资深劳动法律师', situation: '我被辞退了，公司没给经济补偿，或补偿不合理', law: '《劳动合同法》第 47、87 条' },
  无合同: { title: '没签劳动合同', role: '资深劳动法律师', situation: '公司一直没和我签书面劳动合同', law: '《劳动合同法》第 10、82 条（未签合同可主张二倍工资）' },
  工伤: { title: '受了工伤', role: '资深工伤与劳动法律师', situation: '我在工作中受了伤', law: '《工伤保险条例》' },
  消费: { title: '消费纠纷（商品 / 服务 / 预付卡跑路）', role: '资深消费者权益保护律师', situation: '我买商品或服务遇到问题，或商家收了钱跑路', law: '《消费者权益保护法》' },
  网贷催收: { title: '网贷 / 信用卡 / 暴力催收', role: '资深金融消费者权益律师', situation: '我被网贷或信用卡催收困扰（利息过高、暴力催收等）', law: '民间借贷利率上限（LPR 4 倍）、催收自律公约' },
  租房: { title: '租房 / 押金纠纷', role: '资深房屋租赁纠纷律师', situation: '我租房遇到问题（押金不退、房东违约、中介坑等）', law: '《民法典》合同编、当地房屋租赁规定' },
  派遣中介: { title: '劳务派遣 / 黑中介', role: '资深劳动法律师', situation: '我通过劳务派遣或中介找工作，被坑了（收费、克扣、不安排等）', law: '《劳动合同法》劳务派遣专节、《就业促进法》' },
  心理: { title: '心理崩溃 / 压力撑不住', role: '有共情力的心理援助工作者', situation: '我最近压力大到撑不住了，不知道怎么办', law: '（非法律问题，重点是情绪支持和求助渠道）' },
};

// 反诈类型库（按钮墙用）—— calc_engine.py:1735
export const FRAUD_TYPES: Record<string, { title: string; features: string }> = {
  task_rebate: { title: '刷单 / 兼职返利', features: '先让你刷几单、返小额佣金建立信任，再要求大额任务或垫付；或说「操作失误，要连做几单才能提现」。刷单本身违法，凡要先垫钱的兼职 = 骗。' },
  loan_fee: { title: '网贷 / 提额要先交钱', features: '放款前要交「解冻费/保证金/工本费/验资」，或让你往自己账户打流水证明还款能力。正规贷款放款前不收任何费用；凡先交钱的贷款 = 骗。' },
  pig_butchering: { title: '网恋带投资（杀猪盘）', features: '网上认识的「高富帅/美女」嘘寒问暖建立感情，再透露「内幕/漏洞」带你到某投资或博彩平台赚大钱。你看到的账户余额是假的，最后血本无归。' },
  impersonate: { title: '冒充客服 / 公检法', features: '自称京东/微信/支付宝客服说你「注销校园贷/账户异常/理赔」，或自称公检法说你「涉嫌洗钱/案件」要配合、转钱到「安全账户」、开屏幕共享。真警察不会电话办案，没有所谓「安全账户」。' },
  lottery_refund: { title: '中奖 / 理赔先交钱', features: '说你中奖或快递丢失要理赔，领钱前先交「税/手续费/公证费」，或退款要你「刷流水恢复信用」。先要钱的中奖理赔 = 骗。' },
  misc: { title: '其他 / 我也说不准', features: '说不清是哪类，但对方在要钱、要验证码、要屏幕共享，或催促威胁你不让挂电话、不让告诉家人。' },
};

/** _profile_brief (1934)：从档案提取客观事实拼一段（只填用户确认的事实，不含工具估算）。 */
export function profileBrief(profile: any): string {
  if (!profile) return '';
  const p = profile;
  const bits: string[] = [];
  const age = p.age;
  const gender = p.gender;
  if (age) {
    let line = `年龄 ${age} 岁`;
    if (gender) {
      line += `（${gender}）`;
      const health = p.health;
      if (health && !String(health).includes('健康')) line += `，${health}`;
    }
    bits.push(line);
  } else if (gender) {
    bits.push(`性别：${gender}`);
  }
  const ins = p.insurance;
  if (ins) bits.push(`社保：${ins}`);
  const fam: string[] = [];
  if (p.has_partner) {
    const pw = p.partner_wage;
    fam.push('有伴侣' + (pw !== null && pw !== undefined && pw !== '' && pw !== 0 ? `（月薪约 ${pw}）` : ''));
  }
  const nc = p.num_children;
  if (nc) fam.push(`${nc} 个孩子`);
  if (p.support_elderly) fam.push('需赡养老人');
  if (fam.length) bits.push('家庭：' + fam.join('、'));
  const sav = p.savings;
  if (sav !== null && sav !== undefined && sav !== '' && sav !== 0) bits.push(`现有存款约 ${sav} 元`);
  const debts: string[] = [];
  const m = p.mortgage_monthly;
  if (m !== null && m !== undefined && m !== '' && m !== 0) debts.push(`房贷 ${m}/月`);
  const cl = p.car_loan_monthly;
  if (cl !== null && cl !== undefined && cl !== '' && cl !== 0) debts.push(`车贷 ${cl}/月`);
  if (debts.length) bits.push('现有月供负债：' + debts.join('、'));
  if (!bits.length) return '';
  return '【我的其他情况（个人档案）】\n- ' + bits.join('；') + '\n\n';
}

/** build_overtime_prompt (1431)：加班费维权。 */
export function buildOvertimePrompt(
  wage: number, weekdayOt: number, weekendOt: number, holidayOt: number,
  actual: number, months: number, employed: boolean, evidence: string, city: string = '',
): string {
  const employedCn = employed ? '还在职' : '已经离职';
  const evidenceMap: Record<string, string> = {
    充分: '比较齐全（考勤、排班、加班通知、聊天记录等基本都有）',
    部分: '有一部分（比如排班表或聊天记录，但不全）',
    几乎没有: '几乎没有（没什么能证明加班的材料）',
  };
  const evidenceDesc = evidenceMap[evidence] ?? evidence;
  let cityLine: string;
  let localQ: string;
  if (city) {
    cityLine = `- 所在城市：${city}`;
    localQ = `针对我所在城市「${city}」，有没有我该知道的本地规定或更划算的做法？`;
  } else {
    cityLine = '- 所在城市：（我稍后补充，请先按一般情况分析）';
    localQ = '有没有我该知道的常见地方性规定或更划算的做法？';
  }
  return (
    '请以资深劳动法律师的口吻，面向不太懂法律的普通劳动者，用大白话帮我解答。我的情况如下：\n\n' +
    '【我的情况】\n' +
    `- 月工资：${group(wage)} 元\n` +
    `- 每月加班：工作日延时 ${weekdayOt} 小时、休息日 ${weekendOt} 小时、法定节假日 ${holidayOt} 小时\n` +
    `- 每月实际拿到的加班费：${group(actual)} 元\n` +
    `- 这种情况持续了：${months} 个月\n` +
    `- 我目前：${employedCn}\n` +
    `- 手头的证据：${evidenceDesc}\n` +
    `${cityLine}\n\n` +
    '【请帮我算清楚，并告诉我怎么办】\n' +
    '1. 按国家法律，我每月依法应得多少加班费？请给出计算过程（法定时薪 = 月工资 ÷ 21.75 ÷ 8；工作日延时 1.5 倍、休息日 2 倍、法定节假日 3 倍）。\n' +
    `2. 对照我实际拿到的，我每月被欠多少？这 ${months} 个月总共被欠多少？\n` +
    '3. 如果我想把这笔钱要回来，具体该怎么操作？请分步骤讲（先做什么、再做什么），需要准备哪些材料证据、找哪个部门、打哪个电话。\n' +
    '4. 维权大概要花多少时间、有哪些成本和风险（比如在职会不会被针对、劳动仲裁时效、举证难不难、赢了能不能真拿到钱）？请结合我的情况实事求是地说，既不夸大也不劝退。\n' +
    `5. ${localQ}\n` +
    '6. 综合我的实际情况，你最建议我怎么做（现在就去争取 / 先悄悄留好证据以后再说 / 其他）？说说理由。\n\n' +
    '要求：站在我的利益最大化角度，给具体、能照着做的建议，别讲空话套话，也别不管不顾地鼓励我去硬刚。'
  );
}

/** build_loan_apr_prompt (1482)：真实年化反算。 */
export function buildLoanAprPrompt(principal: number, monthly: number, periods: number, profile: any = null): string {
  return (
    '请以资深金融消费者权益保护专家的口吻，用大白话帮我判断这笔贷款正不正常、我有没有被坑。情况如下：\n\n' +
    '【这笔贷款】\n' +
    `- 借款本金：${group(principal)} 元\n` +
    `- 每月还款：${group(monthly)} 元\n` +
    `- 期数：${periods} 个月\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 反算这笔贷款的真实年化利率（IRR 复利口径）和名义年化，给出计算过程。\n' +
    '2. 按真实年化判断它属于哪类（正常 / 偏高 / 高利贷 24%-36% / 超过 36% 红线），结合国家法律说清楚。\n' +
    '3. 如果是高利贷或超红线，我有哪些权利？（如超 36% 部分约定无效可主张返还、24%-36% 法院不予保护等）\n' +
    '4. 我该怎么维权？分步骤讲——找谁、打什么电话、准备什么材料。\n' +
    '5. 综合看，我现在怎么做最划算？\n\n' +
    '要求：站在我的利益最大化角度，实事求是，给能照着做的具体建议，别讲空话。'
  );
}

/** build_compare_methods_prompt (1504)：还款方式对比。 */
export function buildCompareMethodsPrompt(principal: number, aprPct: number, periods: number, profile: any = null): string {
  return (
    '请以资深金融顾问的口吻，用大白话帮我讲清楚两种还款方式的区别，我快被绕晕了。情况如下：\n\n' +
    '【这笔贷款】\n' +
    `- 本金：${group(principal)} 元\n` +
    `- 名义年化：${fix1(aprPct)}%（机构报的价）\n` +
    `- 期数：${periods} 个月\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 分别按「等额本息」和「等本等息（消费分期常见的固定手续费制）」算：每月还多少、总利息多少、真实年化（IRR）多少，给计算过程。\n' +
    '2. 重点解释：为什么「等本等息」的真实年化会比名义高那么多？（提示：手续费按初始本金收、不随还款递减）\n' +
    '3. 如果我正被推销的消费分期 / 信用卡分期用的是「等本等息」，我实际多花了多少？划不划算？\n' +
    '4. 我该怎么选、怎么跟机构谈、有什么要注意的坑？\n\n' +
    '要求：大白话，给具体建议，别讲空话。'
  );
}

/** build_affordable_debt_prompt (1526)：可承受负债。 */
export function buildAffordableDebtPrompt(surplus: number, aprPct: number, periods: number, income: number | null = null, profile: any = null): string {
  const incomeLine = income ? `- 月薪：${group(income)} 元\n` : '- 月薪：（我没填，请按一般情况估算）\n';
  return (
    '请以资深理财顾问的口吻，用大白话帮我判断我现在能不能再借钱、借多少安全。情况如下：\n\n' +
    '【我的情况】\n' +
    `- 每月结余（收入扣掉必要开支后剩下的）：${group(surplus)} 元\n` +
    incomeLine +
    `- 想借的名义年化：${fix1(aprPct)}%\n` +
    `- 想借的期数：${periods} 个月\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 按健康负债的标准（月还款不超过月结余 / 收入的合理比例），我最多能借多少本金？给计算。\n' +
    '2. 我目前的负债能力算健康吗？有没有风险信号？\n' +
    '3. 借之前我该想清楚哪些事？（用途、还款来源、万一收入断了怎么办）\n' +
    '4. 有没有比借钱更好的替代办法？\n\n' +
    '要求：站在我不踩坑的角度，实事求是，给具体建议。'
  );
}

/** build_debt_payoff_prompt (1549)：多笔债雪球/雪崩。 */
export function buildDebtPayoffPrompt(debtsDesc: string, extra: number): string {
  return (
    '请以资深债务顾问的口吻，用大白话帮我制定还清多笔债务的最优方案。情况如下：\n\n' +
    '【我的债务】\n' +
    `${debtsDesc}\n` +
    `- 每月除了各笔最低还款，我还能额外挤出：${group(extra)} 元\n\n` +
    '【请帮我】\n' +
    '1. 按「雪球法」（先还余额最小）和「雪崩法」（先还利率最高）分别推演：多久能全还清、总共要付多少利息？哪种更省？\n' +
    '2. 结合我的情况，建议用哪种、为什么。\n' +
    '3. 有没有哪笔债的最低还款根本盖不住利息（越还越多）？怎么处理？\n' +
    '4. 分步骤讲具体怎么操作（各笔怎么分配、怎么跟债权方谈减免 / 分期）。\n' +
    '5. 怎样能更快摆脱债务（增收、减支、协商等现实办法）？\n\n' +
    '要求：给现实、可执行的方案，别讲空话，也别吓唬我。'
  );
}

/** build_spiral_prompt (1568)：以贷养贷螺旋。 */
export function buildSpiralPrompt(init: number, aprPct: number, months: number, pay: number, profile: any = null): string {
  return (
    '请以资深债务顾问的口吻，用大白话帮我判断我是不是陷入了「以贷养贷」的恶性循环、该怎么脱困。情况如下：\n\n' +
    '【我的情况】\n' +
    `- 目前欠着：${group(init)} 元\n` +
    `- 这笔债的年化：${fix1(aprPct)}%\n` +
    `- 每月我实际能还：${group(pay)} 元\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 按这个还款力度，我的债务是在涨还是在降？大概多久会翻倍？给计算。\n' +
    '2. 我算不算陷入了「借新还旧 / 以贷养贷」的螺旋？严重程度如何？\n' +
    '3. 要让债务停止增长，我每月至少得还多少（止血线）？\n' +
    '4. 给我一个现实可行的脱困方案：怎么止血、怎么逐步还清、要不要债务重组 / 协商、找什么帮助。\n' +
    '5. 如果是网贷 / 信用卡，有没有我该知道的维权或救济渠道（如暴力催收投诉）？\n\n' +
    '要求：实事求是，给我能照着做的出路，别只吓唬我。'
  );
}

/** build_min_wage_prompt (1589)：最低工资对照。 */
export function buildMinWagePrompt(wage: number, tier: string, city: string = '', profile: any = null): string {
  const cityLine = city ? `- 所在城市：${city}` : '- 所在城市：（请按我所在城市等级对应的典型城市分析）';
  return (
    '请以资深劳动法律师的口吻，用大白话帮我判断我的工资是不是低于法定底线、该怎么办。情况如下：\n\n' +
    '【我的情况】\n' +
    `- 我的月薪：${group(wage)} 元\n` +
    `- 所在城市等级：${tier}\n` +
    `${cityLine}\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 我所在地区目前的最低工资标准（精确值）是多少？我的工资有没有低于这个底线？\n' +
    '2. 如果低于，这是违法的——法律依据是什么（如《劳动法》第 48 条）？\n' +
    '3. 就算没低于，我的工资在当地处在什么水平？议价空间大不大？\n' +
    '4. 如果我想争取合理工资或维权，具体怎么做（找谁、打什么电话、准备什么）？\n' +
    '5. 针对我所在地区，有没有我该知道的本地规定？\n\n' +
    '要求：站在我的利益角度，给现实、能照着做的建议。'
  );
}

/** build_unemployment_prompt (1611)：失业金（外包 AI 查当地）。 */
export function buildUnemploymentPrompt(city: string = '', years: any = '', wage: any = '', reason: string = '', profile: any = null): string {
  const cityLine = city ? `- 我所在的城市：${city}` : '- 我所在的城市：（我稍后告诉你，请先问我）';
  let yearsLine: string;
  const yr = parseFloat(years);
  if (!isNaN(yr)) {
    yearsLine = `- 失业保险累计缴费年限：${fix0(yr)} 年`;
  } else {
    yearsLine = '- 失业保险累计缴费年限：（请问我，这决定能领几个月）';
  }
  let wageLine: string;
  if (wage) {
    const fw = parseFloat(wage);
    wageLine = isNaN(fw) ? '- 上份工作月工资：（请问我）' : `- 上份工作月工资：${group(fw)} 元`;
  } else {
    wageLine = '- 上份工作月工资：（请问我）';
  }
  return (
    '请以资深社保 / 劳动保障专家的口吻，用大白话帮我算清楚：我被裁（或快失业）了，能领多少失业金、领多久、怎么领。情况如下：\n\n' +
    '【我的情况】\n' +
    `${cityLine}\n${yearsLine}\n${wageLine}\n` +
    `- 离职原因：${reason || '（请问我：公司辞退 / 合同到期不续签 / 协商解除 / 个人原因，这关系到能不能领）'}\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 按我所在城市的最新规定，算我大概能领多少失业金、能领几个月。\n' +
    '2. 领失业金需要满足什么条件？我的情况符不符合？\n' +
    '3. 具体怎么申领？去哪里办、带什么材料、能线上办吗？\n' +
    '4. 领失业金期间，我的医保 / 养老保险怎么办？有没有其他配套待遇？\n' +
    '5. 除了失业金，我还能不能领别的（如失业补助金、临时救助、就业服务）？\n\n' +
    '要求：结合我所在城市的最新政策，给具体、能照着办的步骤。'
  );
}

/** build_subsidy_prompt (1644)：灵活就业社保补贴（4050）。 */
export function buildSubsidyPrompt(city: string = '', profile: any = null): string {
  const cityLine = city ? `- 我所在的城市：${city}` : '- 我所在的城市：（我稍后告诉你，请先问我）';
  return (
    '请以资深社保 / 就业援助专家的口吻，用大白话帮我搞清楚：我能不能领「灵活就业社保补贴」（有的地方叫 4050 补贴、就业困难人员社保补贴），能补多少、怎么申请。情况如下：\n\n' +
    '【我的情况】\n' +
    `${cityLine}\n` +
    '- 性别：（请问我，4050 对性别和年龄都有要求，一般女≥40/男≥50）\n' +
    '- 是否以灵活就业身份自己缴职工养老+医保？（居民社保不算，请确认）\n' +
    '- 我有没有被认定为「就业困难人员」？（请问我，这是申领前提）\n\n' +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 按我所在城市的最新规定，结合我的年龄/性别/社保情况，判断我能不能享受这个补贴。\n' +
    '2. 如果能，补贴标准大概多少、能享受多久？\n' +
    '3. 怎么申请？去哪里办、带什么材料、流程是什么？\n' +
    '4. 有没有我容易忽略的坑（比如要先做灵活就业登记、认定就业困难人员等）？\n' +
    '5. 除了这个补贴，我这种情况还有没有别的能领的（如创业补贴、技能补贴）？\n\n' +
    '要求：结合我所在城市的最新政策，给具体、能照着办的步骤。'
  );
}

/** build_help_prompt (1704)：求助场景。 */
export function buildHelpPrompt(sceneKey: string, city: string = ''): string {
  const s = HELP_SCENARIOS[sceneKey];
  if (!s) return '（未知场景）';
  const cityLine = city ? `- 我所在的城市：${city}` : '- 我所在的城市：（请先问我，或先按一般情况）';
  const local = city ? `结合我所在城市 ${city} 的最新规定，` : '';
  return (
    `请以${s.role}的口吻，用大白话帮我。${s.situation}。情况如下：\n\n` +
    '【先了解我的情况】\n' +
    `${cityLine}\n` +
    '- 请你先问清楚我关键的细节（比如事情经过、有没有合同或证据、涉及多少钱、拖了多久、对方是什么单位等），再给我建议。\n\n' +
    '【请帮我】\n' +
    '1. 我这种情况，最该找哪个部门？打什么电话？（如 12333 / 12345 / 12315 / 12348 / 110、劳动监察大队、劳动仲裁委等，结合我的问题给准确）\n' +
    '2. 我具体该怎么操作？分步骤讲——先做什么、准备什么材料证据、去哪里办、能不能线上办。\n' +
    `3. 有没有时效限制（比如劳动仲裁时效 1 年）？相关法律依据是什么（${s.law}）？\n` +
    `4. ${local}有没有我该知道的本地政策或更划算的做法？\n` +
    '5. 综合看，我现在第一步最该干什么？\n\n' +
    '要求：站在我的利益最大化角度，给具体、能照着做的建议，别讲空话，也别不管不顾地鼓励我去硬刚。'
  );
}

/** build_antifraud_prompt (1769)：反诈场景。 */
export function buildAntifraudPrompt(key: string, city: string = ''): string {
  const f = FRAUD_TYPES[key];
  if (!f) return '（未知场景）';
  const cityLine = city ? `- 我所在的城市：${city}` : '- 我所在的城市：（请先问我，或先按一般情况）';
  const local = city ? `结合我所在城市 ${city}，` : '';
  return (
    `请以资深反诈民警的口吻，用大白话帮我判断。我怀疑遇到了【${f.title}】类骗局。对方的情况、原话、或发来的链接/二维码如下（我会贴在下面）：\n\n` +
    '【请在这里贴对方的话术、行为描述、或链接/二维码】\n\n' +
    `这类骗局的典型特征：${f.features}\n\n` +
    `${cityLine}\n\n` +
    '【请帮我】\n' +
    '1. 先判断：这大概率是不是骗局？依据是什么（对照上面的典型特征，一条条比对）？\n' +
    '2. 如果是或存疑：我**现在绝对不能做什么**？（别转账、别给验证码/短信码、别开屏幕共享、别按对方说的操作、别退出官方 APP 去加对方私聊）\n' +
    '3. 如果我已经转了钱 / 给了银行卡和验证码 / 开了屏幕共享：**现在立刻怎么紧急止损**？（打银行客服冻结、96110、110——分步骤、抢时间）\n' +
    '4. 怎么核实对方真伪？（通过官方 APP、官方客服电话、或 110 反查，千万别用对方提供的号码去「核实」）\n' +
    `5. ${local}我该去哪里报警、怎么举报（96110 / 110 / 国家反诈中心 APP / 12321）？\n\n` +
    '要求：宁可错杀不可放过——只要对方要钱、要验证码、要屏幕共享、催你或威胁你，就先按骗局处理：停止操作、止损、再核实。别讲空话，给我能立刻照做的步骤。'
  );
}

/** build_current_situation_prompt (1798)：处境诊断。 */
export function buildCurrentSituationPrompt(
  age: number, tier: string, wage: number, ins: string, housing: string, food: string,
  hasCar: boolean, numKids: number, supportElderly: boolean, savings: number, city: string = '',
  childrenByAge: Record<string, number> | null = null, familyMonthly: number = 0,
  hasPartner: boolean = false, partnerWage: number = 0, partnerIns: string = '',
): string {
  const carCn = hasCar ? '有车（含养车成本）' : '无车';
  const elderCn = supportElderly ? '需要赡养老人' : '暂不需要赡养老人';
  let kidsCn: string;
  if (numKids) {
    const segs = normalizeChildrenByAge(childrenByAge, numKids);
    const desc = Object.entries(segs).map(([seg, n]) => `${seg}${n}人`).join('、');
    kidsCn = `有 ${numKids} 个孩子` + (desc ? `（${desc}）` : '');
  } else {
    kidsCn = '没孩子';
  }
  const savingsCn = savings ? `${group(savings)} 元` : '几乎没存款';
  const cityLine = city ? `- 所在城市：${city}（等级 ${tier}）` : `- 所在城市等级：${tier}（具体城市请结合该等级典型城市分析，或先问我）`;
  let extraLines = '';
  if (familyMonthly) extraLines += `- 每月给老家：${group(familyMonthly)} 元\n`;
  if (hasPartner) {
    const pwCn = `伴侣月薪约 ${group(partnerWage)} 元` + (partnerIns ? `（${partnerIns}）` : '');
    extraLines += `- ${pwCn}（家庭双收入）\n`;
  }
  return (
    '请以资深个人理财顾问和生活规划师的口吻，面向一个不太懂理财的普通劳动者，用大白话帮我分析处境、给可执行的建议。我的情况如下：\n\n' +
    '【我的情况】\n' +
    `- 年龄：${age} 岁\n` +
    `- 月薪（税前）：${group(wage)} 元\n` +
    `- 社保：${ins}\n` +
    `- 住房：${housing}　饮食档次：${food}\n` +
    `- ${carCn}\n` +
    `- 家庭：${kidsCn}，${elderCn}\n` +
    `${extraLines}` +
    `- 目前存款：${savingsCn}\n` +
    `${cityLine}\n\n` +
    '【请帮我分析】\n' +
    '1. 先帮我估算：按我的情况，每月大概能结余多少钱（还是入不敷出）？给估算和思路。\n' +
    '2. 我的财务处境健康吗？最该警惕的风险是什么（如没存款抗不了意外、社保断缴影响养老、结余太少攒不下钱等）？\n' +
    '3. 给我几条**能照着做**的建议——请区分哪些是我个人能改的（消费习惯、副业、技能），哪些是结构性的（城市、行业、政策）。别只说「努力攒钱」这种空话，也别把系统性问题全怪到我头上。\n' +
    '4. 如果我想改善处境（增收 / 减支 / 换城市 / 提升技能），最现实、性价比最高的第一步是什么？\n' +
    '5. 结合我所在地区，有没有我该知道的政策或补贴（如灵活就业社保补贴、公租房、个税专项扣除等）？\n\n' +
    '要求：实事求是，不灌鸡汤，给具体能落地的建议。'
  );
}

/** build_milestones_prompt (1849)：人生三座山。 */
export function buildMilestonesPrompt(tier: string, wage: number, city: string = '', profile: any = null): string {
  const cityLine = city ? `- 所在城市：${city}（等级 ${tier}）` : `- 所在城市等级：${tier}`;
  return (
    '请以资深生活规划师的口吻，面向普通劳动者，用大白话帮我算清楚「人生三座山」（结婚、养娃、养老）大概要花多少钱、我该怎么准备。我的情况如下：\n\n' +
    '【我的情况】\n' +
    `- 月薪：${group(wage)} 元\n` +
    `${cityLine}\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 先问清楚我最关心哪座山（结婚 / 养娃 / 养老）以及细节——比如结婚的话有没有彩礼/婚房压力；养娃的话孩子多大、想走公办还是民办；养老的话打算几岁退、社保缴了多少——然后再估算要花多少钱。\n' +
    '2. 按我的收入和所在城市，攒够这笔钱大概要多久？现实不现实？\n' +
    '3. 有没有省钱也能办成的现实办法（公办、补贴、集体办、平替方案）？\n' +
    '4. 我现在每月该存多少、怎么存，才不至于到时候抓瞎？\n' +
    '5. 结合我所在地区，有没有相关的政策、补贴或低门槛途径？\n\n' +
    '要求：实事求是，区分我能改变的和政策/社会层面的，不灌鸡汤。'
  );
}

/** build_compare_prompt (1873)：城市加减法。 */
export function buildComparePrompt(
  tierA: string, tierB: string, wage: number, targetCity: string = '', housing: string = '合租单间',
  food: string = '普通', hasCar: boolean = false, insurance: string = '在职（单位缴）',
): string {
  const bLine = targetCity ? `- 想去的目标城市：${targetCity}（等级 ${tierB}）` : `- 想去的目标城市：等级 ${tierB}（具体城市名我稍后补充，请先问我）`;
  const lifeLine = `- 住房方式：${housing}　饮食档次：${food}　${hasCar ? '有车' : '无车'}　社保：${insurance}`;
  return (
    '请以资深职业与生活规划师的口吻，面向普通劳动者，用大白话帮我判断「换个城市值不值」。我的情况如下：\n\n' +
    '【我的情况】\n' +
    `- 月薪：${group(wage)} 元\n` +
    `- 现在城市：等级 ${tierA}（具体城市名请先问我）\n` +
    `${bLine}\n${lifeLine}\n\n` +
    '【请帮我】\n' +
    '1. 先问清楚我两边的具体城市名，然后对比这两座城市：生活成本（房租、吃饭、交通）、工资水平、就业机会、买房 / 落户难度。\n' +
    '2. 按我的收入，在两个城市分别能结余多少？生活质量差别大吗？\n' +
    '3. 换到目标城市，我的工资大概能涨 / 跌多少？多久能回本（搬家成本、过渡期没收入）？\n' +
    '4. 除了钱，还有哪些该考虑的（离家远近、社保转移、孩子教育、人脉等）？\n' +
    '5. 综合看，我这种情况换城市值不值？有什么风险和注意事项？\n\n' +
    '要求：结合两座城市的真实情况给具体、现实的判断，别只说「大城市机会多」这种空话。'
  );
}

/** build_injury_prompt (1899)：工伤赔偿。 */
export function buildInjuryPrompt(city: string, grade: number, monthlyWage: number, profile: any = null): string {
  return (
    '请以资深工伤与劳动法律师的口吻，用大白话帮我。我在工作中受了伤，想搞清楚能赔多少、怎么走流程。情况如下：\n\n' +
    '【我的情况】\n' +
    `- 所在城市：${city}\n` +
    `- 伤残等级（劳动能力鉴定）：${grade} 级（若还没鉴定，请先问我伤情帮我预估级别）\n` +
    `- 受伤前 12 个月平均月工资：${group(monthlyWage)} 元\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 按国家《工伤保险条例》，我这个等级能拿到哪些赔偿？（一次性伤残补助金、伤残津贴、一次性工伤医疗/就业补助金等）逐项算给我看。\n' +
    '2. 我所在省/市有没有额外标准或差异？\n' +
    '3. 工伤认定完整流程：单位多久内申报、单位不报我怎么办、去哪认定、多久出结果。\n' +
    '4. 劳动能力鉴定怎么申请、对评级不服怎么办。\n' +
    '5. 治疗期间（停工留薪期）工资怎么发、医疗费谁出。\n' +
    '6. 如果单位没缴工伤保险，我该找谁、怎么办。\n\n' +
    '要求：结合我所在地的规定，给具体金额和步骤，别讲空话。'
  );
}

/** build_buy_rent_prompt (2138)：买房vs租房。 */
export function buildBuyRentPrompt(tier: string, years: number, area: number = 90, downRatio: number = 0.3, city: string = '', profile: any = null): string {
  const cityLine = city ? `- 关注的城市：${city}（等级 ${tier}）` : `- 城市等级：${tier}（请结合该等级典型城市，或先问我具体城市）`;
  return (
    '请以资深房产分析师的口吻，用大白话帮我判断「买房还是租房」。我的情况：\n\n' +
    '【我的情况】\n' +
    `${cityLine}\n` +
    `- 对比年限：${years} 年　房产面积：${area}㎡　首付比例：${pct0(downRatio)}\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 结合当地最新的房价、租金、房贷利率，算一算这几年买房 vs 租房大致花多少、哪个更划算。\n' +
    '2. 现在的楼市行情，是买房的好时机吗？房价在涨还是跌？给出判断依据。\n' +
    '3. 如果买房，首付、月供、税费、维修大概多少？我这种收入和存款能承受吗？\n' +
    '4. 如果租房，有什么该注意的（租售比、租金走势、长租稳定性）？\n' +
    '5. 综合看，你建议我买还是租？给明确倾向和理由，别和稀泥。\n\n' +
    '要求：结合当地真实行情和最新政策。我知道楼市波动大，给判断时请说明依据和不确定性。'
  );
}

/** build_fund_prompt (2157)：公积金贷款。 */
export function buildFundPrompt(tier: string, balance: number, contrib: number | null = 0, years: number = 30, city: string = '', profile: any = null): string {
  const cityLine = city ? `- 所在城市：${city}（等级 ${tier}）` : `- 城市等级：${tier}`;
  const contribLine = contrib != null && contrib !== 0 ? `- 月缴存：${contrib} 元　` : '';
  return (
    '请以熟悉各地公积金政策的顾问口吻，用大白话帮我算公积金贷款。我的情况：\n\n' +
    '【我的情况】\n' +
    `${cityLine}\n- 公积金账户余额约：${group(balance)} 元\n` +
    `${contribLine}贷款年限：${years} 年\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 按我所在城市的公积金政策，我最多能贷多少？（当地最高额度、余额倍数、缴存要求都查一下）\n' +
    '2. 首套/二套利率分别是多少？按我的额度算月供和总利息。\n' +
    '3. 公积金贷款 vs 商业贷款，我能省多少利息？\n' +
    '4. 申请公积金贷款要满足什么条件、怎么操作（缴存时长、连续性等）？\n' +
    '5. 有没有我该知道的本地优惠政策（组合贷、人才补贴等）？\n\n' +
    '要求：查当地最新公积金政策，给准确数字和能照着做的步骤。'
  );
}

/** build_rate_stress_prompt (2176)：利率压力测试。 */
export function buildRateStressPrompt(principal: number, baseRate: number, years: number = 30, city: string = '', profile: any = null): string {
  const cityLine = city ? `- 所在城市：${city}\n` : '';
  return (
    '请以资深房贷顾问的口吻，用大白话帮我做利率压力测试。我的情况：\n\n' +
    '【我的情况】\n' +
    `- 计划贷款：${group(principal)} 元\n` +
    `- 当前参考利率：${pct2(baseRate)}　贷款年限：${years} 年\n` +
    `${cityLine}\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 当前 LPR 和首套/二套房贷利率是多少？我这种能拿到什么利率？\n' +
    '2. 利率再涨 0.5% 或 1%（或降），月供和总利息会变多少？\n' +
    '3. 现在选固定利率还是 LPR 浮动更划算？为什么？\n' +
    '4. 未来若加息压力大，有什么应对（提前还贷、转贷等）？\n' +
    '5. 综合看，我现在该锁定利率还是等等？\n\n' +
    '要求：结合当前 LPR 走势和政策，给明确建议。'
  );
}

/** build_tax_prompt (2271)：个税优化。 */
export function buildTaxPrompt(
  annualSalary: number, bonus: number, city: string = '', special: number = 0, social: number = 0,
  kids: number = 0, elderly: boolean = false, loan: boolean = false, edu: boolean = false, profile: any = null,
): string {
  const cityLine = city ? `- 所在城市：${city}\n` : '';
  const familyBits: string[] = [];
  if (kids) familyBits.push(`子女 ${kids} 个`);
  if (elderly) familyBits.push('需赡养老人');
  if (loan) familyBits.push('有首套房贷');
  if (edu) familyBits.push('本人继续教育');
  const familyLine = familyBits.length ? '- 家庭扣除情况：' + familyBits.join('、') + '\n' : '';
  const deduLine = special || social ? `- 月专项附加扣除合计：${group(special)} 元　月社保个人部分：${group(social)} 元\n` : '';
  return (
    '请以熟悉个税政策的税务顾问口吻，用大白话帮我做税务优化。我的情况：\n\n' +
    '【我的情况】\n' +
    `- 年税前工资约 ${group(annualSalary)} 元\n` +
    `- 年终奖约 ${group(bonus)} 元\n` +
    `${deduLine}${familyLine}${cityLine}\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 我的年终奖该单独计税还是并入综合所得？分别算给我看，哪个省、省多少。\n' +
    '2. 我能享受哪些专项附加扣除？每项能扣多少、我符不符合、怎么在个税 APP 申报？\n' +
    '3. 有没有我容易漏的扣除（赡养老人、继续教育、大病医疗、房租/房贷）？\n' +
    '4. 按我的情况，全年大概交多少税、到手多少？有没有合法节税空间？\n' +
    '5. 结合最新个税政策（起征点、专项扣除标准、年终奖优惠延续到何时），给明确建议。\n\n' +
    '要求：算给我看（给税额），给能在个税 APP 照着操作的步骤。'
  );
}

/** build_assistance_prompt (2361)：本地救助。 */
export function buildAssistancePrompt(city: string, perCapitaIncome: number, familyInfo: string = '', asset: number | null = null, profile: any = null): string {
  const assetLine = asset ? `- 家庭人均金融资产：${group(asset)} 元\n` : '';
  return (
    '请以民政/社会救助专家的口吻，用大白话帮我判断能申请什么救助。我的情况：\n\n' +
    '【我的情况】\n' +
    `- 所在城市：${city}\n- 家庭人均月收入约：${group(perCapitaIncome)} 元\n` +
    `${assetLine}` +
    `- 家庭情况：${familyInfo || '（请先问我家庭人数、是否有老小病残、现有保障）'}\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 按我所在城市的最新标准，我符合低保 / 低保边缘 / 特困哪一档？能领多少？\n' +
    '2. 怎么申请？去哪里（街道/乡镇民政）、带什么材料、流程几步、多久能批？\n' +
    '3. 财产限制（金融资产/车辆/房产）我过不过？\n' +
    '4. 除了低保，我还能申请什么（临时救助/医疗救助/教育救助/公租房/残疾人补贴等）？\n' +
    '5. 申请被拒了怎么办？有没有复议或投诉渠道？\n\n' +
    '要求：查当地最新政策和标准，给能照着做的步骤。'
  );
}

/** build_medical_prompt (2391)：医保报销。 */
export function buildMedicalPrompt(city: string, identity: string, cost: number, retired: boolean = false, remote: string = 'none', profile: any = null): string {
  const DISP: Record<string, string> = { none: '本地就医', filed: '异地已备案', unfiled: '异地未备案' };
  return (
    '请以医保政策专家的口吻，用大白话帮我算医保报销。我的情况：\n\n' +
    '【我的情况】\n' +
    `- 参保城市：${city}\n- 医保类型：${identity}${retired ? '（退休）' : ''}\n` +
    `- 就医方式：${DISP[remote] ?? '本地就医'}\n` +
    `- 预估住院费用：${group(cost)} 元（三级医院）\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 基本医保 + 大病保险，我大概能报多少、自付多少？按当地最新政策算给我看。\n' +
    '2. 我要不要先办异地备案/转诊？怎么办（线上步骤）？不办会少报多少？\n' +
    '3. 我有高血压/糖尿病等慢性病，能不能认定门诊慢特病？认定后门诊能多报多少？\n' +
    '4. 我用的药如果是乙类/谈判药，要先自付多少？怎么查药品在不在医保目录？\n' +
    '5. DRG 改革对我这种病/治疗方式有影响吗？该选什么医院？\n\n' +
    '要求：按当地医保局最新政策，给能照着做的步骤。'
  );
}

/** build_debt_health_prompt (2464)：债务健康。 */
export function buildDebtHealthPrompt(totalDebt: number, monthlyIncome: number, monthlyPay: number, avgApr: number, profile: any = null): string {
  return (
    '请以资深债务顾问的口吻，用大白话帮我评估债务健康、给摆脱债务的建议。我的情况：\n\n' +
    `- 总负债约：${group(totalDebt)} 元\n- 月收入：${group(monthlyIncome)} 元\n` +
    `- 每月能还：${group(monthlyPay)} 元\n- 平均年化约：${pct0(avgApr)}\n\n` +
    profileBrief(profile) +
    '【请帮我】\n' +
    '1. 我的负债健康吗？负债率/月供比算给我看，给明确评级。\n' +
    '2. 按现在还款节奏，多久能还清？总利息多少？有没有更省的还法？\n' +
    '3. 现在最该先做什么？（先还哪笔、要不要债务重组/协商减免、怎么增收）\n' +
    '4. 该警惕什么？（以贷养贷、高息网贷、催收陷阱、征信影响）\n' +
    '5. 实在还不上了，合法出路有哪些（调解/法律援助/个人破产试点）？\n\n' +
    '要求：结合我的实际数字，给能照着做的步骤，别讲空话。'
  );
}
