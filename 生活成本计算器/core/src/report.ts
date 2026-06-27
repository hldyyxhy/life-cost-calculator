// report.ts —— 综合报告生成（翻译自 report.py，纯函数）
import { FIELD_DEFS, GROUP_TITLES, type Profile } from './profile';
import { group, signGroup, fix0, fix1 } from './fmt';

function fmtProfile(profile: Profile): string[] {
  const lines: string[] = [];
  for (const [grp, fields] of Object.entries(FIELD_DEFS)) {
    lines.push(`【${GROUP_TITLES[grp]}】`);
    for (const f of fields) {
      let val = profile[f.key] ?? f.default;
      if (f.ctype === 'entry' && val === '') continue; // 未填不显示
      if (f.ctype === 'check') val = val ? '是' : '否';
      lines.push(`  · ${f.label}：${val}`);
    }
    lines.push('');
  }
  return lines;
}

function fmtCurrent(cur: any): string[] {
  if (!cur) return ['（尚未计算：请到「我现在的处境」点「算一算」）', ''];
  const L = ['【二、我现在的处境（月度）】'];
  L.push(`  · 到手收入：${group(cur.income_net)} 元/月　（五险一金 ${group(cur.social_ins)}、个税 ${group(cur.tax)}）`);
  L.push(`  · 生存成本：${group(cur.cost_total)} 元/月　（城市生存底线 ${group(cur.survival_baseline)}）`);
  const sign = cur.surplus >= 0 ? '+' : '';
  L.push(`  · 月结余：${sign}${group(cur.surplus)} 元/月　（结余率 ${fix0(cur.surplus_rate)}%）`);
  if (cur.house_saving_years) L.push(`  · 攒够婚房首付约需 ${fix0(cur.house_saving_years)} 年`);
  L.push('');
  if (cur.interpretation) {
    for (const ln of cur.interpretation.split('\n')) {
      if (ln.trim()) L.push('    ' + ln);
    }
    L.push('');
  }
  return L;
}

function fmtCompare(cmp: any): string[] {
  if (!cmp) return ['【三、城市加减法】', '  （尚未计算：请到「城市加减法」点「开始对比」）', ''];
  const L = ['【三、城市加减法】'];
  if (cmp.comparison_text) {
    for (const ln of cmp.comparison_text.split('\n')) {
      if (ln.trim()) L.push('  ' + ln);
    }
  }
  const cur = cmp.current;
  const tgt = cmp.target;
  if (cur && tgt) {
    L.push(`  · 当前城市：到手 ${group(cur.income_net)} / 成本 ${group(cur.cost_total)} / 结余 ${group(cur.surplus)}`);
    L.push(`  · 目标城市：到手 ${group(tgt.income_net)} / 成本 ${group(tgt.cost_total)} / 结余 ${group(tgt.surplus)}`);
  }
  L.push('');
  return L;
}

function fmtMilestones(ms: any): string[] {
  const L = ['【四、人生三座山】'];
  for (const [key, title] of [['marriage', '结婚'], ['child', '养娃'], ['retire', '养老']] as [string, string][]) {
    const txt = (ms || {})[key];
    L.push(`  ▸ ${title}：`);
    if (txt) {
      for (const ln of txt.split('\n')) {
        if (ln.trim()) L.push('      ' + ln);
      }
    } else {
      L.push('      （尚未计算）');
    }
  }
  L.push('');
  return L;
}

function buildAdvice(profile: any, cur: any, cmp: any, ms: any): string[] {
  const L = ['【综合建议】'];
  const tips: string[] = [];

  if (cur) {
    const sr = cur.surplus_rate;
    const surplus = cur.surplus;
    if (surplus < 0) {
      tips.push(
        `⚠️ 你目前入不敷出，每月缺口 ${group(-surplus)} 元。可以从两方面着手：` +
          '一是增收（副业/换岗），二是减支（把「宽裕」档饮食降为「普通」、不养车、搬郊区合租），先把每月成本压到生存底线以内。',
      );
    } else if (sr < 10) {
      tips.push(
        `结余率仅 ${fix0(sr)}%，抗风险能力极弱。建议把饮食/交通降一档，` +
          `目标是月结余率提到 20% 以上（约多存 ${group(cur.cost_total * 0.1)} 元/月）。`,
      );
    } else if (sr < 20) {
      tips.push(`结余率 ${fix0(sr)}%，略低于 20% 健康线。控制人情娱乐、给老家等弹性支出即可达标。`);
    } else {
      tips.push(`✅ 结余率 ${fix0(sr)}%，处于健康区间。可考虑把结余的一部分用于应急金、一部分做长期储备。`);
    }
    if (cur.house_saving_years) {
      const yrs = cur.house_saving_years;
      if (yrs >= 30) {
        tips.push(`按当前结余攒首付需 ${fix0(yrs)} 年，几乎不现实。可考虑：换低成本城市、双收入家庭、或降低购房预期（小户型/远郊）。`);
      }
    }
  }

  // 抗风险（档案存款 + 处境生存底线）
  let savings = 0;
  const rawSav = profile?.savings;
  if (rawSav) {
    const n = Number(rawSav);
    if (!isNaN(n)) savings = n; // 非数字保持 0（对应 Python except）
  }
  if (cur) {
    const baseline = (cur.survival_baseline ?? 0) || 1;
    const months = baseline > 0 ? savings / baseline : 0;
    if (savings < 50000) {
      tips.push(
        `🔴 存款 ${group(savings)} 元偏低：失业仅能撑 ${fix1(months)} 个月，` +
          `一次大病自付（约5-10万）就可能击穿。建议优先攒够 ${group(baseline * 3)} 元（3个月底线）应急金。`,
      );
    } else if (months < 6) {
      tips.push(`应急储备偏薄：失业能撑 ${fix1(months)} 个月，建议攒到 6 个月底线（约 ${group(baseline * 6)} 元）。`);
    }
  }

  // 养娃（三座山文本关键词）
  const childTxt = (ms || {}).child || '';
  if (childTxt.includes('耗尽') || childTxt.includes('入不敷出')) {
    tips.push('养娃成本已接近或超过你的结余能力。建议选普惠路线（公办+基础养育），避免在课外班上过度投入；有伴侣的话按家庭收入评估更现实。');
  }

  // 城市对比
  if (cmp && (cmp.surplus_diff ?? 0) > 0) {
    tips.push(`城市对比显示：移居目标城市后每月结余可增加 ${group(cmp.surplus_diff)} 元，值得一试（尤其对买房年限的改善明显）。`);
  }

  if (!tips.length) tips.push('数据已记录。建议保持稳定储蓄，量入为出，定期用本工具复盘。');
  tips.forEach((t, i) => L.push(`  ${i + 1}. ${t}`));
  L.push('');
  return L;
}

/** 格式化当前时间（对应 Python datetime.now():%Y-%m-%d %H:%M）。 */
export function fmtNow(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** build_full_report：汇总完整报告字符串。nowStr 可注入（对拍用），默认当前时间。 */
export function buildFullReport(profile: any, cur: any, cmp: any, ms: any, nowStr?: string): string {
  const L: string[] = ['＝ 生活成本计算器 · 个人计算结果 ＝'];
  L.push(`生成时间：${nowStr ?? fmtNow(new Date())}`);
  L.push('（所有数字为公开调研的估算中值，仅供了解量级，不作为理财依据。）');
  L.push('');
  L.push('【一、基本档案】');
  L.push(...fmtProfile(profile));
  L.push(...fmtCurrent(cur));
  L.push(...fmtCompare(cmp));
  L.push(...fmtMilestones(ms));
  L.push(...buildAdvice(profile, cur, cmp, ms));
  return L.join('\n');
}
