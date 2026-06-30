import { useState } from 'react';
import { View, Text, Input, Picker, Switch, Button } from '@tarojs/components';
import { useDidShow } from '@tarojs/taro';
import { loadLastProfile } from '../../core';
import { taroStorage } from '../../utils/storage';
import {
  computeOvertimePay, computeMinWageCheck, assessOvertimeClaim,
  estimateUnemploymentPay, unemployDuration, calcInjuryOneTime, calcInjuryPension, getProvinceInjuryExtra,
  bonusTaxCompare, specialDeductionHints,
  buildOvertimePrompt, buildMinWagePrompt, buildInjuryPrompt, buildUnemploymentPrompt, buildSubsidyPrompt, buildTaxPrompt,
} from '../../core';
import SubTabs from '../../components/SubTabs';
import SmartNote from '../../components/SmartNote';
import { fmtNum } from '../../utils/format';
import PromptCard from '../../components/PromptCard';
import './index.scss';

const TIERS = ['一线', '新一线', '二线', '三线', '四线', '五线'];
const EVIDENCE = ['充分', '部分', '几乎没有'];
const GRADES = ['1级', '2级', '3级', '4级', '5级', '6级', '7级', '8级', '9级', '10级'];
const TABS = ['①加班费', '②最低工资', '③维权', '④失业金', '⑤工伤', '⑥4050', '⑦个税'];

export default function RightsPage() {
  const [tab, setTab] = useState(0);
  const [prompt, setPrompt] = useState('');
  const [otWage, setOtWage] = useState('6000'); const [wd, setWd] = useState('40'); const [we, setWe] = useState('16'); const [ho, setHo] = useState('8');
  const [ot, setOt] = useState<any>(null);
  const [mwWage, setMwWage] = useState('3500'); const [tierIdx, setTierIdx] = useState(2); const [mw, setMw] = useState<any>(null);
  const [owed, setOwed] = useState('8000'); const [employed, setEmployed] = useState(true); const [evIdx, setEvIdx] = useState(1); const [claim, setClaim] = useState<any>(null);
  const [unempCity, setUnempCity] = useState('北京'); const [unempYears, setUnempYears] = useState('6'); const [unemp, setUnemp] = useState<any>(null);
  const [injuryCity, setInjuryCity] = useState('广东'); const [gradeIdx, setGradeIdx] = useState(6); const [injuryWage, setInjuryWage] = useState('6000'); const [injury, setInjury] = useState<any>(null);
  const [annualSalary, setAnnualSalary] = useState('120000'); const [bonus, setBonus] = useState('30000');
  const [taxSpecial, setTaxSpecial] = useState('4000'); const [taxSocial, setTaxSocial] = useState('1500');
  const [taxKids, setTaxKids] = useState(false); const [taxElderly, setTaxElderly] = useState(false); const [taxLoan, setTaxLoan] = useState(false);
  const [tax, setTax] = useState<any>(null); const [taxHints, setTaxHints] = useState<string[] | null>(null);

  // 从档案预填
  useDidShow(() => {
    const p = loadLastProfile(taroStorage);
    if (p) {
      if (p.wage) { setOtWage(String(p.wage)); setMwWage(String(p.wage)); }
      if (p.tier) setTierIdx(Math.max(0, TIERS.indexOf(p.tier)));
    }
  });

  return (
    <View className="page">
      <View className="header"><Text className="header-title">劳动权益</Text></View>
      <SubTabs tabs={TABS} current={tab} onChange={setTab} />

      {tab === 0 && (
        <View className="card calc">
          <View className="calc-title">加班费反算</View>
          <View className="input-row"><Text className="label">月工资</Text><Input className="input" type="digit" value={otWage} onInput={(e) => setOtWage(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">工作日延时</Text><Input className="input" type="digit" value={wd} onInput={(e) => setWd(e.detail.value)} /><Text className="unit">h/月</Text></View>
          <View className="input-row"><Text className="label">休息日</Text><Input className="input" type="digit" value={we} onInput={(e) => setWe(e.detail.value)} /><Text className="unit">h/月</Text></View>
          <View className="input-row"><Text className="label">法定节假日</Text><Input className="input" type="digit" value={ho} onInput={(e) => setHo(e.detail.value)} /><Text className="unit">h/月</Text></View>
          <Button className="btn-primary" onClick={() => { setOt(computeOvertimePay(Number(otWage) || 0, Number(wd) || 0, Number(we) || 0, Number(ho) || 0)); setPrompt(''); }}>算加班费</Button>
          {ot && !ot.error && (
            <View className="result-box">
              <View className="big-line">应得 <Text className="rate good">{fmtNum(ot.total_overtime)}</Text> 元</View>
              <SmartNote text={ot.note} />
              <Button className="btn-ask" onClick={() => setPrompt(buildOvertimePrompt(Number(otWage) || 0, Number(wd) || 0, Number(we) || 0, Number(ho) || 0, 0, 1, true, '部分', ''))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      {tab === 1 && (
        <View className="card calc">
          <View className="calc-title">最低工资对照</View>
          <View className="input-row"><Text className="label">你的月薪</Text><Input className="input" type="digit" value={mwWage} onInput={(e) => setMwWage(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">城市等级</Text><Picker mode="selector" range={TIERS} value={tierIdx} onChange={(e) => setTierIdx(Number(e.detail.value))}><View className="picker">{TIERS[tierIdx]}</View></Picker></View>
          <Button className="btn-primary" onClick={() => { setMw(computeMinWageCheck(Number(mwWage) || 0, TIERS[tierIdx])); setPrompt(''); }}>对照</Button>
          {mw && !mw.error && (
            <View className="result-box">
              <View className={`big-line ${mw.below ? 'bad' : 'good'}`}>{mw.below ? '⚠️ 低于最低工资' : '高于最低工资'}（{(mw.ratio * 100).toFixed(0)}%）</View>
              <SmartNote text={mw.note} />
              <Button className="btn-ask" onClick={() => setPrompt(buildMinWagePrompt(Number(mwWage) || 0, TIERS[tierIdx]))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      {tab === 2 && (
        <View className="card calc">
          <View className="calc-title">维权值不值得</View>
          <View className="input-row"><Text className="label">被欠金额</Text><Input className="input" type="digit" value={owed} onInput={(e) => setOwed(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">是否在职</Text><Switch checked={employed} onChange={(e) => setEmployed(e.detail.value)} color="#e8843c" /></View>
          <View className="input-row"><Text className="label">证据</Text><Picker mode="selector" range={EVIDENCE} value={evIdx} onChange={(e) => setEvIdx(Number(e.detail.value))}><View className="picker">{EVIDENCE[evIdx]}</View></Picker></View>
          <Button className="btn-primary" onClick={() => { setClaim(assessOvertimeClaim(Number(owed) || 0, employed, EVIDENCE[evIdx])); setPrompt(''); }}>评估</Button>
          {claim && !claim.error && (
            <View className="result-box">
              <View className={`big-line ${claim.verdict_level === 'good' ? 'good' : claim.verdict_level === 'warn' ? 'bad' : 'warn'}`}>{claim.verdict}</View>
              <SmartNote text={claim.note} />
            </View>
          )}
        </View>
      )}

      {tab === 3 && (
        <View className="card calc">
          <View className="calc-title">失业金能领多少</View>
          <View className="input-row"><Text className="label">城市</Text><Input className="input" value={unempCity} onInput={(e) => setUnempCity(e.detail.value)} /></View>
          <View className="input-row"><Text className="label">累计缴费</Text><Input className="input" type="digit" value={unempYears} onInput={(e) => setUnempYears(e.detail.value)} /><Text className="unit">年</Text></View>
          <Button className="btn-primary" onClick={() => { const [amt, note] = estimateUnemploymentPay(unempCity); setUnemp({ amt, note, duration: unemployDuration(Number(unempYears) || 0) }); setPrompt(''); }}>查失业金</Button>
          {unemp && (
            <View className="result-box">
              <View className="big-line">每月约 <Text className="rate good">{unemp.amt ? fmtNum(unemp.amt) : '?'}</Text> 元</View>
              <View className="info-row"><Text className="info-label">可领月数</Text><Text className="info-val">{unemp.duration} 个月</Text></View>
              <SmartNote text={unemp.note} />
              <Button className="btn-ask" onClick={() => setPrompt(buildUnemploymentPrompt(unempCity, unempYears, '', ''))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      {tab === 4 && (
        <View className="card calc">
          <View className="calc-title">工伤能赔多少</View>
          <View className="input-row"><Text className="label">省份</Text><Input className="input" value={injuryCity} onInput={(e) => setInjuryCity(e.detail.value)} /></View>
          <View className="input-row"><Text className="label">伤残等级</Text><Picker mode="selector" range={GRADES} value={gradeIdx} onChange={(e) => setGradeIdx(Number(e.detail.value))}><View className="picker">{GRADES[gradeIdx]}</View></Picker></View>
          <View className="input-row"><Text className="label">受伤前月薪</Text><Input className="input" type="digit" value={injuryWage} onInput={(e) => setInjuryWage(e.detail.value)} /><Text className="unit">元</Text></View>
          <Button className="btn-primary" onClick={() => {
            const g = gradeIdx + 1; const w = Number(injuryWage) || 6000;
            const [months, amount] = calcInjuryOneTime(g, w);
            const [ratio, pension, payer] = calcInjuryPension(g, w);
            const [medical, employment, baseNote] = getProvinceInjuryExtra(injuryCity, g);
            setInjury({ months, amount, ratio, pension, payer, medical, employment, baseNote, grade: g, wage: w }); setPrompt('');
          }}>算工伤赔偿</Button>
          {injury && (
            <View className="result-box">
              <View className="big-line">一次性补助 <Text className="rate warn">{fmtNum(injury.amount)}</Text> 元</View>
              {injury.ratio !== null && <View className="info-row"><Text className="info-label">伤残津贴</Text><Text className="info-val">{fmtNum(injury.pension)} 元/月</Text></View>}
              {injury.medical !== null && <View className="info-row"><Text className="info-label">医疗补助</Text><Text className="info-val">{fmtNum(injury.medical)} 元</Text></View>}
              <Button className="btn-ask" onClick={() => setPrompt(buildInjuryPrompt(injuryCity, injury.grade, injury.wage))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      {tab === 5 && (
        <View className="card calc">
          <View className="calc-title">灵活就业补贴（4050）</View>
          <View className="calc-desc">各地政策差异大，点问 AI 查你所在城市的最新标准。</View>
          <Button className="btn-ask" onClick={() => setPrompt(buildSubsidyPrompt(''))}>问 AI：我能不能领 4050</Button>
        </View>
      )}

      {tab === 6 && (
        <View className="card calc">
          <View className="calc-title">年终奖怎么计税省</View>
          <View className="input-row"><Text className="label">年税前工资</Text><Input className="input" type="digit" value={annualSalary} onInput={(e) => setAnnualSalary(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">年终奖</Text><Input className="input" type="digit" value={bonus} onInput={(e) => setBonus(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">月专项扣除</Text><Input className="input" type="digit" value={taxSpecial} onInput={(e) => setTaxSpecial(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">月社保</Text><Input className="input" type="digit" value={taxSocial} onInput={(e) => setTaxSocial(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">有子女</Text><Switch checked={taxKids} onChange={(e) => setTaxKids(e.detail.value)} color="#e8843c" /></View>
          <View className="input-row"><Text className="label">赡养老人</Text><Switch checked={taxElderly} onChange={(e) => setTaxElderly(e.detail.value)} color="#e8843c" /></View>
          <View className="input-row"><Text className="label">有房贷</Text><Switch checked={taxLoan} onChange={(e) => setTaxLoan(e.detail.value)} color="#e8843c" /></View>
          <Button className="btn-primary" onClick={() => { setTax(bonusTaxCompare(Number(annualSalary) || 0, Number(bonus) || 0, Number(taxSpecial) || 0, Number(taxSocial) || 0)); setTaxHints(specialDeductionHints(taxKids ? 1 : 0, taxElderly, taxLoan, false)); setPrompt(''); }}>算哪种省</Button>
          {tax && !tax.error && (
            <View className="result-box">
              <View className="big-line">{tax.recommend}</View>
              <View className="info-row"><Text className="info-label">单独计税</Text><Text className="info-val">{fmtNum(tax.separate_tax)} 元</Text></View>
              <View className="info-row"><Text className="info-label">合并计税</Text><Text className="info-val">{fmtNum(tax.combined_tax)} 元</Text></View>
              <View className="info-row"><Text className="info-label">省</Text><Text className="info-val strong">{fmtNum(Math.abs(tax.saving))} 元</Text></View>
              <Button className="btn-ask" onClick={() => setPrompt(buildTaxPrompt(Number(annualSalary) || 0, Number(bonus) || 0, '', Number(taxSpecial) || 0, Number(taxSocial) || 0, taxKids ? 1 : 0, taxElderly, taxLoan, false))}>问 AI</Button>
            </View>
          )}
          {taxHints && taxHints.map((h, i) => (<View className="note" key={i}>{h}</View>))}
        </View>
      )}

      <PromptCard prompt={prompt} />
    </View>
  );
}
