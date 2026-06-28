// PromptCard —— 显示「问 AI」提示词 + 一键复制（各计算页共用）
import { View, Text, Button } from '@tarojs/components';
import Taro from '@tarojs/taro';
import './PromptCard.scss';

export default function PromptCard({ prompt, title = '问 AI 的提示词（点下方复制）' }: { prompt: string; title?: string }) {
  if (!prompt) return null;
  const onCopy = () => {
    Taro.setClipboardData({
      data: prompt,
      success: () => Taro.showToast({ title: '已复制，去问 AI', icon: 'none' }),
    });
  };
  return (
    <View className="prompt-card">
      <View className="pc-title">{title}</View>
      <Text className="pc-text" selectable>{prompt}</Text>
      <Button className="pc-btn" onClick={onCopy}>复制去问 AI</Button>
    </View>
  );
}
