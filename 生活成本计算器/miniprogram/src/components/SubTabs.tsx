import { ScrollView, View, Text } from '@tarojs/components';
import './SubTabs.scss';

export default function SubTabs({ tabs, current, onChange }: { tabs: string[]; current: number; onChange: (i: number) => void }) {
  return (
    <View className="sub-tabs-wrap">
      <ScrollView scrollX className="sub-tabs" enhanced showScrollbar={false}>
        {tabs.map((t, i) => (
          <View key={i} className={`sub-tab ${i === current ? 'active' : ''}`} onClick={() => onChange(i)}>
            <Text className="sub-tab-text">{t}</Text>
          </View>
        ))}
      </ScrollView>
      <View className="sub-tabs-hint">›</View>
    </View>
  );
}
