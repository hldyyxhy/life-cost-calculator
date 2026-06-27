// fmt.ts —— 精确复刻 Python format spec 的数值格式化
// 用于 interpretation 文本严格对拍：任何格式差异都会让长文本不一致。
// 对应：
//   group(x)     ← f"{x:,}" 与 f"{x:,.0f}"（千分号 + 整数；源数据多为 int）
//   signGroup(x) ← f"{x:+,.0f}"（带符号千分号整数）
//   fix0(x)      ← f"{x:.0f}"（0 位小数无千分号）
//   fix1(x)      ← f"{x:.1f}"（1 位小数无千分号）

/** 给整数字符串加千分号（不依赖 toLocaleString，保证小程序环境一致） */
function withCommas(intStr: string): string {
  const neg = intStr.startsWith('-');
  if (neg) intStr = intStr.slice(1);
  let out = '';
  for (let i = 0; i < intStr.length; i++) {
    if (i > 0 && (intStr.length - i) % 3 === 0) out += ',';
    out += intStr[i];
  }
  return (neg ? '-' : '') + out;
}

/** f"{x:,}" / f"{x:,.0f}" —— round 到整数 + 千分号 */
export function group(x: number): string {
  return withCommas(String(Math.round(x)));
}

/** f"{x:+,.0f}" —— 带符号（正/0 加 +，负自带 -）千分号整数 */
export function signGroup(x: number): string {
  const r = Math.round(x);
  return (r >= 0 ? '+' : '') + withCommas(String(r));
}

/** f"{x:.0f}" —— 0 位小数（无千分号） */
export function fix0(x: number): string {
  return String(Math.round(x));
}

/** f"{x:.1f}" —— 1 位小数（无千分号），如 0.8 / 8.0 */
export function fix1(x: number): string {
  const r = Math.round(x * 10) / 10;
  return r.toFixed(1);
}

/** f"{x:.2f}" —— 2 位小数（无千分号），如时薪 34.48 */
export function fix2(x: number): string {
  return (Math.round(x * 100) / 100).toFixed(2);
}

/** f"{ratio:.0%}" —— 百分比 0 位（ratio×100 后 fix0 + %） */
export function pct0(ratio: number): string {
  return fix0(ratio * 100) + '%';
}

/** f"{ratio:.1%}" —— 百分比 1 位 */
export function pct1(ratio: number): string {
  return fix1(ratio * 100) + '%';
}

/** f"{ratio:.2%}" —— 百分比 2 位（如利率 2.85%） */
export function pct2(ratio: number): string {
  return fix2(ratio * 100) + '%';
}

/**
 * f"{x}" 裸插值浮点 —— Python str(float) 对整数浮点保留 ".0"（1.0→"1.0"），
 * 而 JS String(1.0)→"1"。用于直接插 cf / 系数等浮点的文本（饮食 note、assumptions）。
 */
export function pyFloatStr(x: number): string {
  return Number.isInteger(x) ? `${x}.0` : String(x);
}
