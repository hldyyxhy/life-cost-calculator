import { useState } from 'react';
import { View, Text, Input, Button } from '@tarojs/components';
import { computeLoanApr, computeAffordableDebt } from '../../core';
import './index.scss';

const fmtNum = (n: number): string => {
  const neg = n < 0;
  return (neg ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};
const levelClass = (level: string) => (level === '正常' ? 'good' : level === '偏高' ? 'warn' : 'bad');

export default function DebtPage() {
  // 反算真实年化
  const [principal, setPrincipal] = useState('10000');
  const [monthly, setMonthly] = useState('900');
  const [periods, setPeriods] = useState('12');
  const [apr, setApr] = useState<any>(null);

  // 可承受负债
  const [surplus, setSurplus] = useState('2000');
  const [aprPct, setAprPct] = useState('18');
  const [periods2, setPeriods2] = useState('24');
  const [aff, setAff] = useState<any>(null);

  const onApr = () => setApr(computeLoanApr(Number(principal) || 0, Number(monthly) || 0, Number(periods) || 0));
  const onAff = () => setAff(computeAffordableDebt(Number(surplus) || 0, (Number(aprPct) || 0) / 100, Number(periods2) || 0));

  return (
    <View className="page">
      <View className="header">
        <Text className="header-title">借贷真相</Text>
      </View>

      {/* 反算真实年化 */}
      <View className="card calc">
        <View className="calc-title">反算真实年化</View>
        <View className="calc-desc">输入借款本金、月还、期数，算出真实年化（IRR 复利口径），识破「月费率 0.7%」话术。</View>
        <View className="input-row">
          <Text className="label">借款本金</Text>
          <Input className="input" type="digit" value={principal} onInput={(e) => setPrincipal(e.detail.value)} />
          <Text className="unit">元</Text>
        </View>
        <View className="input-row">
          <Text className="label">每月还款</Text>
          <Input className="input" type="digit" value={monthly} onInput={(e) => setMonthly(e.detail.value)} />
          <Text className="unit">元</Text>
        </View>
        <View className="input-row">
          <Text className="label">期数</Text>
          <Input className="input" type="number" value={periods} onInput={(e) => setPeriods(e.detail.value)} />
          <Text className="unit">月</Text>
        </View>
        <Button className="btn-primary" onClick={onApr}>反算年化</Button>
        {apr && apr.error && <View className="error">{apr.error}</View>}
        {apr && !apr.error && (
          <View className="result-box">
            <View className="big-line">
              真实年化
              <Text className={`rate rate-${levelClass(apr.level)}`}>{(apr.annual_irr * 100).toFixed(1)}%</Text>
              <Text className={`rate-tag tag-${levelClass(apr.level)}`}>{apr.level}</Text>
            </View>
            <View className="info-row">
              <Text className="info-label">总利息</Text>
              <Text className="info-val">{fmtNum(apr.interest)} 元（占本金 {(apr.interest_ratio * 100).toFixed(0)}%）</Text>
            </View>
            <View className="note">{apr.note}</View>
          </View>
        )}
      </View>

      {/* 可承受负债 */}
      <View className="card calc">
        <View className="calc-title">我能借多少</View>
        <View className="calc-desc">按月结余反算安全负债上限（月还款别超过月结余的一半）。</View>
        <View className="input-row">
          <Text className="label">每月结余</Text>
          <Input className="input" type="digit" value={surplus} onInput={(e) => setSurplus(e.detail.value)} />
          <Text className="unit">元</Text>
        </View>
        <View className="input-row">
          <Text className="label">名义年化</Text>
          <Input className="input" type="digit" value={aprPct} onInput={(e) => setAprPct(e.detail.value)} />
          <Text className="unit">%</Text>
        </View>
        <View className="input-row">
          <Text className="label">期数</Text>
          <Input className="input" type="number" value={periods2} onInput={(e) => setPeriods2(e.detail.value)} />
          <Text className="unit">月</Text>
        </View>
        <Button className="btn-primary" onClick={onAff}>算上限</Button>
        {aff && aff.error && <View className="error">{aff.error}</View>}
        {aff && !aff.error && (
          <View className="result-box">
            <View className="info-row">
              <Text className="info-label">最多能借（激进）</Text>
              <Text className="info-val strong">{fmtNum(aff.max_principal)} 元</Text>
            </View>
            <View className="info-row">
              <Text className="info-label">稳妥档（保守）</Text>
              <Text className="info-val">{fmtNum(aff.safe_principal)} 元</Text>
            </View>
            <View className="note">{aff.note}</View>
          </View>
        )}
      </View>
    </View>
  );
}
