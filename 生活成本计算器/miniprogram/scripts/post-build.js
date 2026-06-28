// post-build：Taro 4.2 会生成 app.wxss @import './app-origin.wxss'，但产物缺失（平台 bug）。
// 变通：build 后确保 dist/app-origin.wxss 存在（空文件，微信工具能找到即可）。
const fs = require('fs');
const path = require('path');
const f = path.resolve(__dirname, '..', 'dist', 'app-origin.wxss');
if (!fs.existsSync(f)) {
  fs.writeFileSync(f, '/* app-origin placeholder（Taro 4.2 app-origin.wxss 未生成 bug 的变通） */\n');
  console.log('[post-build] created dist/app-origin.wxss');
}
