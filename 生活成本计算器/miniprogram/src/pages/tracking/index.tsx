import { useState } from 'react';
import { View, Text, Button } from '@tarojs/components';
import { metricsFrom, loadLastProfile } from '../../core';
import { taroStorage } from '../../utils/storage';
import './index.scss';

const fmtNum = (n: number): string => {
  const neg = n < 0;
  return (neg ? '-' : '') + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};
const TRACK_KEY = 'tracking_snapshots';
const fmtTime = (d: Date): string => {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
};
const loadSnaps = (): any[] => {
  try {
    const s = taroStorage.getItem(TRACK_KEY);
    return s ? JSON.parse(s) : [];
  } catch {
    return [];
  }
};

export default function TrackingPage() {
  const [snaps, setSnaps] = useState<any[]>(loadSnaps());

  const onSave = () => {
    const p = loadLastProfile(taroStorage);
    if (!p) {
      return;
    }
    const m = metricsFrom(p);
    const next = [{ time: fmtTime(new Date()), metrics: m }, ...snaps];
    taroStorage.setItem(TRACK_KEY, JSON.stringify(next));
    setSnaps(next);
  };

  const onClear = () => {
    taroStorage.setItem(TRACK_KEY, '[]');
    setSnaps([]);
  };

  return (
    <View className="page">
      <View className="header"><Text className="header-title">长期跟踪</Text></View>

      <View className="card">
        <View className="calc-title">存一次快照</View>
        <View className="calc-desc">按当前档案算 5 项指标存下来，多次积累后看结余/存款的变化趋势。请先到「档案」填好你的情况。</View>
        <Button className="btn-primary" onClick={onSave}>存本次快照</Button>
      </View>

      {snaps.length > 0 && (
        <View className="card">
          <View className="calc-title">历史记录（共 {snaps.length} 次）</View>
          {snaps.map((s, i) => {
            const m = s.metrics;
            return (
              <View className="snap" key={i}>
                <Text className="snap-time">{s.time}</Text>
                <View className="snap-grid">
                  <View className="snap-cell"><Text className="snap-k">月结余</Text><Text className={`snap-v ${m.surplus >= 0 ? 'good' : 'bad'}`}>{fmtNum(m.surplus)}</Text></View>
                  <View className="snap-cell"><Text className="snap-k">结余率</Text><Text className="snap-v">{m.surplus_rate}%</Text></View>
                  <View className="snap-cell"><Text className="snap-k">存款</Text><Text className="snap-v">{fmtNum(m.savings)}</Text></View>
                  <View className="snap-cell"><Text className="snap-k">月成本</Text><Text className="snap-v">{fmtNum(m.cost_total)}</Text></View>
                </View>
              </View>
            );
          })}
          <Button className="btn-clear" onClick={onClear}>清空记录</Button>
        </View>
      )}
    </View>
  );
}
