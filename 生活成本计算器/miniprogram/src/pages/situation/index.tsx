import { useState } from 'react';
import { View, Text, Input, Picker, Switch, Button, ScrollView } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import { computeCurrentSituation, loadLastProfile, buildCurrentSituationPrompt } from '../../core';
import { taroStorage } from '../../utils/storage';
import SmartNote from '../../components/SmartNote';
import PromptCard from '../../components/PromptCard';
import './index.scss';

const TIERS = ['一线', '新一线', '二线', '三线', '四线', '五线'];
const HOUSINGS = ['合租单间', '一居室整租', '已购房（还月供）', '与父母同住（免租）'];
const FOODS = ['节俭', '普通', '宽裕'];
const INSURANCES = ['在职（单位缴）', '灵活就业（全自缴）', '不缴社保'];

const fmtNum = (n: number): string => {
  const neg = n < 0;
  return (neg ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

export default function SituationPage() {
  const [age, setAge] = useState('30');
  const [wage, setWage] = useState('6000');
  const [tierIdx, setTierIdx] = useState(2);
  const [housingIdx, setHousingIdx] = useState(0);
  const [foodIdx, setFoodIdx] = useState(1);
  const [hasCar, setHasCar] = useState(false);
  const [insIdx, setInsIdx] = useState(0);
  const [result, setResult] = useState<any>(null);
  const [prompt, setPrompt] = useState('');
  const [overrides, setOverrides] = useState<any>(null);
  // overrides 弹窗
  const [showOv, setShowOv] = useState(false);
  const [ovVals, setOvVals] = useState<Record<string, string>>({});

  useDidShow(() => {
    const p = loadLastProfile(taroStorage);
    if (p) {
      setAge(String(p.age ?? '30'));
      setWage(String(p.wage ?? ''));
      setTierIdx(Math.max(0, TIERS.indexOf(p.tier)));
      setHousingIdx(Math.max(0, HOUSINGS.indexOf(p.housing)));
      setFoodIdx(Math.max(0, FOODS.indexOf(p.food)));
      setHasCar(!!p.has_car);
      setInsIdx(Math.max(0, INSURANCES.indexOf(p.insurance)));
    }
  });

  const buildInput = () => ({
    age: Number(age) || 30, wagePretax: Number(wage) || 0, tier: TIERS[tierIdx],
    housing: HOUSINGS[housingIdx], foodLevel: FOODS[foodIdx], hasCar,
    insuranceMode: INSURANCES[insIdx], overrides: overrides ?? undefined,
  });

  const onCompute = () => { setResult(computeCurrentSituation(buildInput())); setPrompt(''); };

  const onAskAi = () => {
    setPrompt(buildCurrentSituationPrompt(
      Number(age) || 30, TIERS[tierIdx], Number(wage) || 0, INSURANCES[insIdx],
      HOUSINGS[housingIdx], FOODS[foodIdx], hasCar, 0, false, 0,
    ));
  };

  const onOpenOv = () => {
    if (!result?.breakdown) return;
    const vals: Record<string, string> = {};
    Object.entries(result.breakdown).forEach(([k, v]) => { vals[k] = String(v); });
    setOvVals(vals);
    setShowOv(true);
  };

  const onApplyOv = () => {
    const ov: Record<string, number> = {};
    Object.entries(ovVals).forEach(([k, v]) => {
      const n = Number(v);
      if (!isNaN(n)) ov[k] = n;
    });
    setOverrides(ov);
    setResult(computeCurrentSituation({ ...buildInput(), overrides: ov }));
    setShowOv(false);
  };

  const onResetOv = () => {
    setOverrides(null);
    setResult(computeCurrentSituation(buildInput()));
    setShowOv(false);
  };

  const surplusPositive = !!result && result.surplus >= 0;

  return (
    <View className="page">
      <View className="header">
        <Text className="header-title">我现在的处境</Text>
        <Text className="header-link" onClick={() => Taro.switchTab({ url: '/pages/profile/index' })}>档案 ›</Text>
      </View>

      <View className="card form">
        <View className="form-title">我的情况</View>
        <View className="form-row"><Text className="label">年龄</Text><Input className="input" type="number" value={age} onInput={(e) => setAge(e.detail.value)} /></View>
        <View className="form-row"><Text className="label">税前月薪</Text><Input className="input" type="digit" value={wage} onInput={(e) => setWage(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="form-row"><Text className="label">城市等级</Text><Picker mode="selector" range={TIERS} value={tierIdx} onChange={(e) => setTierIdx(Number(e.detail.value))}><View className="picker">{TIERS[tierIdx]}</View></Picker></View>
        <View className="form-row"><Text className="label">住房</Text><Picker mode="selector" range={HOUSINGS} value={housingIdx} onChange={(e) => setHousingIdx(Number(e.detail.value))}><View className="picker">{HOUSINGS[housingIdx]}</View></Picker></View>
        <View className="form-row"><Text className="label">饮食档次</Text><Picker mode="selector" range={FOODS} value={foodIdx} onChange={(e) => setFoodIdx(Number(e.detail.value))}><View className="picker">{FOODS[foodIdx]}</View></Picker></View>
        <View className="form-row"><Text className="label">养车</Text><Switch checked={hasCar} onChange={(e) => setHasCar(e.detail.value)} color="#e8843c" /></View>
        <View className="form-row"><Text className="label">社保</Text><Picker mode="selector" range={INSURANCES} value={insIdx} onChange={(e) => setInsIdx(Number(e.detail.value))}><View className="picker">{INSURANCES[insIdx]}</View></Picker></View>
        <Button className="btn-primary" onClick={onCompute}>算一算</Button>
        <Button className="btn-ask" onClick={onAskAi}>问 AI：我该怎么改善</Button>
      </View>

      {result && (
        <View className="result">
          <View className={`card surplus ${surplusPositive ? 'pos' : 'neg'}`}>
            <Text className="surplus-label">每月结余</Text>
            <Text className="surplus-value">{surplusPositive ? '+' : ''}{fmtNum(result.surplus)}<Text className="surplus-unit"> 元</Text></Text>
            <Text className="surplus-rate">结余率 {result.surplus_rate}%</Text>
          </View>
          <View className="card summary">
            <View className="summary-row"><Text className="summary-label">到手收入</Text><Text className="summary-value">{fmtNum(result.income_net)} 元/月</Text></View>
            <View className="summary-row"><Text className="summary-label">生存成本</Text><Text className="summary-value">{fmtNum(result.cost_total)} 元/月</Text></View>
            <View className="summary-row"><Text className="summary-label">城市生存底线</Text><Text className="summary-value muted">{fmtNum(result.survival_baseline)} 元/月</Text></View>
          </View>
          {/* 成本构成图 + 按实际改 */}
          <View className="card chart">
            <View className="chart-header">
              <Text className="chart-title">成本构成</Text>
              <Text className="chart-edit" onClick={onOpenOv}>✏ 按实际改</Text>
            </View>
            {Object.entries(result.breakdown).map(([cat, amt]: [string, any]) => {
              const pct = result.cost_total > 0 ? (amt / result.cost_total) * 100 : 0;
              return (
                <View className="bar-row" key={cat}>
                  <Text className="bar-label">{cat}</Text>
                  <View className="bar-track"><View className="bar-fill" style={{ width: pct + '%' }} /></View>
                  <Text className="bar-val">{fmtNum(amt)}</Text>
                </View>
              );
            })}
            {overrides && <Text className="ov-note" onClick={onResetOv}>（显示的是你改过的实际值，点此恢复估算）</Text>}
          </View>
          <View className="card detail">
            <View className="detail-title">成本明细</View>
            {result.cost_rows.map((r: any, i: number) => (
              <View className="detail-row" key={i}><Text className="detail-item">{r.item}</Text><Text className="detail-amount">{fmtNum(r.amount)} 元</Text></View>
            ))}
          </View>
          <View className="card interp"><SmartNote text={result.interpretation} /></View>
          <PromptCard prompt={prompt} />
        </View>
      )}

      {/* overrides 弹窗 */}
      {showOv && (
        <View className="ov-mask" onClick={() => setShowOv(false)}>
          <View className="ov-modal" catchMove onClick={(e) => e.stopPropagation()}>
            <View className="ov-title">✏ 按我的实际改</View>
            <Text className="ov-desc">哪项和你实际差得多就改哪项，改完自动重算结余。</Text>
            <ScrollView scrollY className="ov-body">
              {Object.entries(ovVals).map(([k, v]) => (
                <View className="ov-row" key={k}>
                  <Text className="ov-label">{k}</Text>
                  <Input className="ov-input" type="digit" value={v} onInput={(e) => setOvVals({ ...ovVals, [k]: e.detail.value })} />
                </View>
              ))}
            </ScrollView>
            <View className="ov-actions">
              <Button className="ov-btn-reset" onClick={onResetOv}>恢复估算</Button>
              <Button className="ov-btn-apply" onClick={onApplyOv}>确定重算</Button>
            </View>
          </View>
        </View>
      )}
    </View>
  );
}
