// SubTabs —— 横向 tab 切换（用于计算器多的页面，替代一长条滚动）
import { ScrollView, View, Text } from '@tarojs/components';
import './SubTabs.scss';

export default function SubTabs({ tabs, current, onChange }: { tabs: string[]; current: number; onChange: (i: number) => void }) {
  return (
    <ScrollView scrollX className="sub-tabs" enhanced showScrollbar={false}>
      {tabs.map((t, i) => (
        <View key={i} className={`sub-tab ${i === current ? 'active' : ''}`} onClick={() => onChange(i)}>
          <Text className="sub-tab-text">{t}</Text>
        </View>
      ))}
    </ScrollView>
  );
}
