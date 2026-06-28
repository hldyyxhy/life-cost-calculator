import { useState } from 'react';
import { View, Text, Picker, Switch, Button } from '@tarojs/components';
import { computeLifeCost } from '../../core';
import './index.scss';

const fmtNum = (n: number): string => {
  const neg = n < 0;
  return (neg ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};
const TIERS = ['一线', '新一线', '二线', '三线', '四线', '五线'];
const LEVELS = ['普惠', '中产', '高端'];
const BIRTH = ['公立·顺产', '公立·剖腹产', '私立·顺产', '私立·剖腹产'];
const CARE = ['居家养老', '普惠养老机构', '中高端养老机构'];

export default function MilestonesPage() {
  const [tierIdx, setTierIdx] = useState(2);
  const [levelIdx, setLevelIdx] = useState(0);
  const [birthIdx, setBirthIdx] = useState(0);
  const [careIdx, setCareIdx] = useState(0);
  const [graduate, setGraduate] = useState(false);
  const [result, setResult] = useState<any>(null);

  const onCompute = () => {
    setResult(computeLifeCost(TIERS[tierIdx], LEVELS[levelIdx], BIRTH[birthIdx], CARE[careIdx], '公办', graduate));
  };

  return (
    <View className="page">
      <View className="header"><Text className="header-title">人生三座山</Text></View>

      <View className="card calc">
        <View className="calc-title">一生要花多少钱</View>
        <View className="calc-desc">从怀孕到死亡的一生净成本（含结婚、养娃、养老三大件）。算的是"三线城市·全国城镇平均"为基准，按你选的城市/档次换算。</View>
        <View className="input-row"><Text className="label">城市等级</Text><Picker mode="selector" range={TIERS} value={tierIdx} onChange={(e) => setTierIdx(Number(e.detail.value))}><View className="picker">{TIERS[tierIdx]}</View></Picker></View>
        <View className="input-row"><Text className="label">养育档位</Text><Picker mode="selector" range={LEVELS} value={levelIdx} onChange={(e) => setLevelIdx(Number(e.detail.value))}><View className="picker">{LEVELS[levelIdx]}</View></Picker></View>
        <View className="input-row"><Text className="label">分娩方式</Text><Picker mode="selector" range={BIRTH} value={birthIdx} onChange={(e) => setBirthIdx(Number(e.detail.value))}><View className="picker">{BIRTH[birthIdx]}</View></Picker></View>
        <View className="input-row"><Text className="label">养老方式</Text><Picker mode="selector" range={CARE} value={careIdx} onChange={(e) => setCareIdx(Number(e.detail.value))}><View className="picker">{CARE[careIdx]}</View></Picker></View>
        <View className="input-row"><Text className="label">读研(22-23岁)</Text><Switch checked={graduate} onChange={(e) => setGraduate(e.detail.value)} color="#e8843c" /></View>
        <Button className="btn-primary" onClick={onCompute}>算一生成本</Button>
      </View>

      {result && (
        <View className="result">
          <View className="card grand">
            <Text className="grand-label">一生净成本（已抵减养老金）</Text>
            <Text className="grand-value">{fmtNum(result.grand_total)}<Text className="grand-unit"> 元</Text></Text>
          </View>
          <View className="card stages">
            <View className="stages-title">六个阶段分布</View>
            {result.stage_subtotals.map((s: any, i: number) => (
              <View className="stage-row" key={i}>
                <View className="stage-info"><Text className="stage-name">{s.stage}</Text><Text className="stage-pct">{s.pct}%</Text></View>
                <Text className="stage-amount">{fmtNum(s.amount)} 元</Text>
              </View>
            ))}
          </View>
        </View>
      )}
    </View>
  );
}
