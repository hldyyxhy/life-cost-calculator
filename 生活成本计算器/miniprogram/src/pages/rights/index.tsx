import { useState } from 'react';
import { View, Text, Input, Picker, Switch, Button } from '@tarojs/components';
import {
  computeOvertimePay, computeMinWageCheck, assessOvertimeClaim,
  estimateUnemploymentPay, unemployDuration, calcInjuryOneTime, calcInjuryPension, getProvinceInjuryExtra,
  bonusTaxCompare, specialDeductionHints,
  buildOvertimePrompt, buildMinWagePrompt, buildInjuryPrompt, buildUnemploymentPrompt, buildSubsidyPrompt, buildTaxPrompt,
} from '../../core';
import PromptCard from '../../components/PromptCard';
import './index.scss';

const fmtNum = (n: number): string => {
  if (n === null || n === undefined) return '—';
  const neg = n < 0;
  return (neg ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};
const TIERS = ['一线', '新一线', '二线', '三线', '四线', '五线'];
const EVIDENCE = ['充分', '部分', '几乎没有'];
const GRADES = ['1级', '2级', '3级', '4级', '5级', '6级', '7级', '8级', '9级', '10级'];

export default function RightsPage() {
  const [prompt, setPrompt] = useState('');

  // ① 加班费 ② 最低工资 ③ 维权
  const [otWage, setOtWage] = useState('6000');
  const [wd, setWd] = useState('40');
  const [we, setWe] = useState('16');
  const [ho, setHo] = useState('8');
  const [ot, setOt] = useState<any>(null);
  const [mwWage, setMwWage] = useState('3500');
  const [tierIdx, setTierIdx] = useState(2);
  const [mw, setMw] = useState<any>(null);
  const [owed, setOwed] = useState('8000');
  const [employed, setEmployed] = useState(true);
  const [evIdx, setEvIdx] = useState(1);
  const [claim, setClaim] = useState<any>(null);

  // ④ 失业金
  const [unempCity, setUnempCity] = useState('北京');
  const [unempYears, setUnempYears] = useState('6');
  const [unemp, setUnemp] = useState<any>(null);

  // ⑤ 工伤
  const [injuryCity, setInjuryCity] = useState('广东');
  const [gradeIdx, setGradeIdx] = useState(6);
  const [injuryWage, setInjuryWage] = useState('6000');
  const [injury, setInjury] = useState<any>(null);

  // ⑥ 个税
  const [annualSalary, setAnnualSalary] = useState('120000');
  const [bonus, setBonus] = useState('30000');
  const [taxSpecial, setTaxSpecial] = useState('4000');
  const [taxSocial, setTaxSocial] = useState('1500');
  const [taxKids, setTaxKids] = useState(false);
  const [taxElderly, setTaxElderly] = useState(false);
  const [taxLoan, setTaxLoan] = useState(false);
  const [tax, setTax] = useState<any>(null);

  // 个税提示词
  const [taxHints, setTaxHints] = useState<string[] | null>(null);

  const calcInjury = () => {
    const grade = gradeIdx + 1;
    const wage = Number(injuryWage) || 6000;
    const [months, amount] = calcInjuryOneTime(grade, wage);
    const [ratio, pension, payer] = calcInjuryPension(grade, wage);
    const [medical, employment, baseNote] = getProvinceInjuryExtra(injuryCity, grade);
    setInjury({ months, amount, ratio, pension, payer, medical, employment, baseNote, grade, wage });
  };

  const calcTax = () => {
    const r = bonusTaxCompare(Number(annualSalary) || 0, Number(bonus) || 0, Number(taxSpecial) || 0, Number(taxSocial) || 0);
    const hints = specialDeductionHints(taxKids ? 1 : 0, taxElderly, taxLoan, false);
    setTax(r);
    setTaxHints(hints);
  };

  return (
    <View className="page">
      <View className="header"><Text className="header-title">劳动权益</Text></View>

      {/* ① 加班费 */}
      <View className="card calc">
        <View className="calc-title">① 加班费反算</View>
        <View className="input-row"><Text className="label">月工资</Text><Input className="input" type="digit" value={otWage} onInput={(e) => setOtWage(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">工作日延时</Text><Input className="input" type="digit" value={wd} onInput={(e) => setWd(e.detail.value)} /><Text className="unit">h/月</Text></View>
        <View className="input-row"><Text className="label">休息日</Text><Input className="input" type="digit" value={we} onInput={(e) => setWe(e.detail.value)} /><Text className="unit">h/月</Text></View>
        <View className="input-row"><Text className="label">法定节假日</Text><Input className="input" type="digit" value={ho} onInput={(e) => setHo(e.detail.value)} /><Text className="unit">h/月</Text></View>
        <Button className="btn-primary" onClick={() => { setOt(computeOvertimePay(Number(otWage) || 0, Number(wd) || 0, Number(we) || 0, Number(ho) || 0)); setPrompt(''); }}>算加班费</Button>
        {ot && !ot.error && (
          <View className="result-box">
            <View className="big-line">应得 <Text className="rate good">{fmtNum(ot.total_overtime)}</Text> 元</View>
            <View className="info-row"><Text className="info-label">法定时薪</Text><Text className="info-val">{ot.hourly_wage.toFixed(2)} 元/h</Text></View>
            <View className="note">{ot.note}</View>
            <Button className="btn-ask" onClick={() => setPrompt(buildOvertimePrompt(Number(otWage) || 0, Number(wd) || 0, Number(we) || 0, Number(ho) || 0, 0, 1, true, '部分', ''))}>问 AI</Button>
          </View>
        )}
      </View>

      {/* ② 最低工资 */}
      <View className="card calc">
        <View className="calc-title">② 最低工资对照</View>
        <View className="input-row"><Text className="label">你的月薪</Text><Input className="input" type="digit" value={mwWage} onInput={(e) => setMwWage(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">城市等级</Text><Picker mode="selector" range={TIERS} value={tierIdx} onChange={(e) => setTierIdx(Number(e.detail.value))}><View className="picker">{TIERS[tierIdx]}</View></Picker></View>
        <Button className="btn-primary" onClick={() => { setMw(computeMinWageCheck(Number(mwWage) || 0, TIERS[tierIdx])); setPrompt(''); }}>对照</Button>
        {mw && !mw.error && (
          <View className="result-box">
            <View className={`big-line ${mw.below ? 'bad' : 'good'}`}>{mw.below ? '⚠️ 低于最低工资' : '高于最低工资'}（{(mw.ratio * 100).toFixed(0)}%）</View>
            <View className="info-row"><Text className="info-label">当地最低工资</Text><Text className="info-val">{fmtNum(mw.min_wage)} 元/月</Text></View>
            <Button className="btn-ask" onClick={() => setPrompt(buildMinWagePrompt(Number(mwWage) || 0, TIERS[tierIdx]))}>问 AI</Button>
          </View>
        )}
      </View>

      {/* ③ 维权评估 */}
      <View className="card calc">
        <View className="calc-title">③ 维权值不值得</View>
        <View className="input-row"><Text className="label">被欠金额</Text><Input className="input" type="digit" value={owed} onInput={(e) => setOwed(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">是否在职</Text><Switch checked={employed} onChange={(e) => setEmployed(e.detail.value)} color="#e8843c" /></View>
        <View className="input-row"><Text className="label">证据</Text><Picker mode="selector" range={EVIDENCE} value={evIdx} onChange={(e) => setEvIdx(Number(e.detail.value))}><View className="picker">{EVIDENCE[evIdx]}</View></Picker></View>
        <Button className="btn-primary" onClick={() => { setClaim(assessOvertimeClaim(Number(owed) || 0, employed, EVIDENCE[evIdx])); setPrompt(''); }}>评估</Button>
        {claim && !claim.error && (
          <View className="result-box">
            <View className={`big-line ${claim.verdict_level === 'good' ? 'good' : claim.verdict_level === 'warn' ? 'bad' : 'warn'}`}>{claim.verdict}</View>
            <View className="note">{claim.note}</View>
          </View>
        )}
      </View>

      {/* ④ 失业金 */}
      <View className="card calc">
        <View className="calc-title">④ 失业金能领多少</View>
        <View className="input-row"><Text className="label">城市</Text><Input className="input" value={unempCity} onInput={(e) => setUnempCity(e.detail.value)} /></View>
        <View className="input-row"><Text className="label">累计缴费</Text><Input className="input" type="digit" value={unempYears} onInput={(e) => setUnempYears(e.detail.value)} /><Text className="unit">年</Text></View>
        <Button className="btn-primary" onClick={() => {
          const [amt, note] = estimateUnemploymentPay(unempCity);
          const duration = unemployDuration(Number(unempYears) || 0);
          setUnemp({ amt, note, duration }); setPrompt('');
        }}>查失业金</Button>
        {unemp && (
          <View className="result-box">
            <View className="big-line">每月约 <Text className="rate good">{unemp.amt ? fmtNum(unemp.amt) : '?'}</Text> 元</View>
            <View className="info-row"><Text className="info-label">可领月数</Text><Text className="info-val">{unemp.duration} 个月</Text></View>
            <View className="note">{unemp.note}</View>
            <Button className="btn-ask" onClick={() => setPrompt(buildUnemploymentPrompt(unempCity, unempYears, '', ''))}>问 AI：怎么申领</Button>
          </View>
        )}
      </View>

      {/* ⑤ 工伤赔偿 */}
      <View className="card calc">
        <View className="calc-title">⑤ 工伤能赔多少</View>
        <View className="input-row"><Text className="label">省份</Text><Input className="input" value={injuryCity} onInput={(e) => setInjuryCity(e.detail.value)} /></View>
        <View className="input-row"><Text className="label">伤残等级</Text><Picker mode="selector" range={GRADES} value={gradeIdx} onChange={(e) => setGradeIdx(Number(e.detail.value))}><View className="picker">{GRADES[gradeIdx]}</View></Picker></View>
        <View className="input-row"><Text className="label">受伤前月薪</Text><Input className="input" type="digit" value={injuryWage} onInput={(e) => setInjuryWage(e.detail.value)} /><Text className="unit">元</Text></View>
        <Button className="btn-primary" onClick={() => { calcInjury(); setPrompt(''); }}>算工伤赔偿</Button>
        {injury && (
          <View className="result-box">
            <View className="big-line">一次性补助 <Text className="rate warn">{fmtNum(injury.amount)}</Text> 元</View>
            <View className="info-row"><Text className="info-label">补助月数</Text><Text className="info-val">{injury.months} 个月</Text></View>
            {injury.ratio !== null && (
              <>
                <View className="info-row"><Text className="info-label">伤残津贴</Text><Text className="info-val">{fmtNum(injury.pension)} 元/月（{injury.payer}）</Text></View>
                <View className="info-row"><Text className="info-label">医疗补助</Text><Text className="info-val">{injury.medical !== null ? `${fmtNum(injury.medical)} 元` : '未收录'}</Text></View>
                <View className="info-row"><Text className="info-label">就业补助</Text><Text className="info-val">{injury.employment !== null ? `${fmtNum(injury.employment)} 元` : '未收录'}</Text></View>
              </>
            )}
            {injury.baseNote && <View className="note">{injury.baseNote}</View>}
            <Button className="btn-ask" onClick={() => setPrompt(buildInjuryPrompt(injuryCity, injury.grade, injury.wage))}>问 AI</Button>
          </View>
        )}
      </View>

      {/* ⑥ 灵活就业补贴（4050）—— 外包 AI 查当地政策 */}
      <View className="card calc">
        <View className="calc-title">⑥ 灵活就业补贴（4050）</View>
        <View className="calc-desc">各地政策差异大，点「问 AI」查你所在城市的最新标准。</View>
        <Button className="btn-ask" onClick={() => setPrompt(buildSubsidyPrompt(''))}>问 AI：我能不能领 4050</Button>
      </View>

      {/* ⑦ 个税优化 */}
      <View className="card calc">
        <View className="calc-title">⑦ 年终奖怎么计税省</View>
        <View className="input-row"><Text className="label">年税前工资</Text><Input className="input" type="digit" value={annualSalary} onInput={(e) => setAnnualSalary(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">年终奖</Text><Input className="input" type="digit" value={bonus} onInput={(e) => setBonus(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">月专项扣除</Text><Input className="input" type="digit" value={taxSpecial} onInput={(e) => setTaxSpecial(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">月社保</Text><Input className="input" type="digit" value={taxSocial} onInput={(e) => setTaxSocial(e.detail.value)} /><Text className="unit">元</Text></View>
        <View className="input-row"><Text className="label">有子女</Text><Switch checked={taxKids} onChange={(e) => setTaxKids(e.detail.value)} color="#e8843c" /></View>
        <View className="input-row"><Text className="label">赡养老人</Text><Switch checked={taxElderly} onChange={(e) => setTaxElderly(e.detail.value)} color="#e8843c" /></View>
        <View className="input-row"><Text className="label">有房贷</Text><Switch checked={taxLoan} onChange={(e) => setTaxLoan(e.detail.value)} color="#e8843c" /></View>
        <Button className="btn-primary" onClick={() => { calcTax(); setPrompt(''); }}>算哪种省</Button>
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

      <PromptCard prompt={prompt} />
    </View>
  );
}
