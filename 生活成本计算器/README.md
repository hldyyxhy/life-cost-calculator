# 生活成本计算器

> 帮劳动者看清钱去哪了、换城市值不值、三座大山（结婚/养娃/养老）要多少钱。

## 项目概况

面向普通劳动者的生活成本工具，现已覆盖**三端**：

| 端 | 技术栈 | 状态 |
|---|---|---|
| **微信小程序**（主端） | Taro 4 + React + TypeScript | ✅ 10 页全功能 |
| **TS 核心**（共享） | 纯 TypeScript，零依赖 | ✅ 93/93 交叉验证 |
| **Python 桌面**（过渡） | tkinter，零第三方包 | ✅ v1.2 保留 |

## 功能一览（10 页）

1. **我的档案** — 6 组表单（基础/收入/居住/伴侣/家庭/负债），首次向导 7 步分步填写
2. **我现在的处境** — 月结余计算 + 成本构成横条图 + overrides 按实际改 + 白话解读（智能着色）
3. **城市与住房** — 城市对比(7行表+分项明细) / 买vs租 / 公积金额度 / 利率压力测试
4. **人生三座山** — 结婚 / 养娃 / 养老（各自独立计算）
5. **借贷真相** — 真实年化 / 可承受负债 / 雪球雪崩(动态债务) / 以贷养贷 / 债务健康
6. **劳动权益** — 加班费 / 最低工资 / 维权评估 / 失业金 / 工伤 / 4050补贴 / 个税优化
7. **求助与反诈** — 10 类求助场景 + 6 类反诈（生成问 AI 提示词）
8. **医保就医** — 住院报销估算（基本+大病+异地）
9. **长期跟踪** — 趋势柱状图 + 可展开快照（含完整档案） + 单条删除
10. **关于** — 工具箱入口 + 数据说明

## 如何运行

### 微信小程序（主端）
```bash
cd miniprogram
npm install
npm run build:weapp   # 编译到 dist/
```
用微信开发者工具打开 `miniprogram/` 目录，清缓存后编译刷新。

### Python 桌面（过渡保留）
```bash
python main.py        # 或双击 main.py
```
仅 Python 标准库（tkinter），零第三方包。PyInstaller 打包：`pyinstaller build.spec --clean`

### TS 核心（独立验证）
```bash
cd core
npm install
python scripts/export_data.py     # 导出数据 JSON
python scripts/dump_baselines.py  # 生成黄金基准
npm run verify                   # 93/93 交叉验证
```

## 目录结构

```
生活成本计算器/
├── main.py, gui_app.py, gui_widgets.py     # Python 桌面入口
├── cost_data.py, calc_engine.py            # Python 计算逻辑+数据
├── rights_data.py, medical_data.py, relief_data.py  # 各地政策数据
├── profile.py, report.py, tracking.py      # 档案/报告/跟踪
├── pages/                                  # Python 桌面页面
│
├── core/                                   # TS 核心（与 UI 框架无关）
│   ├── src/calc/   (15 个模块)             # 计算逻辑（翻译自 calc_engine）
│   ├── src/data/   (4 个 JSON + TS)        # 数据模型+查询函数
│   ├── src/        (types/fmt/profile/...)  # 类型/格式化/档案/报告/跟踪
│   ├── scripts/    (export_data/dump_baselines)  # 数据导出+基准生成
│   ├── __fixtures__/                        # 93 个黄金用例
│   └── 翻译清单.md                          # Python→TS 翻译图谱
│
├── miniprogram/                            # Taro 小程序
│   ├── src/pages/    (10 页)               # 档案/处境/城市/三座山/借贷/权益/求助/医保/跟踪/关于
│   ├── src/components/ (6 组件)            # SmartNote/RichNote/PromptCard/SubTabs/WizardModal + scss
│   ├── src/core/    (复制自 core/src)     # 编译进小程序的 core 副本
│   ├── config/                             # Taro 编译配置
│   └── package.json                        # Taro4 + React + TS + tsx
│
└── 调研数据/                               # 公开来源调研底稿
```

## 数据来源与可靠性

- 所有数据来自 2023-2026 年公开调研报告（育娲《中国生育成本报告》、国家统计局、北大 CIEFR、国家医保局、人社部、各市统计局等）。
- 完整调研底稿见 `调研数据/` 目录。
- **所有数字均为估算中值**，个体差异可能很大，仅供了解量级与结构，**不作为任何理财、投资或消费决策的依据**。

## 计算模型

采用「基准值 × 城市系数 × 养育档位」模型：
- 城市系数以**三线城市≈全国城镇平均 = 1.0** 为基准（一线2.0/新一线1.5/二线1.2/三线1.0/四线0.82/五线0.70）
- 养育档位系数：普惠1.0、中产2.2、高端4.5（教育/月子高端额外加权）
- 个税按 5000 元起征点 + 七级累进 + 专项附加扣除
- IRR 二分法反算真实年化（复利口径），不是简单的月费率×12
