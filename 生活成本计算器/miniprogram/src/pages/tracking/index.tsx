import { useState } from 'react';
import { View, Text, Button } from '@tarojs/components';
import { metricsFrom, loadLastProfile } from '../../core';
import { taroStorage } from '../../utils/storage';
import { fmtNum } from '../../utils/format';
import './index.scss';

const TRACK_KEY = 'tracking_snapshots';
const fmtTime = (d: Date): string => {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
};

interface Snap {
  time: string;
  name: string;
  metrics: any;
  profile: any;
}

const loadSnaps = (): Snap[] => {
  try {
    const s = taroStorage.getItem(TRACK_KEY);
    return s ? JSON.parse(s) : [];
  } catch { return []; }
};

const PROFILE_FIELDS: [string, string][] = [
  ['age', '年龄'], ['wage', '月薪(元)'], ['tier', '城市等级'],
  ['housing', '住房'], ['food', '饮食'], ['has_car', '养车'],
  ['insurance', '社保'], ['num_children', '子女数'],
  ['savings', '存款(元)'], ['mortgage_monthly', '房贷(元)'],
];

export default function TrackingPage() {
  useShareAppMessage(() => ({ title: '生活成本计算器——看清你的钱花哪了', path: '/pages/situation/index' }));
  const [snaps, setSnaps] = useState<Snap[]>(loadSnaps());
  const [expanded, setExpanded] = useState<number | null>(null);

  const onSave = () => {
    const p = loadLastProfile(taroStorage);
    if (!p) { return; }
    const m = metricsFrom(p);
    const snap: Snap = {
      time: fmtTime(new Date()),
      name: p.name || '我的档案',
      metrics: m,
      profile: { ...p },
    };
    const next = [snap, ...snaps];
    taroStorage.setItem(TRACK_KEY, JSON.stringify(next));
    setSnaps(next);
  };

  const onDelete = (idx: number) => {
    const next = snaps.filter((_, i) => i !== idx);
    taroStorage.setItem(TRACK_KEY, JSON.stringify(next));
    setSnaps(next);
    if (expanded === idx) setExpanded(null);
  };

  const onClear = () => {
    taroStorage.setItem(TRACK_KEY, '[]');
    setSnaps([]);
  };

  // 柱状图高度比例
  const maxAbs = Math.max(...snaps.map((s) => Math.abs(s.metrics.surplus)), 1);
  const trendData = [...snaps].reverse(); // 时间正序排列

  return (
    <View className="page">
      <View className="header"><Text className="header-title">长期跟踪</Text></View>

      <View className="card">
        <View className="calc-title">存一次快照</View>
        <View className="calc-desc">按当前档案算 5 项指标存下来，多次积累后看趋势变化。请先到「档案」填好你的情况。</View>
        <Button className="btn-primary" onClick={onSave}>📌 存本次快照</Button>
      </View>

      {snaps.length > 0 && (
        <View>
          {/* 趋势柱状图 */}
          <View className="card">
            <View className="detail-title">月结余趋势</View>
            <ScrollView scrollX className="trend-scroll">
              <View className="trend-chart">
                {trendData.map((s, i) => {
                  const heightPct = Math.max((Math.abs(s.metrics.surplus) / maxAbs) * 100, 4);
                  const isPos = s.metrics.surplus >= 0;
                  return (
                    <View className="bar-col" key={i}>
                      <Text className={`bar-val ${isPos ? 'pos' : 'neg'}`}>{isPos ? '' : '-'}{fmtNum(Math.abs(s.metrics.surplus))}</Text>
                      <View className={`bar-fill ${isPos ? 'pos' : 'neg'}`} style={{ height: `${heightPct}%` }} />
                      <Text className="bar-label">{s.time.slice(5, 10)}</Text>
                    </View>
                  );
                })}
              </View>
            </ScrollView>
          </View>

          {/* 快照列表 */}
          {snaps.map((s, idx) => (
            <View className="card snap-card" key={idx}>
              <View className="snap-header" onClick={() => setExpanded(expanded === idx ? null : idx)}>
                <View className="snap-info">
                  <Text className="snap-name">{s.name}</Text>
                  <Text className="snap-time">{s.time}</Text>
                </View>
                <View className="snap-summary">
                  <Text className={`snap-surplus ${s.metrics.surplus >= 0 ? 'pos' : 'neg'}`}>
                    {s.metrics.surplus >= 0 ? '+' : ''}{fmtNum(s.metrics.surplus)} 元
                  </Text>
                  <Text className="snap-rate">{s.metrics.surplus_rate}%</Text>
                  <Text className="snap-arrow">{expanded === idx ? '▼' : '▶'}</Text>
                </View>
              </View>

              {/* 收起时：快速指标行 */}
              {expanded !== idx && (
                <View className="snap-quick">
                  <Text className="quick-item">存款 {fmtNum(s.metrics.savings)}</Text>
                  <Text className="quick-item">成本 {fmtNum(s.metrics.cost_total)}</Text>
                  <Text className="quick-item">负债 {fmtNum(s.metrics.debt_monthly)}</Text>
                </View>
              )}

              {/* 展开：完整信息 */}
              {expanded === idx && (
                <View className="snap-detail">
                  <View className="snap-metrics">
                    <View className="snap-metric"><Text className="m-label">月结余</Text><Text className={`m-val ${s.metrics.surplus >= 0 ? 'pos' : 'neg'}`}>{fmtNum(s.metrics.surplus)} 元</Text></View>
                    <View className="snap-metric"><Text className="m-label">结余率</Text><Text className="m-val">{s.metrics.surplus_rate}%</Text></View>
                    <View className="snap-metric"><Text className="m-label">存款</Text><Text className="m-val">{fmtNum(s.metrics.savings)} 元</Text></View>
                    <View className="snap-metric"><Text className="m-label">月成本</Text><Text className="m-val">{fmtNum(s.metrics.cost_total)} 元</Text></View>
                    <View className="snap-metric"><Text className="m-label">月负债</Text><Text className="m-val">{fmtNum(s.metrics.debt_monthly)} 元</Text></View>
                  </View>
                  <View className="snap-profile">
                    <Text className="sp-title">档案快照</Text>
                    {PROFILE_FIELDS.map(([key, label]) => {
                      const v = s.profile?.[key];
                      if (v === undefined || v === null || v === '') return null;
                      const display = typeof v === 'boolean' ? (v ? '是' : '否') : String(v);
                      return (
                        <View className="sp-row" key={key}>
                          <Text className="sp-label">{label}</Text>
                          <Text className="sp-val">{display}</Text>
                        </View>
                      );
                    })}
                  </View>
                  <Button className="btn-delete" onClick={() => onDelete(idx)}>🗑 删除此快照</Button>
                </View>
              )}
            </View>
          ))}

          <Button className="btn-clear" onClick={onClear}>清空全部记录</Button>
        </View>
      )}
    </View>
  );
}
