// calc/money.ts —— _money (calc_engine.py:1929)：金额简写，供结果富文本段落用。
import { fix1, group } from '../fmt';

/** ≥1 万显示 'X.X 万'，否则 'X,XXX 元'。 */
export function moneyFmt(x: number): string {
  return Math.abs(x) >= 10000 ? `${fix1(x / 10000)} 万` : `${group(x)} 元`;
}
