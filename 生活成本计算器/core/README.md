# cost-calc-core —— 生活成本计算器 TypeScript 核心

把 Python 版（`../calc_engine.py` 等）的计算逻辑翻译成 **与 UI 框架无关的 TypeScript 纯核心**，未来供微信小程序 / Web / 桌面复用。计算全部在端侧跑（离线秒算）。

## 目录

```
src/
  types.ts                 类型定义
  data/cost.ts             读 cost.json + 批次0逻辑函数（城市系数/个税等）
  data/cost.json           export_data.py 导出的常量
  calc/normalizeChildren.ts
  calc/survival.ts
  calc/interpretation.ts
  calc/situation.ts        处境页主入口 computeCurrentSituation
  index.ts                 barrel 导出
scripts/
  export_data.py           导出 Python 数据模块为 JSON
  dump_baselines.py        dump 黄金用例完整返回 → __fixtures__
  verify.ts                交叉验证：TS 输出 vs Python 基准
__fixtures__/              黄金基准（提交进仓库）
```

## 工作流

```bash
npm install                       # 首次
python scripts/export_data.py     # 生成 src/data/*.json
python scripts/dump_baselines.py  # 生成 __fixtures__/*.json（黄金基准）
npm run verify                    # TS 翻译输出 vs Python 基准逐字段对拍
npm run typecheck                 # 类型检查
```

## 交叉验证容差

- 金额 ≤1 元（Python `round` 银行家舍入 vs JS `Math.round` 差异兜底）
- `interpretation` 文本**严格相等**（最强回归捕捉器）
- 结构字段 `deepStrictEqual`

详见 `../翻译清单.md` 与 `../多端迁移方案.md`。
