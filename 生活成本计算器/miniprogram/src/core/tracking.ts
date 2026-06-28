// tracking.ts —— 长期跟踪数据层（翻译自 tracking.py 的纯逻辑部分）
// metricsFrom/renderTxt/safeName/toNum。文件 I/O 留 UI 层注入 storage。
import { computeCurrentSituation } from './calc/situation';
import { group, signGroup, fix0 } from './fmt';

/** entry 空串/None/异常 → default。对应 _to_num。 */
export function toNum(v: any, def: number = 0): number {
  if (v === '' || v === null || v === undefined) return def;
  const n = typeof v === 'number' ? v : parseFloat(v);
  return isNaN(n) ? def : n;
}

/** 姓名 → 安全文件名片段（去非法字符）；空则默认。对应 _safe_name。 */
export function safeName(name: string): string {
  const s = (name ?? '').trim().replace(/[\/\\:*?"<>|]/g, '');
  return s || '我的档案';
}

export interface Metrics {
  surplus: number;
  savings: number;
  cost_total: number;
  debt_monthly: number;
  surplus_rate: number;
}

/** metrics_from：从档案 + 处境页结果提取 5 项跟踪指标。last_result 优先。 */
export function metricsFrom(profile: any, lastResult?: any): Metrics {
  const p = profile || {};
  let surplus: number;
  let cost_total: number;
  let surplus_rate: number;
  if (lastResult && typeof lastResult === 'object' && 'surplus' in lastResult) {
    surplus = lastResult.surplus ?? 0;
    cost_total = lastResult.cost_total ?? 0;
    surplus_rate = lastResult.surplus_rate ?? 0;
  } else {
    try {
      const r: any = computeCurrentSituation({
        age: p.age ?? 30,
        wagePretax: toNum(p.wage, 8000),
        tier: p.tier ?? '三线',
        housing: p.housing ?? '合租单间',
        foodLevel: p.food ?? '普通',
        hasCar: p.has_car ?? false,
        insuranceMode: p.insurance ?? '在职（单位缴）',
        numChildren: p.num_children ?? 0,
        supportElderly: p.support_elderly ?? false,
        supportFamilyMonthly: toNum(p.support_family),
      });
      surplus = r.surplus ?? 0;
      cost_total = r.cost_total ?? 0;
      surplus_rate = r.surplus_rate ?? 0;
    } catch (e) {
      surplus = cost_total = surplus_rate = 0;
    }
  }
  const savings = toNum(p.savings);
  const debt_monthly = toNum(p.mortgage_monthly) + toNum(p.car_loan_monthly);
  return {
    surplus: Math.round(surplus),
    savings: Math.round(savings),
    cost_total: Math.round(cost_total),
    debt_monthly: Math.round(debt_monthly),
    surplus_rate: Math.round(surplus_rate * 10) / 10,
  };
}

/** render_txt：生成人读文本档案（标题 + 逐条 5 项数值）。 */
export function renderTxt(name: string, snapshots: any[]): string {
  const lines = [`长期跟踪档案 · ${name}`, '='.repeat(40)];
  if (!snapshots.length) lines.push('（暂无记录）');
  for (const s of snapshots) {
    const m = s.metrics || {};
    const sp = m.surplus ?? 0;
    const sp_s = sp ? signGroup(sp) : '0'; // f"{sp:+,.0f}" if sp else "0"
    lines.push(
      '',
      s.time ?? '',
      `  月结余: ${sp_s} 元    存款: ${group(m.savings ?? 0)} 元    月度成本: ${group(m.cost_total ?? 0)} 元`,
      `  月负债: ${group(m.debt_monthly ?? 0)} 元    结余率: ${fix0(m.surplus_rate ?? 0)}%`,
    );
  }
  lines.push('', '='.repeat(40), `共 ${snapshots.length} 次记录`);
  return lines.join('\n');
}
