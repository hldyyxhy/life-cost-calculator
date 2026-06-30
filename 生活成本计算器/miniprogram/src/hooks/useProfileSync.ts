// useProfileSync —— 从档案预填（useDidShow + loadLastProfile 的共享 hook）
// 用法：useProfileSync((p) => { setWage(String(p.wage ?? '')); setTierIdx(...); });
import { useDidShow } from '@tarojs/taro';
import { loadLastProfile } from '../core';
import { taroStorage } from '../utils/storage';

export function useProfileSync(callback: (profile: any) => void): void {
  useDidShow(() => {
    const p = loadLastProfile(taroStorage);
    if (p) callback(p);
  });
}
