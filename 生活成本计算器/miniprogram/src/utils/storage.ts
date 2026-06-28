import Taro from '@tarojs/taro';

// ProfileStorage 接口（与 core 一致，本地定义避免 import core.bundle 的类型）
interface ProfileStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export const taroStorage: ProfileStorage = {
  getItem(key: string): string | null {
    try {
      const v = Taro.getStorageSync(key);
      if (v === '' || v === undefined || v === null) return null;
      return typeof v === 'string' ? v : JSON.stringify(v);
    } catch {
      return null;
    }
  },
  setItem(key: string, value: string): void {
    try {
      Taro.setStorageSync(key, value);
    } catch {
      // 静默
    }
  },
};
