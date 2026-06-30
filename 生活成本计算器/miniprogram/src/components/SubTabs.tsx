import { View, Text } from '@tarojs/components';
import './SubTabs.scss';

export default function SubTabs({ tabs, current, onChange }: { tabs: string[]; current: number; onChange: (i: number) => void }) {
  return (
    <View className="sub-tabs-wrap">
      {/* 用 CSS overflow 代替 ScrollView——不受 React 重渲染影响，点 tab 后滚动位置不重置 */}
      <View className="sub-tabs-scroll">
        {tabs.map((t, i) => (
          <View key={i} className={`sub-tab ${i === current ? 'active' : ''}`} onClick={() => onChange(i)}>
            <Text className="sub-tab-text">{t}</Text>
          </View>
        ))}
      </View>
      <View className="sub-tabs-hint">›</View>
    </View>
  );
}
