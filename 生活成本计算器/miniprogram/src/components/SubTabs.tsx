import { useState } from 'react';
import { ScrollView, View, Text } from '@tarojs/components';
import './SubTabs.scss';

export default function SubTabs({ tabs, current, onChange }: { tabs: string[]; current: number; onChange: (i: number) => void }) {
  // 受控 scrollLeft：onScroll 记录位置，current 变化重渲染时恢复——
  // 解决 ScrollView 重渲染 scrollLeft 重置到 0 的平台行为
  const [scrollLeft, setScrollLeft] = useState(0);

  // tab 数 ≤4 时不显示右滑提示（4 个能放下，不需要拖动）
  const showHint = tabs.length > 4;

  return (
    <View className="sub-tabs-wrap">
      <ScrollView
        scrollX
        scrollLeft={scrollLeft}
        scrollWithAnimation={false}
        onScroll={(e) => {
          const left = e.detail.scrollLeft;
          if (Math.abs(left - scrollLeft) > 3) setScrollLeft(left);
        }}
        className="sub-tabs"
        enhanced
        showScrollbar={false}
      >
        {tabs.map((t, i) => (
          <View key={i} className={`sub-tab ${i === current ? 'active' : ''}`} onClick={() => onChange(i)}>
            <Text className="sub-tab-text">{t}</Text>
          </View>
        ))}
      </ScrollView>
      {showHint && <View className="sub-tabs-hint">›</View>}
    </View>
  );
}
