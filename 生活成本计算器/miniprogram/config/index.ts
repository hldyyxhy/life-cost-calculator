import { defineConfig } from '@tarojs/cli';
import devConfig from './dev';
import prodConfig from './prod';

// Taro4 编译配置（React + webpack5 + sass）
export default defineConfig(async (merge) => {
  const base = {
    projectName: 'shenghuo-miniprogram',
    date: '2026-6-27',
    designWidth: 750,
    deviceRatio: {
      640: 2.34 / 2,
      750: 1,
      375: 2 / 1,
      828: 1.81 / 2,
    },
    sourceRoot: 'src',
    outputRoot: 'dist',
    framework: 'react',
    compiler: { type: 'webpack5', prebundle: { enable: false } },
    cache: { enable: false },
    mini: {
      postcss: {
        pxtransform: { enable: true, config: {} },
      },
    },
    h5: {},
  };
  const envConfig = process.env.NODE_ENV === 'development' ? devConfig : prodConfig;
  return merge(base, envConfig);
});
