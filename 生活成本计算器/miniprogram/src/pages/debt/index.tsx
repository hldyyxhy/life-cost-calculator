import { useState } from 'react';
import { View, Text, Input, Picker, Button } from '@tarojs/components';
import {
  computeLoanApr, computeAffordableDebt, simulateDebtPayoff, simulateLoanSpiral, assessDebtHealth,
  buildLoanAprPrompt, buildAffordableDebtPrompt, buildDebtPayoffPrompt, buildSpiralPrompt, buildDebtHealthPrompt,
} from '../../core';
import SubTabs from '../../components/SubTabs';
import { fmtNum } from '../../utils/format';
import PromptCard from '../../components/PromptCard';
import SmartNote from '../../components/SmartNote';
import './index.scss';

const lc = (l: string) => (l === '正常' ? 'good' : l === '偏高' ? 'warn' : 'bad');
const TABS = ['①真实年化', '②可承受', '③雪球雪崩', '④以贷养贷', '⑤债务健康'];
const METHODS = ['雪球法（先还小额）', '雪崩法（先还高息）'];
const MK = ['snowball', 'avalanche'];

export default function DebtPage() {
  const [tab, setTab] = useState(0);
  const [prompt, setPrompt] = useState('');
  const [principal, setPrincipal] = useState('10000');
  const [monthly, setMonthly] = useState('900');
  const [periods, setPeriods] = useState('12');
  const [apr, setApr] = useState<any>(null);
  const [surplus, setSurplus] = useState('2000');
  const [aprPct, setAprPct] = useState('18');
  const [periods2, setPeriods2] = useState('24');
  const [aff, setAff] = useState<any>(null);
  const [d1b, setD1b] = useState('3000'); const [d1r, setD1r] = useState('18'); const [d1m, setD1m] = useState('300');
  const [d2b, setD2b] = useState('10000'); const [d2r, setD2r] = useState('36'); const [d2m, setD2m] = useState('500');
  const [methodIdx, setMethodIdx] = useState(1);
  const [extra, setExtra] = useState('500');
  const [payoff, setPayoff] = useState<any>(null);
  const [init, setInit] = useState('10000');
  const [spiralApr, setSpiralApr] = useState('24');
  const [months, setMonths] = useState('24');
  const [pay, setPay] = useState('0');
  const [spiral, setSpiral] = useState<any>(null);
  const [totalDebt, setTotalDebt] = useState('50000');
  const [income, setIncome] = useState('8000');
  const [monthlyPay, setMonthlyPay] = useState('2000');
  const [healthApr, setHealthApr] = useState('18');
  const [health, setHealth] = useState<any>(null);

  return (
    <View className="page">
      <View className="header"><Text className="header-title">借贷真相</Text></View>
      <SubTabs tabs={TABS} current={tab} onChange={setTab} />

      {tab === 0 && (
        <View className="card calc">
          <View className="calc-title">反算真实年化</View>
          <View className="calc-desc">输入本金、月还、期数，算真实年化（IRR），识破「月费率0.7%」话术。</View>
          <View className="input-row"><Text className="label">借款本金</Text><Input className="input" type="digit" value={principal} onInput={(e) => setPrincipal(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">每月还款</Text><Input className="input" type="digit" value={monthly} onInput={(e) => setMonthly(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">期数</Text><Input className="input" type="number" value={periods} onInput={(e) => setPeriods(e.detail.value)} /><Text className="unit">月</Text></View>
          <Button className="btn-primary" onClick={() => { setApr(computeLoanApr(Number(principal) || 0, Number(monthly) || 0, Number(periods) || 0)); setPrompt(''); }}>反算年化</Button>
          {apr && !apr.error && (
            <View className="result-box">
              <View className="big-line">真实年化<Text className={`rate ${lc(apr.level)}`}>{(apr.annual_irr * 100).toFixed(1)}%</Text><Text className={`rate-tag ${lc(apr.level)}`}>{apr.level}</Text></View>
              <View className="info-row"><Text className="info-label">名义年化</Text><Text className="info-val">{(apr.nominal_apr * 100).toFixed(1)}%</Text></View>
              <View className="info-row"><Text className="info-label">总还款</Text><Text className="info-val">{fmtNum(apr.total_payment)} 元</Text></View>
              <View className="info-row"><Text className="info-label">总利息</Text><Text className="info-val">{fmtNum(apr.interest)} 元（{(apr.interest_ratio * 100).toFixed(0)}%）</Text></View>
              <SmartNote text={apr.note} />
              <Button className="btn-ask" onClick={() => setPrompt(buildLoanAprPrompt(Number(principal) || 0, Number(monthly) || 0, Number(periods) || 0))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      {tab === 1 && (
        <View className="card calc">
          <View className="calc-title">我能借多少</View>
          <View className="input-row"><Text className="label">每月结余</Text><Input className="input" type="digit" value={surplus} onInput={(e) => setSurplus(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">名义年化</Text><Input className="input" type="digit" value={aprPct} onInput={(e) => setAprPct(e.detail.value)} /><Text className="unit">%</Text></View>
          <View className="input-row"><Text className="label">期数</Text><Input className="input" type="number" value={periods2} onInput={(e) => setPeriods2(e.detail.value)} /><Text className="unit">月</Text></View>
          <Button className="btn-primary" onClick={() => { setAff(computeAffordableDebt(Number(surplus) || 0, (Number(aprPct) || 0) / 100, Number(periods2) || 0)); setPrompt(''); }}>算上限</Button>
          {aff && !aff.error && (
            <View className="result-box">
              <View className="info-row"><Text className="info-label">最多能借</Text><Text className="info-val strong">{fmtNum(aff.max_principal)} 元</Text></View>
              <View className="info-row"><Text className="info-label">稳妥档</Text><Text className="info-val">{fmtNum(aff.safe_principal)} 元</Text></View>
              <SmartNote text={aff.note} />
              <Button className="btn-ask" onClick={() => setPrompt(buildAffordableDebtPrompt(Number(surplus) || 0, Number(aprPct) || 0, Number(periods2) || 0))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      {tab === 2 && (
        <View className="card calc">
          <View className="calc-title">多笔债怎么还最快</View>
          <View className="calc-desc">输入你的债，模拟两种还法，看哪种省利息。</View>
          <View className="input-row"><Text className="label">债1 余额</Text><Input className="input" type="digit" value={d1b} onInput={(e) => setD1b(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">债1 年化</Text><Input className="input" type="digit" value={d1r} onInput={(e) => setD1r(e.detail.value)} /><Text className="unit">%</Text></View>
          <View className="input-row"><Text className="label">债1 月还</Text><Input className="input" type="digit" value={d1m} onInput={(e) => setD1m(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">债2 余额</Text><Input className="input" type="digit" value={d2b} onInput={(e) => setD2b(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">债2 年化</Text><Input className="input" type="digit" value={d2r} onInput={(e) => setD2r(e.detail.value)} /><Text className="unit">%</Text></View>
          <View className="input-row"><Text className="label">债2 月还</Text><Input className="input" type="digit" value={d2m} onInput={(e) => setD2m(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">每月额外</Text><Input className="input" type="digit" value={extra} onInput={(e) => setExtra(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">还法</Text><Picker mode="selector" range={METHODS} value={methodIdx} onChange={(e) => setMethodIdx(Number(e.detail.value))}><View className="picker">{METHODS[methodIdx]}</View></Picker></View>
          <Button className="btn-primary" onClick={() => {
            const debts = [
              { name: '债1', balance: Number(d1b) || 0, annual_rate: (Number(d1r) || 0) / 100, min_monthly: Number(d1m) || 0 },
              { name: '债2', balance: Number(d2b) || 0, annual_rate: (Number(d2r) || 0) / 100, min_monthly: Number(d2m) || 0 },
            ].filter((d) => d.balance > 0);
            setPayoff(simulateDebtPayoff(debts, MK[methodIdx], Number(extra) || 0)); setPrompt('');
          }}>模拟还清</Button>
          {payoff && !payoff.error && (
            <View className="result-box">
              {payoff.unpayable ? (
                <View className="big-line bad">{payoff.unpayable_reason.split('。\n')[0]}。</View>
              ) : (
                <>
                  <View className="big-line">{MK[methodIdx] === 'snowball' ? '雪球法' : '雪崩法'} <Text className="rate warn">{payoff.total_months}</Text> 个月还清</View>
                  <View className="info-row"><Text className="info-label">总付出</Text><Text className="info-val">{fmtNum(payoff.total_payment)} 元</Text></View>
                  <View className="info-row"><Text className="info-label">总利息</Text><Text className="info-val">{fmtNum(payoff.total_interest)} 元</Text></View>
                </>
              )}
              <SmartNote text={payoff.note} />
              <Button className="btn-ask" onClick={() => setPrompt(buildDebtPayoffPrompt(`债1: ${d1b}元/${d1r}%/月还${d1m}\n债2: ${d2b}元/${d2r}%/月还${d2m}`, Number(extra) || 0))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      {tab === 3 && (
        <View className="card calc">
          <View className="calc-title">以贷养贷会怎样</View>
          <View className="calc-desc">只还最低/借新还旧，债务怎么滚。</View>
          <View className="input-row"><Text className="label">当前欠款</Text><Input className="input" type="digit" value={init} onInput={(e) => setInit(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">年化</Text><Input className="input" type="digit" value={spiralApr} onInput={(e) => setSpiralApr(e.detail.value)} /><Text className="unit">%</Text></View>
          <View className="input-row"><Text className="label">演示月数</Text><Input className="input" type="number" value={months} onInput={(e) => setMonths(e.detail.value)} /><Text className="unit">月</Text></View>
          <View className="input-row"><Text className="label">每月实还</Text><Input className="input" type="digit" value={pay} onInput={(e) => setPay(e.detail.value)} /><Text className="unit">元</Text></View>
          <Button className="btn-primary" onClick={() => { setSpiral(simulateLoanSpiral(Number(init) || 0, (Number(spiralApr) || 0) / 100, Number(months) || 0, Number(pay) || 0)); setPrompt(''); }}>看螺旋</Button>
          {spiral && !spiral.error && (
            <View className="result-box">
              <View className="big-line">{months}月后欠 <Text className={`rate ${spiral.final_balance > Number(init) ? 'bad' : 'good'}`}>{fmtNum(spiral.final_balance)}</Text> 元</View>
              {spiral.doubled && <View className="info-row"><Text className="info-label">翻倍用时</Text><Text className="info-val">{spiral.doubling_month} 月</Text></View>}
              <View className="info-row"><Text className="info-label">止血线</Text><Text className="info-val">月还 {fmtNum(spiral.breakeven_monthly)} 元</Text></View>
              <SmartNote text={spiral.note} />
              <Button className="btn-ask" onClick={() => setPrompt(buildSpiralPrompt(Number(init) || 0, Number(spiralApr) || 0, Number(months) || 0, Number(pay) || 0))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      {tab === 4 && (
        <View className="card calc">
          <View className="calc-title">债务健康检查</View>
          <View className="calc-desc">负债率/月供比/还清月数，一眼看有没有危险。</View>
          <View className="input-row"><Text className="label">总负债</Text><Input className="input" type="digit" value={totalDebt} onInput={(e) => setTotalDebt(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">月收入</Text><Input className="input" type="digit" value={income} onInput={(e) => setIncome(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">月还款</Text><Input className="input" type="digit" value={monthlyPay} onInput={(e) => setMonthlyPay(e.detail.value)} /><Text className="unit">元</Text></View>
          <View className="input-row"><Text className="label">平均年化</Text><Input className="input" type="digit" value={healthApr} onInput={(e) => setHealthApr(e.detail.value)} /><Text className="unit">%</Text></View>
          <Button className="btn-primary" onClick={() => { setHealth(assessDebtHealth(Number(totalDebt) || 0, Number(income) || 0, Number(monthlyPay) || 0, (Number(healthApr) || 0) / 100)); setPrompt(''); }}>检查健康</Button>
          {health && !health.error && (
            <View className="result-box">
              <View className={`big-line ${health.color === 'deficit' ? 'bad' : health.color === 'accent' ? 'warn' : 'good'}`}>{health.level}</View>
              <View className="info-row"><Text className="info-label">负债收入比</Text><Text className="info-val">{(health.debt_ratio * 100).toFixed(0)}%</Text></View>
              <View className="info-row"><Text className="info-label">月供占收入</Text><Text className="info-val">{(health.pay_ratio * 100).toFixed(0)}%</Text></View>
              {health.months !== null && <View className="info-row"><Text className="info-label">还清月数</Text><Text className="info-val">{health.months} 月</Text></View>}
              <SmartNote text={health.note} />
              <Button className="btn-ask" onClick={() => setPrompt(buildDebtHealthPrompt(Number(totalDebt) || 0, Number(income) || 0, Number(monthlyPay) || 0, (Number(healthApr) || 0) / 100))}>问 AI</Button>
            </View>
          )}
        </View>
      )}

      <PromptCard prompt={prompt} />
    </View>
  );
}
