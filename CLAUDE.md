# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**生活成本计算器** — 一个面向普通劳动者的桌面工具（Python/tkinter，零第三方依赖）。帮助用户看清生活成本、换城市值不值、结婚养娃养老要多少钱。

**入口**：`生活成本计算器/main.py`（双击运行或 `python main.py`）

## 架构分层

```
main.py → gui_app.py (主窗口+导航)
              ├── pages/page_profile.py   — "我的档案"（用户信息表单）
              ├── pages/page_current.py   — "我现在的处境"（月结余计算）
              ├── pages/page_compare.py   — "城市加减法"（城市对比）
              ├── pages/page_milestones.py— "人生三座山"（结婚/养娃/养老）
              ├── pages/page_rights.py    — "劳动权益"（加班费/失业金/4050/工伤）
              ├── pages/page_debt.py      — "借贷真相"（真实年化/还款方案）
              ├── pages/page_help.py      — "求助渠道"（出事找谁的问AI按钮墙）
              └── pages/page_about.py     — 关于与数据说明
调用关系：
    calc_engine.py  ← 纯函数计算逻辑（无tkinter依赖，可 unittest 单独测）
    cost_data.py    ← 底层数据模型（城市分级、成本基准、系数）
    rights_data.py  ← 劳动权益/救助类补充数据（最低工资、失业金、4050、工伤）
    profile.py      ← 用户档案数据模型（FIELD_DEFS + JSON序列化）
    gui_widgets.py  ← 可复用 GUI 组件（CardFrame、ProportionBars、open_prompt_dialog）
    report.py       ← 综合报告生成（纯函数）
```

## 核心设计模式

### 1. "纯函数 + page 模式" 新增功能
所有计算逻辑写在 `calc_engine.py` 的纯函数里（输入→dict输出，无副作用），GUI 页面的 `on_compute()` 调用它并渲染结果。新增计算模块时：
1. `calc_engine.py` 加纯函数
2. `pages/page_xxx.py` 加 GUI 页面
3. 在 `gui_app.py` 注册导航按钮+创建页面

### 2. 数据模型：基准值 × 城市系数 × 养育档位
```
实际成本 = 三线基准值 × COST_FACTOR[tier] × RAISE_LEVELS[level].factor
```
- 6 个城市等级（一线/新一线/二线/三线/四线/五线），系数见 `cost_data.py`
- 3 个养育档位（普惠/中产/高端），系数见 `cost_data.py`
- `cost_data.py` 提供 `city_to_tier(city_name)` 反向映射（335个城市）

### 3. 用户档案同步机制
`profile.py` 的 `FIELD_DEFS` 定义表单字段（基本/收入/居住/伴侣/家庭/负债6组）→ `page_profile.py` 自动渲染 → 用户点「确定」→ 调用各页面的 `apply_profile(prof)` 方法同步数据。
- 所有支持档案同步的页面必须实现 `apply_profile(self, prof)` 方法
- 同步目标在 `page_profile.on_apply()` 的 `targets` 列表中注册

### 4. "问 AI" 提示词生成
每个功能卡片底部都有一个「生成问 AI 的提示词」按钮 → 调用 `calc_engine.py` 的 `build_*_prompt()` 函数，把用户输入的字段填充到结构化提示词中 → 弹出 `gui_widgets.open_prompt_dialog()` 让用户一键复制去问 AI。
- 城市信息通过 `initial_city=self._profile_city` 预填到弹窗
- `build_fn(city_var.get().strip())` 确保城市名进入提示词正文

### 5. 劳动权益补充数据
`rights_data.py` 是 `cost_data.py` 的补充，包含需联网检索的各地政策数据：
- `PROVINCE_MIN_WAGE` — 31省最低工资
- `UNEMPLOYMENT_INSURANCE` — 失业保险金标准
- `FLEXIBLE_SUBSIDY_PROVINCE` — 4050社保补贴
- `PROVINCE_INJURY_EXTRA` — 工伤一次性补助金各省差异
- `CITY_TO_PROVINCE` — 城市→省份映射（80+城市）
- 工具函数如 `estimate_unemployment_pay()`, `unemploy_duration()`, `calc_injury_one_time()`

## 关键数据流

```
用户填档案 → profile.json（JSON 序列化）
                  ↕
page_profile.on_apply()
    → 遍历 targets：pg.apply_profile(prof)
        → 其他页面填充各自表单字段
        → rights_data 函数提供各省精确标准
用户点"算一算" → calc_engine 纯函数 → dict 结果 → GUI 渲染
用户点"问 AI" → build_*_prompt() 填充数据 → open_prompt_dialog() 弹窗
```

## 文件说明

| 文件 | 职责 | 规模 |
|------|------|------|
| `calc_engine.py` | 全部计算逻辑（纯函数，30+个函数） | ~1900行 |
| `cost_data.py` | 城市分级/成本基准/系数/335城映射 | ~500行 |
| `rights_data.py` | 劳动权益补充数据（最低工资/失业金/4050/工伤） | ~580行 |
| `gui_widgets.py` | 可复用 GUI 组件 + 样式 + 提示词弹窗 | ~480行 |
| `gui_app.py` | 主窗口（导航+页面切换） | ~120行 |
| `profile.py` | 用户档案数据模型 + auto_map_tier | ~170行 |
| `report.py` | 综合报告生成（纯函数） | ~160行 |

## 运行方式

```bash
# 从项目目录运行
python main.py

# 或直接双击 main.py（确保 Python 已关联 .py 文件）
```

**依赖**：仅 Python 标准库（tkinter），零第三方包。

## 目录结构

```
生活成本计算器/
├── main.py, gui_app.py, gui_widgets.py
├── cost_data.py, calc_engine.py, rights_data.py
├── profile.py, report.py
├── pages/          — 每个功能一个独立页面
└── 功能改进计划.md

调研数据/           — 调研底稿（公开来源，仅供参考）
├── 01_城市分级体系.md ... 07_待补数据清单.md
```

## 微信小程序平台思维

微信小程序平台以 Bug 多、官方维护不足而"闻名"。在调试时，应始终把"平台本身存在问题"作为一个重要假设，而不是最后才考虑的可能性。

### 默认的调试思路

1. 在假设是我们代码出错之前，先问：这种行为是否符合已知的微信平台 Bug 或限制？
2. 优先搜索已有问题：社区论坛（v2ex、掘金、segmentfault）、Taro 的 GitHub issues，以及微信开放社区（developers.weixin.qq.com）——很多官方 Bug 报告多年都没有解决。
3. 如果行为无法解释、只在特定环境出现（例如 iOS vs Android、开发者工具 vs 真机），或者难以稳定复现——应高度怀疑是平台 Bug。

### 微信平台已知的不可靠类别

- **iOS 与 Android 差异**：CSS 渲染、JS 引擎行为、API 返回值在两端经常不同，必须同时测试。
- **开发者工具 vs 真机**：开发者工具基于 Chromium，而真机使用定制 JS 引擎（Android 为 V8，iOS 为 JavaScriptCore）。很多问题只会在真机上出现。
- **API 不一致**：同一个 API 在不同基础库版本下，返回结构或错误码可能不同。不要盲信文档——一定要以实际行为为准。
- **基础库版本碎片化**：用户可能使用不同版本的基础库。在某个版本修复的问题，可能在另一个版本出现新的问题。
- **分包 / 异步加载问题**：分包加载、预加载、独立分包存在已知的竞态条件和生命周期 Bug。
- **Canvas / WebGL**：非常脆弱，在不同设备和系统版本之间存在渲染差异。
- **存储与文件系统 API**：配额限制、错误码和异步行为不一致。

### 以变通方案为先的文化

一旦确认或怀疑是平台 Bug，目标应是找到可行的变通方案，而不是等待官方修复（大概率不会发生）。同时，应在代码注释以及 `.claude/skills/` 中记录该变通方案及推测的根本原因。

> 小程序相关代码在 `生活成本计算器/miniprogram/`（Taro4 + React + TS，复用 `生活成本计算器/core/` 的 TS 核心）。core 通过 esbuild 预打包成单文件 `core.bundle.js` 接入，规避 Taro 编译 core 多模块时的 chunk/`Page has not been registered` 问题（详见记忆 miniprogram-ui）。
