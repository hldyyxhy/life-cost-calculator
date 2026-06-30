// format.ts —— 共享格式化工具（从各页 tsx 抽取，消除 ~10 处重复）

/** 千分号格式化（null/undefined → '—'） */
export const fmtNum = (n: number): string => {
  if (n === null || n === undefined) return '—';
  const neg = n < 0;
  return (neg ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

/** 变化值格式化（b-a，0 → '—'） */
export const fmtDiff = (a: number, b: number): string => {
  const d = b - a;
  if (d === 0) return '—';
  return (d > 0 ? '+' : '') + fmtNum(d);
};

/** 评级 → CSS class（正常=good/偏高=warn/其他=bad） */
export const levelClass = (level: string): string =>
  level === '正常' ? 'good' : level === '偏高' ? 'warn' : 'bad';
