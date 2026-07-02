import { useState } from 'react';
import { View, Text, Input, Picker, Switch, Button } from '@tarojs/components';
import { useDidShow } from '@tarojs/taro';
import {
  compareCities, compareBuyRent, housingFundLoan, rateStressTest, loadLastProfile,
  buildComparePrompt, buildBuyRentPrompt, buildFundPrompt, buildRateStressPrompt,
} from '../../core';
import { taroStorage } from '../../utils/storage';
import SubTabs from '../../components/SubTabs';
import SmartNote from '../../components/SmartNote';
import RichNote from '../../components/RichNote';
import { fmtNum } from '../../utils/format';
import { useShareAppMessage } from '@tarojs/taro';
import PromptCard from '../../components/PromptCard';
import './index.scss';

const fmtDiff = (a: number, b: number): string => {
  const d = b - a;
  if (d === 0) return '—';
  return (d > 0 ? '+' : '') + fmtNum(d);
};
import { TIERS } from '../../utils/constants';
const HOUSINGS = ['合租单间', '一居室整租', '已购房（还月供）', '免租'];
const FOODS = ['节俭', '普通', '宽裕'];
const INSURANCES = ['在职（单位缴）', '灵活就业（全自缴）', '不缴社保'];
const TABS = ['①城市对比', '②买vs租', '③公积金', '④利率压力'];

export default function ComparePage() {
  useShareAppMessage(() => ({ title: '生活成本计算器——看清你的钱花哪了', path: '/pages/situation/index' }));
  const [tab, setTab] = useState(0);
  const [prompt, setPrompt] = useState('');

  // ① 城市对比
  const [wage, setWage] = useState('6000');
  const [curIdx, setCurIdx] = useState(2);
  const [tgtIdx, setTgtIdx] = useState(0);
  const [housingIdx, setHousingIdx] = useState(0);
  const [foodIdx, setFoodIdx] = useState(1);
  const [hasCar, setHasCar] = useState(false);
  const [insIdx, setInsIdx] = useState(0);
  const [cmp, setCmp] = useState<any>(null);

  // ② 买vs租 ③ 公积金 ④ 利率
  const [brTier, setBrTier] = useState(2);
  const [brYears, setBrYears] = useState('10');
  const [br, setBr] = useState<any>(null);
  const [gfTier, setGfTier] = useState(2);
  const [gfBalance, setGfBalance] = useState('30000');
  const [gfContrib, setGfContrib] = useState('800');
  const [gf, setGf] = useState<any>(null);
  const [rsPrincipal, setRsPrincipal] = useState('500000');
  const [rsRate, setRsRate] = useState('3.45');
  const [rs, setRs] = useState<any>(null);

  // 从档案预填（各页共享档案）
  useDidShow(() => {
    const p = loadLastProfile(taroStorage);
    if (p) {
      setWage(String(p.wage ?? ''));
      setCurIdx(Math.max(0, TIERS.indexOf(p.tier)));
      setHousingIdx(Math.max(0, HOUSINGS.indexOf(p.housing)));
      setFoodIdx(Math.max(0, FOODS.indexOf(p.food)));
      setHasCar(!!p.has_car);
      setInsIdx(Math.max(0, INSURANCES.indexOf(p.insurance)));
    }
  });

  const onCompare = () => {
    const r = compareCities(Number(wage) || 0, TIERS[curIdx], TIERS[tgtIdx], INSURANCES[insIdx], HOUSINGS[housingIdx], FOODS[foodIdx], hasCar);
    setCmp(r);
    if (r && !r.error) taroStorage.setItem('last_result_compare', JSON.stringify(r));
    setPrompt('');
  };

  // 7 行对比数据
  const cmpRows = cmp ? [
    { label: '到手月薪', a: cmp.current.income_net, b: cmp.target.income_net, unit: '元', goodUp: true },
    { label: '生存成本', a: cmp.current.cost_total, b: cmp.target.cost_total, unit: '元', goodUp: false },
    { label: '月结余', a: cmp.current.surplus, b: cmp.target.surplus, unit: '元', goodUp: true },
    { label: '结余率', a: cmp.current.surplus_rate, b: cmp.target.surplus_rate, unit: '%', goodUp: true },
    { label: '社保月缴', a: cmp.current.social_ins, b: cmp.target.social_ins, unit: '元', goodUp: false },
    { label: '个税', a: cmp.current.tax, b: cmp.target.tax, unit: '元', goodUp: false },
    { label: '攒首付年限', a: cmp.current.house_saving_years ?? 0, b: cmp.target.house_saving_years ?? 0, unit: '年', goodUp: false },
  ] : [];

  return (
    <View className="page">
      <View className="header"><Text className="header-title">城市与住房</Text></View>
      <SubTabs tabs={TABS} current={tab} onChange={setTab} />

      {tab === 0 && (
        <View>
          <View className="card calc">
            <View className="calc-title">对比两个城市的生活成本</View>
            <View className="input-row"><Text className="label">月薪（税前）</Text><Input className="input" type="digit" value={wage} onInput={(e) => setWage(e.detail.value)} /><Text className="unit">元</Text></View>
            <View className="input-row"><Text className="label">方案A（当前）</Text><Picker mode="selector" range={TIERS} value={curIdx} onChange={(e) => setCurIdx(Number(e.detail.value))}><View className="picker">{TIERS[curIdx]}</View></Picker></View>
            <View className="input-row"><Text className="label">方案B（目标）</Text><Picker mode="selector" range={TIERS} value={tgtIdx} onChange={(e) => setTgtIdx(Number(e.detail.value))}><View className="picker">{TIERS[tgtIdx]}</View></Picker></View>
            <View className="input-row"><Text className="label">住房方式</Text><Picker mode="selector" range={HOUSINGS} value={housingIdx} onChange={(e) => setHousingIdx(Number(e.detail.value))}><View className="picker">{HOUSINGS[housingIdx]}</View></Picker></View>
            <View className="input-row"><Text className="label">饮食档次</Text><Picker mode="selector" range={FOODS} value={foodIdx} onChange={(e) => setFoodIdx(Number(e.detail.value))}><View className="picker">{FOODS[foodIdx]}</View></Picker></View>
            <View className="input-row"><Text className="label">有车</Text><Switch checked={hasCar} onChange={(e) => setHasCar(e.detail.value)} color="#e8843c" /></View>
            <View className="input-row"><Text className="label">社保</Text><Picker mode="selector" range={INSURANCES} value={insIdx} onChange={(e) => setInsIdx(Number(e.detail.value))}><View className="picker">{INSURANCES[insIdx]}</View></Picker></View>
            <Button className="btn-primary" onClick={onCompare}>▶ 开始对比</Button>
          </View>

          {cmp && !cmp.error && (
            <View>
              {/* 7 行对比表 */}
              <View className="card">
                <View className="cmp-table-header">
                  <Text className="cmp-col-item">项目</Text>
                  <Text className="cmp-col-val">{TIERS[curIdx]}</Text>
                  <Text className="cmp-col-diff">变化</Text>
                  <Text className="cmp-col-val">{TIERS[tgtIdx]}</Text>
                </View>
                {cmpRows.map((r, i) => {
                  const diff = r.b - r.a;
                  const isGood = diff !== 0 && (r.goodUp ? diff > 0 : diff < 0);
                  const isBad = diff !== 0 && !isGood;
                  return (
                    <View className="cmp-table-row" key={i}>
                      <Text className="cmp-col-item">{r.label}</Text>
                      <Text className="cmp-col-val">{fmtNum(r.a)}{r.unit}</Text>
                      <Text className={`cmp-col-diff ${isGood ? 'good' : isBad ? 'bad' : ''}`}>{fmtDiff(r.a, r.b)}</Text>
                      <Text className="cmp-col-val">{fmtNum(r.b)}{r.unit}</Text>
                    </View>
                  );
                })}
              </View>

              {/* 分项成本对比明细 */}
              <View className="card">
                <View className="detail-title">分项成本对比</View>
                <View className="cmp-table-header">
                  <Text className="cmp-col-item">项目</Text>
                  <Text className="cmp-col-val">{TIERS[curIdx]}</Text>
                  <Text className="cmp-col-diff">变化</Text>
                  <Text className="cmp-col-val">{TIERS[tgtIdx]}</Text>
                </View>
                {cmp.current.cost_rows.map((cr: any, i: number) => {
                  const bItem = cmp.target.cost_rows.find((x: any) => x.item === cr.item);
                  const bAmt = bItem ? bItem.amount : 0;
                  return (
                    <View className="cmp-table-row" key={i}>
                      <Text className="cmp-col-item">{cr.item}</Text>
                      <Text className="cmp-col-val">{fmtNum(cr.amount)}</Text>
                      <Text className={`cmp-col-diff ${(bAmt - cr.amount) < 0 ? 'good' : (bAmt - cr.amount) > 0 ? 'bad' : ''}`}>{fmtDiff(cr.amount, bAmt)}</Text>
                      <Text className="cmp-col-val">{fmtNum(bAmt)}</Text>
                    </View>
                  );
                })}
              </View>

              {/* 结论 */}
              <View className="card">
                <View className="detail-title">结论</View>
                <RichNote rich={cmp.rich} />
              </View>

              <Button className="btn-ask" onClick={() => setPrompt(buildComparePrompt(TIERS[curIdx], TIERS[tgtIdx], Number(wage) || 0))}>问 AI：具体两城怎么选</Button>
            </View>
          )}
        </View>
      )}

      {tab === 1 && (
        <View className="card calc">
          <View className="calc-title">买房还是租房</View>
          <View className="calc-desc">房价不变估算：买房代价≈利息。房价若跌额外亏。</View>
          <View className="input-row"><Text className="label">城市等级</Text><Picker mode="selector" range={TIERS} value={brTier} onChange={(e) => setBrTier(Number(e.detail.value))}><View className="picker">{TIERS[brTier]}</View></Picker></View>
          <View className="input-row"><Text className="label">对比年限</Text><Input className="input" type="number" value={brYears} onInput={(e) => setBrYears(e.detail.value)} /><Text className="unit">年</Text></View>
          <Button className="btn-primary" onClick={() => { setBr(compareBuyRent(TIERS[brTier], Number(brYears) || 10)); setPrompt(''); }}>算买vs租</Button>
          {br && (
            <View className="result-box">
              <View className={`big-line ${br.diff < 0 ? 'good' : 'bad'}`}>房价不跌时 {br.diff < 0 ? '买房省' : '租房省'} {fmtNum(Math.abs(br.diff))} 元</View>
              <RichNote rich={br.rich} />
              <Button className="btn-ask" onClick={() => setPrompt(buildBuyRentPrompt(TIERS[brTier], Number(brYears) || 10))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      {tab === 2 && (
        <View className="card calc">
          <View className="calc-title">公积金能贷多少</View>
          <View className="input-row"><Text className="label">城市等级</Text><Picker mode="selector" range={TIERS} value={gfTier} onChange={(e) => setGfTier(Number(e.detail.value))}><View className="picker">{TIERS[gfTier]}</View></Picker></View>
          <View className="input-row"><Text className="label">公积金余额</Text><Input className="input" type="digit" value={gfBalance} onInput={(e) => setGfBalance(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">月缴存</Text><Input className="input" type="digit" value={gfContrib} onInput={(e) => setGfContrib(e.detail.value)} /><Text className="unit">元</Text></View>
          <Button className="btn-primary" onClick={() => { setGf(housingFundLoan(TIERS[gfTier], Number(gfBalance) || 0, Number(gfContrib) || 0, 30)); setPrompt(''); }}>算额度</Button>
          {gf && (
            <View className="result-box">
              <View className="big-line">可贷 <Text className="rate warn">{fmtNum(gf.eligible)}</Text> 元</View>
              <View className="info-row"><Text className="info-label">月供</Text><Text className="info-val">{fmtNum(gf.monthly)} 元</Text></View>
              <RichNote rich={gf.rich} />
              <Button className="btn-ask" onClick={() => setPrompt(buildFundPrompt(TIERS[gfTier], Number(gfBalance) || 0, Number(gfContrib) || 0))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      {tab === 3 && (
        <View className="card calc">
          <View className="calc-title">利率涨了月供多多少</View>
          <View className="input-row"><Text className="label">贷款额</Text><Input className="input" type="digit" value={rsPrincipal} onInput={(e) => setRsPrincipal(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">基准年化</Text><Input className="input" type="digit" value={rsRate} onInput={(e) => setRsRate(e.detail.value)} /><Text className="unit">%</Text></View>
          <Button className="btn-primary" onClick={() => { setRs(rateStressTest(Number(rsPrincipal) || 0, (Number(rsRate) || 0) / 100, 30)); setPrompt(''); }}>压力测试</Button>
          {rs && (
            <View className="result-box">
              {rs.rows.map((r: any, i: number) => (
                <View className="info-row" key={i}><Text className="info-label">{(r.rate * 100).toFixed(2)}%{i === 0 ? ' 基准' : i === 1 ? ' +0.5%' : ' +1%'}</Text><Text className="info-val">{fmtNum(r.monthly)} 元/月</Text></View>
              ))}
              <RichNote rich={rs.rich} />
              <Button className="btn-ask" onClick={() => setPrompt(buildRateStressPrompt(Number(rsPrincipal) || 0, (Number(rsRate) || 0) / 100))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      <PromptCard prompt={prompt} />
    </View>
  );
}
