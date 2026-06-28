import { useState } from 'react';
import { View, Text, Input, Picker, Button } from '@tarojs/components';
import {
  compareCities, compareBuyRent, housingFundLoan, rateStressTest,
  buildComparePrompt, buildBuyRentPrompt, buildFundPrompt, buildRateStressPrompt,
} from '../../core';
import PromptCard from '../../components/PromptCard';
import './index.scss';

const fmtNum = (n: number): string => {
  if (n === null || n === undefined) return '—';
  const neg = n < 0;
  return (neg ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};
const TIERS = ['一线', '新一线', '二线', '三线', '四线', '五线'];

export default function ComparePage() {
  const [prompt, setPrompt] = useState('');

  // ① 城市对比
  const [wage, setWage] = useState('6000');
  const [curIdx, setCurIdx] = useState(2);
  const [tgtIdx, setTgtIdx] = useState(0);
  const [cmp, setCmp] = useState<any>(null);

  // ② 买vs租
  const [brTier, setBrTier] = useState(2);
  const [brYears, setBrYears] = useState('10');
  const [br, setBr] = useState<any>(null);

  // ③ 公积金
  const [gfTier, setGfTier] = useState(2);
  const [gfBalance, setGfBalance] = useState('30000');
  const [gfContrib, setGfContrib] = useState('800');
  const [gf, setGf] = useState<any>(null);

  // ④ 利率压力
  const [rsPrincipal, setRsPrincipal] = useState('500000');
  const [rsRate, setRsRate] = useState('3.45');
  const [rs, setRs] = useState<any>(null);

  return (
    <View className="page">
      <View className="header"><Text className="header-title">城市与住房</Text></View>

      {/* ① 城市对比 */}
      <View className="card calc">
        <View className="calc-title">① 换城市值不值</View>
        <View className="input-row"><Text className="label">月薪</Text><Input className="input" type="digit" value={wage} onInput={(e) => setWage(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">当前城市</Text><Picker mode="selector" range={TIERS} value={curIdx} onChange={(e) => setCurIdx(Number(e.detail.value))}><View className="picker">{TIERS[curIdx]}</View></Picker></View>
        <View className="input-row"><Text className="label">目标城市</Text><Picker mode="selector" range={TIERS} value={tgtIdx} onChange={(e) => setTgtIdx(Number(e.detail.value))}><View className="picker">{TIERS[tgtIdx]}</View></Picker></View>
        <Button className="btn-primary" onClick={() => { setCmp(compareCities(Number(wage) || 0, TIERS[curIdx], TIERS[tgtIdx])); setPrompt(''); }}>开始对比</Button>
        <Button className="btn-ask" onClick={() => setPrompt(buildComparePrompt(TIERS[curIdx], TIERS[tgtIdx], Number(wage) || 0))}>问 AI</Button>
        {cmp && !cmp.error && (
          <View className="result-box">
            <View className={`big-line ${cmp.surplus_diff > 0 ? 'good' : 'bad'}`}>移居后结余{cmp.surplus_diff > 0 ? '增加' : '减少'} {fmtNum(Math.abs(cmp.surplus_diff))} 元/月</View>
            <View className="info-row"><Text className="info-label">{TIERS[curIdx]} 结余</Text><Text className="info-val">{fmtNum(cmp.current.surplus)} 元</Text></View>
            <View className="info-row"><Text className="info-label">{TIERS[tgtIdx]} 结余</Text><Text className="info-val">{fmtNum(cmp.target.surplus)} 元</Text></View>
          </View>
        )}
      </View>

      {/* ② 买 vs 租 */}
      <View className="card calc">
        <View className="calc-title">② 买房还是租房</View>
        <View className="calc-desc">按「房价不变」估算：买房代价≈利息。房价若跌，买房还额外亏。</View>
        <View className="input-row"><Text className="label">城市等级</Text><Picker mode="selector" range={TIERS} value={brTier} onChange={(e) => setBrTier(Number(e.detail.value))}><View className="picker">{TIERS[brTier]}</View></Picker></View>
        <View className="input-row"><Text className="label">对比年限</Text><Input className="input" type="number" value={brYears} onInput={(e) => setBrYears(e.detail.value)} /><Text className="unit">年</Text></View>
        <Button className="btn-primary" onClick={() => { setBr(compareBuyRent(TIERS[brTier], Number(brYears) || 10)); setPrompt(''); }}>算买vs租</Button>
        {br && (
          <View className="result-box">
            <View className={`big-line ${br.diff < 0 ? 'good' : 'bad'}`}>房价不跌时 {br.diff < 0 ? '买房省' : '租房省'} {fmtNum(Math.abs(br.diff))} 元</View>
            <View className="info-row"><Text className="info-label">买房代价(利息)</Text><Text className="info-val">{fmtNum(br.buy_net)} 元</Text></View>
            <View className="info-row"><Text className="info-label">租房代价</Text><Text className="info-val">{fmtNum(br.rent_total)} 元</Text></View>
            <View className="note">{br.note}</View>
            <Button className="btn-ask" onClick={() => setPrompt(buildBuyRentPrompt(TIERS[brTier], Number(brYears) || 10))}>问 AI</Button>
          </View>
        )}
      </View>

      {/* ③ 公积金额度 */}
      <View className="card calc">
        <View className="calc-title">③ 公积金能贷多少</View>
        <View className="input-row"><Text className="label">城市等级</Text><Picker mode="selector" range={TIERS} value={gfTier} onChange={(e) => setGfTier(Number(e.detail.value))}><View className="picker">{TIERS[gfTier]}</View></Picker></View>
        <View className="input-row"><Text className="label">公积金余额</Text><Input className="input" type="digit" value={gfBalance} onInput={(e) => setGfBalance(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">月缴存</Text><Input className="input" type="digit" value={gfContrib} onInput={(e) => setGfContrib(e.detail.value)} /><Text className="unit">元</Text></View>
        <Button className="btn-primary" onClick={() => { setGf(housingFundLoan(TIERS[gfTier], Number(gfBalance) || 0, Number(gfContrib) || 0, 30)); setPrompt(''); }}>算公积金额度</Button>
        {gf && (
          <View className="result-box">
            <View className="big-line">可贷约 <Text className="rate warn">{fmtNum(gf.eligible)}</Text> 元</View>
            <View className="info-row"><Text className="info-label">月供(30年)</Text><Text className="info-val">{fmtNum(gf.monthly)} 元/月</Text></View>
            <View className="info-row"><Text className="info-label">总利息</Text><Text className="info-val">{fmtNum(gf.total_interest)} 元</Text></View>
            <View className="note">{gf.note}</View>
            <Button className="btn-ask" onClick={() => setPrompt(buildFundPrompt(TIERS[gfTier], Number(gfBalance) || 0, Number(gfContrib) || 0))}>问 AI</Button>
          </View>
        )}
      </View>

      {/* ④ 利率压力测试 */}
      <View className="card calc">
        <View className="calc-title">④ 利率涨了月供多多少</View>
        <View className="input-row"><Text className="label">贷款额</Text><Input className="input" type="digit" value={rsPrincipal} onInput={(e) => setRsPrincipal(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">基准年化</Text><Input className="input" type="digit" value={rsRate} onInput={(e) => setRsRate(e.detail.value)} /><Text className="unit">%</Text></View>
        <Button className="btn-primary" onClick={() => { setRs(rateStressTest(Number(rsPrincipal) || 0, (Number(rsRate) || 0) / 100, 30)); setPrompt(''); }}>压力测试</Button>
        {rs && (
          <View className="result-box">
            {rs.rows.map((r: any, i: number) => (
              <View className="info-row" key={i}>
                <Text className="info-label">{(r.rate * 100).toFixed(2)}%{i === 0 ? '（基准）' : i === 1 ? '（+0.5%）' : '（+1%）'}</Text>
                <Text className="info-val">{fmtNum(r.monthly)} 元/月</Text>
              </View>
            ))}
            <View className="note">利率每涨 1%，月供多约 {fmtNum(rs.rows[2].monthly - rs.rows[0].monthly)} 元，30 年多付利息 {fmtNum(rs.rows[2].total_interest - rs.rows[0].total_interest)} 元。</View>
            <Button className="btn-ask" onClick={() => setPrompt(buildRateStressPrompt(Number(rsPrincipal) || 0, (Number(rsRate) || 0) / 100))}>问 AI</Button>
          </View>
        )}
      </View>

      <PromptCard prompt={prompt} />
    </View>
  );
}
