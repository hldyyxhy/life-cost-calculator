export default defineAppConfig({
  pages: ['pages/situation/index', 'pages/profile/index', 'pages/debt/index', 'pages/about/index', 'pages/rights/index', 'pages/compare/index', 'pages/milestones/index', 'pages/help/index', 'pages/medical/index', 'pages/tracking/index'],
  tabBar: {
    color: '#9a8b7a',
    selectedColor: '#e8843c',
    backgroundColor: '#ffffff',
    borderStyle: 'white',
    list: [
      { pagePath: 'pages/situation/index', text: '处境' },
      { pagePath: 'pages/profile/index', text: '档案' },
      { pagePath: 'pages/debt/index', text: '借贷' },
      { pagePath: 'pages/about/index', text: '关于' },
    ],
  },
  window: {
    backgroundTextStyle: 'dark',
    navigationBarBackgroundColor: '#FAF4EC',
    navigationBarTitleText: '生活成本计算器',
    navigationBarTextStyle: 'black',
  },
});
