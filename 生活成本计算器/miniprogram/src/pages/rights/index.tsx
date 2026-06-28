import { useState } from 'react';
import { View, Text, Input, Picker, Switch, Button } from '@tarojs/components';
import { computeOvertimePay, computeMinWageCheck, assessOvertimeClaim } from '../../core';
import './index.scss';

const fmtNum = (n: number): string => {
  const neg = n < 0;
  return (neg ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};
const TIERS = ['一线', '新一线', '二线', '三线', '四线', '五线'];
const EVIDENCE = ['充分', '部分', '几乎没有'];

export default function RightsPage() {
  // 加班费
  const [otWage, setOtWage] = useState('6000');
  const [wd, setWd] = useState('40');
  const [we, setWe] = useState('16');
  const [ho, setHo] = useState('8');
  const [ot, setOt] = useState<any>(null);
  // 最低工资
  const [mwWage, setMwWage] = useState('3500');
  const [tierIdx, setTierIdx] = useState(2);
  const [mw, setMw] = useState<any>(null);
  // 维权评估
  const [owed, setOwed] = useState('8000');
  const [employed, setEmployed] = useState(true);
  const [evIdx, setEvIdx] = useState(1);
  const [claim, setClaim] = useState<any>(null);

  return (
    <View className="page">
      <View className="header"><Text className="header-title">劳动权益</Text></View>

      {/* 加班费反算 */}
      <View className="card calc">
        <View className="calc-title">加班费反算</View>
        <View className="calc-desc">依法反算应得加班费（工作日 1.5 倍、休息日 2 倍、法定节假日 3 倍）。</View>
        <View className="input-row"><Text className="label">月工资</Text><Input className="input" type="digit" value={otWage} onInput={(e) => setOtWage(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">工作日延时</Text><Input className="input" type="digit" value={wd} onInput={(e) => setWd(e.detail.value)} /><Text className="unit">小时/月</Text></View>
        <View className="input-row"><Text className="label">休息日</Text><Input className="input" type="digit" value={we} onInput={(e) => setWe(e.detail.value)} /><Text className="unit">小时/月</Text></View>
        <View className="input-row"><Text className="label">法定节假日</Text><Input className="input" type="digit" value={ho} onInput={(e) => setHo(e.detail.value)} /><Text className="unit">小时/月</Text></View>
        <Button className="btn-primary" onClick={() => setOt(computeOvertimePay(Number(otWage) || 0, Number(wd) || 0, Number(we) || 0, Number(ho) || 0))}>算加班费</Button>
        {ot && !ot.error && (
          <View className="result-box">
            <View className="big-line">应得<Text className="rate good">{fmtNum(ot.total_overtime)}</Text>元</View>
            <View className="info-row"><Text className="info-label">法定时薪</Text><Text className="info-val">{ot.hourly_wage.toFixed(2)} 元/小时</Text></View>
            {ot.detail.map((d: any, i: number) => (
              <View className="info-row" key={i}><Text className="info-label">{d.type} {d.hours}h×{d.rate}倍</Text><Text className="info-val">{fmtNum(d.pay)} 元</Text></View>
            ))}
            <View className="note">{ot.note}</View>
          </View>
        )}
      </View>

      {/* 最低工资对照 */}
      <View className="card calc">
        <View className="calc-title">最低工资对照</View>
        <View className="calc-desc">月薪低于当地最低工资即违法。</View>
        <View className="input-row"><Text className="label">你的月薪</Text><Input className="input" type="digit" value={mwWage} onInput={(e) => setMwWage(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">城市等级</Text><Picker mode="selector" range={TIERS} value={tierIdx} onChange={(e) => setTierIdx(Number(e.detail.value))}><View className="picker">{TIERS[tierIdx]}</View></Picker></View>
        <Button className="btn-primary" onClick={() => setMw(computeMinWageCheck(Number(mwWage) || 0, TIERS[tierIdx]))}>对照</Button>
        {mw && !mw.error && (
          <View className="result-box">
            <View className={`big-line ${mw.below ? 'bad' : 'good'}`}>{mw.below ? '⚠️ 低于最低工资' : '高于最低工资'}（{(mw.ratio * 100).toFixed(0)}%）</View>
            <View className="info-row"><Text className="info-label">当地最低工资</Text><Text className="info-val">{fmtNum(mw.min_wage)} 元/月</Text></View>
            <View className="note">{mw.note}</View>
          </View>
        )}
      </View>

      {/* 维权评估 */}
      <View className="card calc">
        <View className="calc-title">维权现实评估</View>
        <View className="calc-desc">被欠加班费，值不值得争？按实际成本给分级建议。</View>
        <View className="input-row"><Text className="label">被欠金额</Text><Input className="input" type="digit" value={owed} onInput={(e) => setOwed(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">是否在职</Text><Switch checked={employed} onChange={(e) => setEmployed(e.detail.value)} color="#e8843c" /></View>
        <View className="input-row"><Text className="label">证据情况</Text><Picker mode="selector" range={EVIDENCE} value={evIdx} onChange={(e) => setEvIdx(Number(e.detail.value))}><View className="picker">{EVIDENCE[evIdx]}</View></Picker></View>
        <Button className="btn-primary" onClick={() => setClaim(assessOvertimeClaim(Number(owed) || 0, employed, EVIDENCE[evIdx]))}>评估</Button>
        {claim && !claim.error && (
          <View className="result-box">
            <View className={`big-line ${claim.verdict_level === 'good' ? 'good' : claim.verdict_level === 'warn' ? 'bad' : 'warn'}`}>{claim.verdict}</View>
            <View className="info-row"><Text className="info-label">胜算</Text><Text className="info-val">{claim.win_chance}</Text></View>
            <View className="note">{claim.note}</View>
          </View>
        )}
      </View>
    </View>
  );
}
