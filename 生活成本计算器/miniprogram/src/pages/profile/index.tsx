import { useState, useRef } from 'react';
import { View, Text, Input, Picker, Switch, Button } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import { FIELD_DEFS, GROUP_TITLES, defaultProfile, validateProfile, autoMapTier, saveLastProfile, loadLastProfile } from '../../core';
import { taroStorage } from '../../utils/storage';
import WizardModal from '../../components/WizardModal';
import './index.scss';

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(() => loadLastProfile(taroStorage) || defaultProfile());
  const [showWizard, setShowWizard] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['basic']));
  const hasChecked = useRef(false);

  useDidShow(() => {
    const p = loadLastProfile(taroStorage);
    if (p) {
      setProfile(p);
    } else if (!hasChecked.current) {
      // 首次启动（无档案）→ 弹分步向导，避免面对一长页表单
      setShowWizard(true);
    }
    hasChecked.current = true;
  });

  const setField = (key: string, val: any) => {
    setProfile((p: any) => {
      const np = { ...p, [key]: val };
      if (key === 'city') np.tier = autoMapTier({ ...np }).tier ?? np.tier;
      return np;
    });
  };

  const onSave = () => {
    const valid = validateProfile(profile);
    autoMapTier(valid);
    saveLastProfile(taroStorage, valid);
    Taro.showToast({ title: '已保存', icon: 'success' });
  };

  const onWizardComplete = (prof: any) => {
    saveLastProfile(taroStorage, prof);
    setProfile(prof);
    setShowWizard(false);
    Taro.switchTab({ url: '/pages/situation/index' });
  };

  const renderField = (f: any) => {
    const val = profile[f.key];
    if (f.ctype === 'check') {
      return (
        <View className="field-row" key={f.key}>
          <Text className="field-label">{f.label}</Text>
          <Switch checked={!!val} onChange={(e) => setField(f.key, e.detail.value)} color="#e8843c" />
        </View>
      );
    }
    if (f.ctype === 'combo') {
      const opts = f.meta as string[];
      const idx = Math.max(0, opts.indexOf(val));
      return (
        <View className="field-row" key={f.key}>
          <Text className="field-label">{f.label}</Text>
          <Picker mode="selector" range={opts} value={idx} onChange={(e) => setField(f.key, opts[Number(e.detail.value)])}>
            <View className="picker">{val}</View>
          </Picker>
        </View>
      );
    }
    if (f.ctype === 'spin') {
      const [mn] = f.meta as [number, number];
      return (
        <View className="field-row" key={f.key}>
          <Text className="field-label">{f.label}</Text>
          <Input
            className="input"
            type="number"
            value={String(val)}
            onInput={(e) => {
              const v = e.detail.value;
              if (v === '') { setField(f.key, ''); return; }
              const n = Number(v);
              setField(f.key, isNaN(n) ? mn : n);
            }}
          />
        </View>
      );
    }
    const cityTier = f.key === 'city' && val ? autoMapTier({ city: String(val).trim(), tier: '' }).tier : '';
    return (
      <View className="field-row entry-col" key={f.key}>
        <View className="entry-main">
          <Text className="field-label">{f.label}</Text>
          <Input className="input" value={String(val ?? '')} placeholder={String(f.meta || '')} onInput={(e) => setField(f.key, e.detail.value)} />
        </View>
        {f.key === 'city' && val && (
          <Text className={`city-hint ${cityTier ? 'ok' : 'no'}`}>
            {cityTier ? `✓ 已匹配：${cityTier}` : '未识别，请填标准城市名（如 北京/成都/台州）'}
          </Text>
        )}
      </View>
    );
  };

  return (
    <View className="page">
      {Object.entries(FIELD_DEFS).map(([group, fields]: [string, any]) => (
        <View className="card group" key={group}>
          <View className="group-title" onClick={() => {
            const next = new Set(expanded);
            if (next.has(group)) next.delete(group); else next.add(group);
            setExpanded(next);
          }}>{expanded.has(group) ? '▼' : '▶'} {GROUP_TITLES[group]}</View>
          {expanded.has(group) && (fields as any[]).map(renderField)}
        </View>
      ))}
      <Button className="btn-primary" onClick={onSave}>保存档案</Button>
      <View className="hint">填一次档案，各计算页都会自动带入了。城市等级按城市名自动匹配。</View>

      {/* 首次启动向导 */}
      {showWizard && <WizardModal onComplete={onWizardComplete} />}
    </View>
  );
}
