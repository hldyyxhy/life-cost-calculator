// PromptCard —— 「问 AI」弹窗（prompt 非空时弹出覆盖层，自管 visible，各页只需传 prompt）
import { useState, useEffect } from 'react';
import { View, Text, Button, ScrollView } from '@tarojs/components';
import Taro from '@tarojs/taro';
import './PromptCard.scss';

export default function PromptCard({ prompt, title = '问 AI 的提示词' }: { prompt: string; title?: string }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    setVisible(!!prompt);
  }, [prompt]);
  if (!visible) return null;

  const onCopy = () => {
    Taro.setClipboardData({
      data: prompt,
      success: () => Taro.showToast({ title: '已复制，去问 AI', icon: 'none' }),
    });
  };

  return (
    <View className="pm-mask" onClick={() => setVisible(false)}>
      <View className="pm-modal" catchMove onClick={(e) => e.stopPropagation()}>
        <View className="pm-header">
          <Text className="pm-title">{title}</Text>
          <Text className="pm-close" onClick={() => setVisible(false)}>✕</Text>
        </View>
        <ScrollView scrollY className="pm-body">
          <Text className="pm-text" selectable>{prompt}</Text>
        </ScrollView>
        <View className="pm-actions">
          <Button className="pm-btn-copy" onClick={onCopy}>复制去问 AI</Button>
        </View>
      </View>
    </View>
  );
}
