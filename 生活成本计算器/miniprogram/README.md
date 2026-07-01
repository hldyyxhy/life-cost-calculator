# 生活成本计算器 · 微信小程序

Taro 4 + React + TypeScript，复用 `../core/` 的 TS 核心。暖色设计（#e8843c 橙 / #faf4ec 米）。

## 开发

```bash
cd miniprogram
npm install
npm run build:weapp   # 编译到 dist/
# 或 npm run dev:weapp（watch 模式）
```

用微信开发者工具打开 `miniprogram/` 目录（会自动读 `project.config.json` 找到 `dist/`）。
**每次改代码后清缓存**（工具→清除缓存→全部），否则 `n[e] is not a function` / `app-origin.wxss not found`。

## 页面结构（10 页）

```
src/pages/
├── profile/     档案（首次向导 WizardModal + 6 组折叠 + 城市匹配）
├── situation/   处境（成本图 + overrides + SmartNote + 报告）
├── compare/     城市与住房（4 tab SubTabs：对比/买租/公积金/利率）
├── milestones/  三座山（结婚/养娃/养老独立计算）
├── debt/        借贷真相（5 tab SubTabs + 动态债务列表）
├── rights/      劳动权益（7 tab SubTabs）
├── help/        求助与反诈（场景按钮墙 + PromptCard 弹窗）
├── medical/     医保就医（住院报销估算）
├── tracking/    长期跟踪（CSS 柱状图 + 快照展开/删除）
└── about/       关于（工具箱入口 + 数据说明）
```

## 组件

| 组件 | 职责 |
|---|---|
| SmartNote | 纯文本智能着色（行首判定+行内 token，移植 Python RichNote） |
| RichNote | rich[] 段落渲染（按 tag 着色，用于 core 返回的富文本结果） |
| PromptCard | 问 AI 弹窗（自管 visible，遮罩关闭+复制） |
| SubTabs | 横向 tab 切换（ScrollView+受控 scrollLeft，>4 显示 › 提示） |
| WizardModal | 首次向导（7 步+show_if 智能跳过，全屏覆盖） |

## core 接入方式

`src/core/` 是 `../core/src/` 的复制（Taro babel-loader 不编译 core 外部多模块）。修改 core 后需：
```bash
rm -rf src/core && cp -r ../core/src src/core
npm run build:weapp
```

## 共享资源

- `src/styles/_vars.scss` — 暖色变量
- `src/styles/shared.scss` — 各页通用样式（card/btn/input-row/info-row 等）
- `src/utils/format.ts` — fmtNum / fmtDiff / levelClass
- `src/hooks/useProfileSync.ts` — 各页从档案预填的共享 hook
- `src/utils/storage.ts` — ProfileStorage 的 Taro 实现（wx.getStorageSync）
