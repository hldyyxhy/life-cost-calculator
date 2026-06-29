import { useState } from 'react';
import { View, Text, Input, Picker, Switch, Button } from '@tarojs/components';
import { estimateInpatient, buildMedicalPrompt } from '../../core';
import PromptCard from '../../components/PromptCard';
import SmartNote from '../../components/SmartNote';
import './index.scss';

const fmtNum = (n: number): string => {
  const neg = n < 0;
  return (neg ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};
const IDENTITY = ['职工', '居民'];
const REMOTE = ['本地就医', '异地已备案', '异地未备案'];
const REMOTE_KEY = ['none', 'filed', 'unfiled'];

export default function MedicalPage() {
  const [city, setCity] = useState('广州');
  const [idIdx, setIdIdx] = useState(0);
  const [cost, setCost] = useState('50000');
  const [remoteIdx, setRemoteIdx] = useState(0);
  const [retired, setRetired] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [prompt, setPrompt] = useState('');

  return (
    <View className="page">
      <View className="header"><Text className="header-title">医保就医</Text></View>

      <View className="card calc">
        <View className="calc-title">住院报销估算</View>
        <View className="calc-desc">基本医保 + 大病保险 + 异地调整的粗算（未含乙类药自付等细节，以医院结算为准）。</View>
        <View className="input-row"><Text className="label">参保城市</Text><Input className="input" value={city} onInput={(e) => setCity(e.detail.value)} /></View>
        <View className="input-row"><Text className="label">医保类型</Text><Picker mode="selector" range={IDENTITY} value={idIdx} onChange={(e) => setIdIdx(Number(e.detail.value))}><View className="picker">{IDENTITY[idIdx]}</View></Picker></View>
        <View className="input-row"><Text className="label">住院费用</Text><Input className="input" type="digit" value={cost} onInput={(e) => setCost(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">就医方式</Text><Picker mode="selector" range={REMOTE} value={remoteIdx} onChange={(e) => setRemoteIdx(Number(e.detail.value))}><View className="picker">{REMOTE[remoteIdx]}</View></Picker></View>
        <View className="input-row"><Text className="label">是否退休</Text><Switch checked={retired} onChange={(e) => setRetired(e.detail.value)} color="#e8843c" /></View>
        <Button className="btn-primary" onClick={() => { setResult(estimateInpatient(city, IDENTITY[idIdx], Number(cost) || 0, REMOTE_KEY[remoteIdx], retired)); setPrompt(''); }}>估算报销</Button>
        <Button className="btn-ask" onClick={() => setPrompt(buildMedicalPrompt(city, IDENTITY[idIdx], Number(cost) || 0, retired, REMOTE_KEY[remoteIdx]))}>问 AI：医保怎么办最省</Button>
      </View>

      {result && !result.error && (
        <View className="result">
          <View className="card grand">
            <Text className="grand-label">合计报销约</Text>
            <Text className="grand-value good">{fmtNum(result.total_pay)}<Text className="grand-unit"> 元</Text></Text>
            <Text className="grand-sub">报销比 {(result.rate * 100).toFixed(0)}%　个人自付 {fmtNum(result.self_pay)} 元</Text>
          </View>
          <View className="card"><SmartNote text={result.note} /></View>
          <PromptCard prompt={prompt} />
        </View>
      )}
      {result && result.error && <View className="card"><Text className="note bad">{result.error}</Text></View>}
    </View>
  );
}
