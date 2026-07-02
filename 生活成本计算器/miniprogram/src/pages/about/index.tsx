import { View, Text, Button } from '@tarojs/components';
import Taro, { useShareAppMessage } from '@tarojs/taro';
import './index.scss';

const TOOLS = [
  { title: '借贷真相', desc: '真实年化反算 / 可承受负债', path: '/pages/debt/index' },
  { title: '劳动权益', desc: '加班费 / 最低工资 / 维权', path: '/pages/rights/index' },
  { title: '求助与反诈', desc: '出事找谁 / 识破骗局', path: '/pages/help/index' },
  { title: '医保就医', desc: '住院报销估算', path: '/pages/medical/index' },
  { title: '长期跟踪', desc: '结余变化趋势', path: '/pages/tracking/index' },
];

export default function AboutPage() {
  useShareAppMessage(() => ({ title: '生活成本计算器——看清你的钱花哪了', path: '/pages/situation/index' }));
  return (
    <View className="page">
      <View className="header"><Text className="header-title">更多工具</Text></View>

      <View className="tool-list">
        {TOOLS.map((t, i) => (
          <View className="tool-item" key={i} onClick={() => Taro.navigateTo({ url: t.path })}>
            <View className="tool-info">
              <Text className="tool-title">{t.title}</Text>
              <Text className="tool-desc">{t.desc}</Text>
            </View>
            <Text className="tool-arrow">›</Text>
          </View>
        ))}
      </View>

      <View className="card about">
        <Text className="p">生活成本计算器——帮普通劳动者看清生活成本、识破借贷陷阱、知道自己有哪些权益。</Text>
        <Text className="p muted">所有数字为公开调研中值估算，不作为理财/法律依据。数据来源：人社部、医保局、各地民政/人社（2024–2025）。</Text>
      </View>

      {/* 反馈入口（上线后用 openType=feedback 接微信官方反馈通道，当前先留占位） */}
      <Button className="btn-feedback" openType="feedback">📝 意见反馈（上线后可用）</Button>
    </View>
  );
}
