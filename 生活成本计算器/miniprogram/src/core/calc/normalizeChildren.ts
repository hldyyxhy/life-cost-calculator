// calc/normalizeChildren.ts —— _normalize_children (calc_engine.py:453)
// 把子女段计数规整成 {段: 人数(>0)}；空且 numChildren>0 时兜底全归「中小学」。
export function normalizeChildrenByAge(
  childrenByAge: Record<string, number> | null | undefined,
  numChildren = 0,
): Record<string, number> {
  const kids: Record<string, number> = {};
  for (const [seg, n] of Object.entries(childrenByAge ?? {})) {
    if (n && n > 0) kids[seg] = n; // Python: if n and n > 0
  }
  if (Object.keys(kids).length === 0 && numChildren && numChildren > 0) {
    return { '中小学（6-18岁）': numChildren };
  }
  return kids;
}
