// RichNote —— 渲染 core 返回的 rich[] 段落（{t, tag}），按 tag 着色
// 用于 compareBuyRent/housingFundLoan/rateStressTest/compareCities 的富文本结果
import { View, Text } from '@tarojs/components';
import './RichNote.scss';

const TAG_CLASS: Record<string, string> = {
  h: 'rn-h', big: 'rn-big', bigbad: 'rn-bigbad',
  buy: 'rn-buy', rent: 'rn-rent', warn: 'rn-warn',
  muted: 'rn-muted', normal: 'rn-normal',
};

export default function RichNote({ rich }: { rich: any[] | null | undefined }) {
  if (!rich || !rich.length) return null;
  return (
    <View className="rich-note">
      {rich.map((seg: any, i: number) => (
        <Text key={i} className={`rn-seg ${TAG_CLASS[seg.tag] || 'rn-normal'}`}>{seg.t}</Text>
      ))}
    </View>
  );
}
