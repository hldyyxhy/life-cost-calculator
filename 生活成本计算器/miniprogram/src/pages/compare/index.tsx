import { useState } from 'react';
import { View, Text, Input, Picker, Button } from '@tarojs/components';
import { compareCities, buildComparePrompt } from '../../core';
import PromptCard from '../../components/PromptCard';
import './index.scss';

const fmtNum = (n: number): string => {
  const neg = n < 0;
  return (neg ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};
const TIERS = ['一线', '新一线', '二线', '三线', '四线', '五线'];

export default function ComparePage() {
  const [wage, setWage] = useState('6000');
  const [curIdx, setCurIdx] = useState(2);
  const [tgtIdx, setTgtIdx] = useState(0);
  const [result, setResult] = useState<any>(null);
  const [prompt, setPrompt] = useState('');

  const onCompare = () => { setResult(compareCities(Number(wage) || 0, TIERS[curIdx], TIERS[tgtIdx])); setPrompt(''); };
  const onAskAi = () => setPrompt(buildComparePrompt(TIERS[curIdx], TIERS[tgtIdx], Number(wage) || 0));
  const diffPositive = !!result && result.surplus_diff > 0;

  return (
    <View className="page">
      <View className="header"><Text className="header-title">城市加减法</Text></View>

      <View className="card calc">
        <View className="calc-title">换城市值不值</View>
        <View className="calc-desc">对比当前城市与目标城市的成本、收入、结余。目标工资按比例估算。</View>
        <View className="input-row"><Text className="label">现在月薪</Text><Input className="input" type="digit" value={wage} onInput={(e) => setWage(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">当前城市</Text><Picker mode="selector" range={TIERS} value={curIdx} onChange={(e) => setCurIdx(Number(e.detail.value))}><View className="picker">{TIERS[curIdx]}</View></Picker></View>
        <View className="input-row"><Text className="label">目标城市</Text><Picker mode="selector" range={TIERS} value={tgtIdx} onChange={(e) => setTgtIdx(Number(e.detail.value))}><View className="picker">{TIERS[tgtIdx]}</View></Picker></View>
        <Button className="btn-primary" onClick={onCompare}>开始对比</Button>
        <Button className="btn-ask" onClick={onAskAi}>问 AI：具体两城怎么选</Button>
      </View>

      {result && !result.error && (
        <View className="result">
          <View className={`card surplus ${diffPositive ? 'pos' : 'neg'}`}>
            <Text className="surplus-label">移居后每月结余变化</Text>
            <Text className="surplus-value">{diffPositive ? '+' : ''}{fmtNum(result.surplus_diff)}<Text className="surplus-unit"> 元</Text></Text>
          </View>
          <View className="card compare-detail">
            {result.comparison_text.split('\n').map((ln: string, i: number) => (
              <Text className="cmp-line" key={i}>{ln || ' '}</Text>
            ))}
          </View>
          <View className="card cmp-grid">
            <View className="cmp-col">
              <Text className="cmp-col-title">{TIERS[curIdx]}（当前）</Text>
              <Text className="cmp-row">到手 {fmtNum(result.current.income_net)}</Text>
              <Text className="cmp-row">成本 {fmtNum(result.current.cost_total)}</Text>
              <Text className="cmp-row">结余 {fmtNum(result.current.surplus)}</Text>
            </View>
            <View className="cmp-col">
              <Text className="cmp-col-title">{TIERS[tgtIdx]}（目标）</Text>
              <Text className="cmp-row">到手 {fmtNum(result.target.income_net)}</Text>
              <Text className="cmp-row">成本 {fmtNum(result.target.cost_total)}</Text>
              <Text className="cmp-row">结余 {fmtNum(result.target.surplus)}</Text>
            </View>
          </View>
          <PromptCard prompt={prompt} />
        </View>
      )}
    </View>
  );
}
