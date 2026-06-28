import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import './index.scss';

// 全部工具入口（core 功能全覆盖）
const TOOLS = [
  { title: '劳动权益', desc: '加班费反算 / 最低工资 / 维权评估', path: '/pages/rights/index' },
  { title: '城市加减法', desc: '换城市值不值', path: '/pages/compare/index' },
  { title: '人生三座山', desc: '一生成本（结婚/养娃/养老）', path: '/pages/milestones/index' },
  { title: '求助与反诈', desc: '出事找谁 / 识破骗局', path: '/pages/help/index' },
  { title: '医保就医', desc: '住院报销估算', path: '/pages/medical/index' },
  { title: '长期跟踪', desc: '结余变化趋势', path: '/pages/tracking/index' },
];

export default function AboutPage() {
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
    </View>
  );
}
