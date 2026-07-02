// WizardModal —— 首次填写向导（移植 Python page_wizard.py + profile.WIZARD_STEPS）
// 7 步分步填写，show_if 智能跳过（没伴侣不问伴侣薪资、没孩子不问年龄等）
import { useState } from 'react';
import { View, Text, Input, Picker, Switch, Button, ScrollView } from '@tarojs/components';
import { WIZARD_STEPS, FIELD_DEFS, defaultProfile, autoMapTier, validateProfile } from '../core';
import './WizardModal.scss';

// 从 FIELD_DEFS 查找字段定义
function findDef(key: string): any {
  for (const fields of Object.values(FIELD_DEFS)) {
    const f = (fields as any[]).find((fd) => fd.key === key);
    if (f) return f;
  }
  return null;
}

export default function WizardModal({ onComplete, onSkip }: { onComplete: (profile: any) => void; onSkip?: () => void }) {
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<any>(defaultProfile());

  const setField = (key: string, val: any) => {
    setProfile((p: any) => {
      const np = { ...p, [key]: val };
      if (key === 'city') np.tier = autoMapTier({ ...np }).tier ?? np.tier;
      return np;
    });
  };

  const stepData = WIZARD_STEPS[step];
  // show_if 过滤：不满足条件的字段不显示
  const fields = stepData.fields.filter((f: any) => !f.show_if || f.show_if(profile));

  const renderField = (key: string) => {
    const f = findDef(key);
    if (!f) return null;
    const val = profile[f.key];

    if (f.ctype === 'check') {
      return (
        <View className="wz-field" key={key}>
          <Text className="wz-label">{f.label}</Text>
          <Switch checked={!!val} onChange={(e) => setField(key, e.detail.value)} color="#e8843c" />
        </View>
      );
    }
    if (f.ctype === 'combo') {
      const opts = f.meta as string[];
      const idx = Math.max(0, opts.indexOf(val));
      return (
        <View className="wz-field" key={key}>
          <Text className="wz-label">{f.label}</Text>
          <Picker mode="selector" range={opts} value={idx} onChange={(e) => setField(key, opts[Number(e.detail.value)])}>
            <View className="wz-picker">{val} ›</View>
          </Picker>
        </View>
      );
    }
    if (f.ctype === 'spin') {
      return (
        <View className="wz-field" key={key}>
          <Text className="wz-label">{f.label}</Text>
          <Input className="wz-input" type="number" value={String(val)} onInput={(e) => {
            const v = e.detail.value;
            setField(key, v === '' ? '' : (Number(v) || 0));
          }} />
        </View>
      );
    }
    // entry
    const cityTier = key === 'city' && val ? autoMapTier({ city: String(val).trim(), tier: '' }).tier : '';
    return (
      <View className="wz-field wz-entry" key={key}>
        <Text className="wz-label">{f.label}</Text>
        <Input className="wz-input" value={String(val ?? '')} placeholder={String(f.meta || '')} onInput={(e) => setField(key, e.detail.value)} />
        {key === 'city' && val && (
          <Text className={`wz-city-hint ${cityTier ? 'ok' : 'no'}`}>{cityTier ? `✓ ${cityTier}` : '未识别'}</Text>
        )}
      </View>
    );
  };

  const isLast = step >= WIZARD_STEPS.length - 1;
  const onFinish = () => {
    const valid = validateProfile(profile);
    autoMapTier(valid);
    onComplete(valid);
  };

  return (
    <View className="wz-mask">
      <View className="wz-modal" catchMove>
        {/* 进度条 */}
        <View className="wz-progress-bar">
          {WIZARD_STEPS.map((_: any, i: number) => (
            <View key={i} className={`wz-dot ${i <= step ? 'active' : ''}`} />
          ))}
        </View>

        <View className="wz-header">
          <Text className="wz-step-num">第 {step + 1} 步 / 共 {WIZARD_STEPS.length} 步</Text>
          <Text className="wz-step-title">{stepData.title}</Text>
        </View>

        <ScrollView scrollY className="wz-body">
          {fields.map((f: any) => renderField(f.key))}
          {fields.length === 0 && <Text className="wz-skip">这一步没有需要填的，直接下一步</Text>}
        </ScrollView>

        <View className="wz-actions">
          {step > 0 && <Button className="wz-btn-prev" onClick={() => setStep(step - 1)}>上一步</Button>}
          {isLast ? (
            <Button className="wz-btn-next" onClick={onFinish}>完成，开始用</Button>
          ) : (
            <Button className="wz-btn-next" onClick={() => setStep(step + 1)}>下一步</Button>
          )}
        </View>
        {step === 0 && onSkip && <Text className="wz-skip-link" onClick={onSkip}>以后再说，先看看</Text>}
      </View>
    </View>
  );
}
