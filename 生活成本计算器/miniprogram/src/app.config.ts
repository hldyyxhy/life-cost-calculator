// 导航对齐 Python 版 gui_app.py 顺序（10 项）：档案→处境→城市住房→三座山→借贷→权益→求助反诈→医保→跟踪→关于
// tabBar 放前 5 项（高频），后 5 项从「关于」工具箱进入
export default defineAppConfig({
  pages: [
    'pages/profile/index',
    'pages/situation/index',
    'pages/compare/index',
    'pages/milestones/index',
    'pages/debt/index',
    'pages/rights/index',
    'pages/help/index',
    'pages/medical/index',
    'pages/tracking/index',
    'pages/about/index',
  ],
  tabBar: {
    color: '#9a8b7a',
    selectedColor: '#e8843c',
    backgroundColor: '#ffffff',
    borderStyle: 'white',
    list: [
      { pagePath: 'pages/profile/index', text: '档案' },
      { pagePath: 'pages/situation/index', text: '处境' },
      { pagePath: 'pages/compare/index', text: '城市' },
      { pagePath: 'pages/milestones/index', text: '三座山' },
      { pagePath: 'pages/about/index', text: '更多' },
    ],
  },
  window: {
    backgroundTextStyle: 'dark',
    navigationBarBackgroundColor: '#FAF4EC',
    navigationBarTitleText: '生活成本计算器',
    navigationBarTextStyle: 'black',
  },
});
