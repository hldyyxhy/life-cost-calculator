import { useState } from 'react';
import { View, Text, Button } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { HELP_SCENARIOS, FRAUD_TYPES, buildHelpPrompt, buildAntifraudPrompt } from '../../core';
import './index.scss';

export default function HelpPage() {
  useShareAppMessage(() => ({ title: '生活成本计算器——看清你的钱花哪了', path: '/pages/situation/index' }));
  const [prompt, setPrompt] = useState('');

  const onHelp = (key: string) => setPrompt(buildHelpPrompt(key, ''));
  const onFraud = (key: string) => setPrompt(buildAntifraudPrompt(key, ''));
  const onCopy = () => {
    Taro.setClipboardData({ data: prompt, success: () => Taro.showToast({ title: '已复制，去问 AI', icon: 'none' }) });
  };

  return (
    <View className="page">
      <View className="header"><Text className="header-title">求助与反诈</Text></View>

      <View className="card">
        <View className="section-title">遇到这些事，知道找谁</View>
        <View className="section-desc">点对应的场景，生成一段提示词，复制去问 AI（豆包/Kimi/DeepSeek 等），它会告诉你打什么电话、走什么流程。</View>
        <View className="wall">
          {Object.entries(HELP_SCENARIOS).map(([key, v]: [string, any]) => (
            <View className="wall-btn" key={key} onClick={() => onHelp(key)}>{v.title}</View>
          ))}
        </View>
      </View>

      <View className="card">
        <View className="section-title warn-text">怀疑遇到骗局？</View>
        <View className="section-desc">点你遇到的类型，生成提示词让 AI 帮你判断 + 紧急止损步骤。</View>
        <View className="wall">
          {Object.entries(FRAUD_TYPES).map(([key, v]: [string, any]) => (
            <View className="wall-btn warn" key={key} onClick={() => onFraud(key)}>{v.title}</View>
          ))}
        </View>
      </View>

      {prompt && (
        <View className="card prompt-box">
          <View className="prompt-title">提示词（长按或点下方复制）</View>
          <Text className="prompt-text" selectable>{prompt}</Text>
          <Button className="btn-primary" onClick={onCopy}>复制去问 AI</Button>
        </View>
      )}
    </View>
  );
}
