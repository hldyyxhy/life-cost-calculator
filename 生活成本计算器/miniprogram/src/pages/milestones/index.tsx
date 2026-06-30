import { useState } from 'react';
import { View, Text, Input, Picker, Button } from '@tarojs/components';
import { useDidShow } from '@tarojs/taro';
import { cityFactor, computeLifeCost, computeSurplus, buildMilestonesPrompt, loadLastProfile } from '../../core';
import { taroStorage } from '../../utils/storage';
import costData from '../../core/data/cost.json';
import PromptCard from '../../components/PromptCard';
import SmartNote from '../../components/SmartNote';
import './index.scss';

const fmtNum = (n: number): string => {
  const neg = n < 0;
  return (neg ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};
const TIERS = ['一线', '新一线', '二线', '三线', '四线', '五线'];
const LEVELS = ['普惠', '中产', '高端'];
const CARE_MODES = ['居家养老', '普惠养老机构', '中高端养老机构'];
const CARE_MAP: Record<string, string> = {
  '居家养老': '居家养老（基本生活费）',
  '普惠养老机构': '普惠养老机构',
  '中高端养老机构': '中高端养老机构',
};
const C = costData as any;

export default function MilestonesPage() {
  // 公共输入
  const [tierIdx, setTierIdx] = useState(2);
  const [wage, setWage] = useState('5000');
  // 结婚
  const [purchase, setPurchase] = useState<'贷款' | '全款'>('贷款');
  const [marriage, setMarriage] = useState<any>(null);
  // 养娃
  const [levelIdx, setLevelIdx] = useState(0);
  const [child, setChild] = useState<any>(null);
  // 养老
  const [careIdx, setCareIdx] = useState(0);
  const [retireAge, setRetireAge] = useState('60');
  const [retire, setRetire] = useState<any>(null);
  // 问 AI
  const [prompt, setPrompt] = useState('');

  // 从档案预填
  useDidShow(() => {
    const p = loadLastProfile(taroStorage);
    if (p) {
      setTierIdx(Math.max(0, TIERS.indexOf(p.tier)));
      if (p.wage) setWage(String(p.wage));
    }
  });

  const tier = TIERS[tierIdx];
  const wageN = Number(wage) || 5000;
  const monthlySurplus = () => computeSurplus(wageN, tier);

  // 结婚
  const calcMarriage = () => {
    const cf = cityFactor(tier);
    const bride = C.MARRIAGE_COST['彩礼'][tier];
    const wedding = C.MARRIAGE_COST['婚礼']['base'] * cf;
    const hp = C.HOUSE_PURCHASE[tier];
    const house = purchase === '全款' ? hp.total : hp.downpayment;
    const total = bride + wedding + house;
    const ms = monthlySurplus();
    const years = ms > 0 ? total / (ms * 12) : -1;
    setMarriage({ bride, wedding, house, total, hp, years, ms });
  };

  // 养娃
  const calcChild = () => {
    const result = computeLifeCost(tier, LEVELS[levelIdx], '公立·顺产', '居家养老', '公办', false);
    const eduTotal = result.stage_subtotals.find((s: any) => s.stage.includes('养育'))?.amount || 0;
    const annual = eduTotal / 22;
    const monthly = eduTotal / (22 * 12);
    const ms = monthlySurplus();
    const ratio = ms > 0 ? (monthly / ms) * 100 : -1;
    setChild({ total: eduTotal, annual, monthly, ms, ratio });
  };

  // 养老
  const calcRetire = () => {
    const ra = Number(retireAge) || 60;
    const years = C.LIFE_EXPECTANCY - ra;
    const pension = C.RETIREMENT['pension_monthly'][tier];
    const care = C.RETIREMENT['care_monthly'][CARE_MAP[CARE_MODES[careIdx]]][tier];
    const gap = pension - care;
    const totalGap = gap < 0 ? -gap * 12 * years : 0;
    setRetire({ pension, care, gap, years, ra, totalGap });
  };

  return (
    <View className="page">
      <View className="header"><Text className="header-title">人生三座山</Text></View>

      {/* 公共输入 */}
      <View className="card common">
        <View className="calc-title">基本信息（三座山共享）</View>
        <View className="input-row">
          <Text className="label">城市等级</Text>
          <Picker mode="selector" range={TIERS} value={tierIdx} onChange={(e) => setTierIdx(Number(e.detail.value))}>
            <View className="picker">{tier}</View>
          </Picker>
        </View>
        <View className="input-row">
          <Text className="label">月薪（税前）</Text>
          <Input className="input" type="digit" value={wage} onInput={(e) => setWage(e.detail.value)} />
          <Text className="unit">元</Text>
        </View>
        <Button className="btn-ask" onClick={() => setPrompt(buildMilestonesPrompt(tier, wageN))}>问 AI：三座山怎么规划</Button>
      </View>

      {/* 第一座山：结婚 */}
      <View className="card mountain">
        <View className="mountain-title">第一座山：结婚</View>
        <View className="seg-tabs">
          <View className={`seg-tab ${purchase === '贷款' ? 'active' : ''}`} onClick={() => setPurchase('贷款')}><Text>贷款（算首付）</Text></View>
          <View className={`seg-tab ${purchase === '全款' ? 'active' : ''}`} onClick={() => setPurchase('全款')}><Text>全款</Text></View>
        </View>
        <Button className="btn-primary" onClick={calcMarriage}>计算结婚成本</Button>
        {marriage && (
          <View className="result-box">
            <View className="info-row"><Text className="info-label">彩礼</Text><Text className="info-val">{fmtNum(marriage.bride)} 元</Text></View>
            <View className="info-row"><Text className="info-label">婚礼婚宴</Text><Text className="info-val">{fmtNum(marriage.wedding)} 元</Text></View>
            <View className="info-row"><Text className="info-label">{purchase === '全款' ? '婚房（全款）' : '婚房首付'}</Text><Text className="info-val">{fmtNum(marriage.house)} 元</Text></View>
            <View className="big-line">合计 <Text className="rate warn">{fmtNum(marriage.total)}</Text> 元</View>
            <SmartNote text={marriage.years < 0 ? '⚠️ 你目前入不敷出，暂不具备条件。' : marriage.years >= 100 ? '按当前结余几乎不可能攒够。' : `按月结余 ${fmtNum(marriage.ms)} 元，需攒约 ${Math.round(marriage.years)} 年。`} />
          </View>
        )}
      </View>

      {/* 第二座山：养娃 */}
      <View className="card mountain">
        <View className="mountain-title">第二座山：养一个孩子</View>
        <View className="input-row">
          <Text className="label">养育路线</Text>
          <Picker mode="selector" range={LEVELS} value={levelIdx} onChange={(e) => setLevelIdx(Number(e.detail.value))}>
            <View className="picker">{LEVELS[levelIdx]}</View>
          </Picker>
        </View>
        <Button className="btn-primary" onClick={calcChild}>计算养娃成本</Button>
        {child && (
          <View className="result-box">
            <View className="big-line">0-22岁累计 <Text className="rate warn">{fmtNum(child.total)}</Text> 元</View>
            <View className="info-row"><Text className="info-label">年均</Text><Text className="info-val">{fmtNum(child.annual)} 元/年</Text></View>
            <View className="info-row"><Text className="info-label">折合月支出</Text><Text className="info-val">{fmtNum(child.monthly)} 元/月</Text></View>
            <SmartNote text={child.ratio < 0 ? '⚠️ 你目前没有结余，养娃需另找来源。' : child.ratio > 100 ? `⚠️ 占月结余 ${child.ratio.toFixed(0)}%，超过全部结余！` : child.ratio >= 50 ? `⚠️ 占月结余 ${child.ratio.toFixed(0)}%，压力较大。` : `✅ 占月结余 ${child.ratio.toFixed(0)}%，可承受。`} />
          </View>
        )}
      </View>

      {/* 第三座山：养老 */}
      <View className="card mountain">
        <View className="mountain-title">第三座山：养老</View>
        <View className="input-row">
          <Text className="label">养老方式</Text>
          <Picker mode="selector" range={CARE_MODES} value={careIdx} onChange={(e) => setCareIdx(Number(e.detail.value))}>
            <View className="picker">{CARE_MODES[careIdx]}</View>
          </Picker>
        </View>
        <View className="input-row">
          <Text className="label">退休年龄</Text>
          <Input className="input" type="number" value={retireAge} onInput={(e) => setRetireAge(e.detail.value)} />
          <Text className="unit">岁</Text>
        </View>
        <Button className="btn-primary" onClick={calcRetire}>计算养老缺口</Button>
        {retire && (
          <View className="result-box">
            <View className="info-row"><Text className="info-label">每月养老金</Text><Text className="info-val">{fmtNum(retire.pension)} 元</Text></View>
            <View className="info-row"><Text className="info-label">每月支出</Text><Text className="info-val">{fmtNum(retire.care)} 元</Text></View>
            <View className="big-line">
              {retire.gap >= 0
                ? <Text className="rate good">无缺口 ✅（每月多 {fmtNum(retire.gap)} 元）</Text>
                : <Text className="rate bad">每月缺口 {fmtNum(-retire.gap)} 元 ⚠️</Text>}
            </View>
            {retire.gap < 0 && (
              <SmartNote text={`退休后 ${retire.years} 年总缺口约 ${fmtNum(retire.totalGap)} 元。现在起每月多存 ${fmtNum(-retire.gap)} 元可填补。`} />
            )}
          </View>
        )}
      </View>

      <PromptCard prompt={prompt} />
    </View>
  );
}
