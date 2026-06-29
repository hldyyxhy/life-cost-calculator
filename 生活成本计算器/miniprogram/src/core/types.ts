// types.ts —— 全局类型定义（对应 Python cost_data 的字面量 + calc_engine 的 dict 结构）
// 字面量联合来自 cost_data.py 的常量键，TS 端集中管理避免中文全角括号写错。

/** 城市等级（cost_data.TIER_KEYS） */
export type Tier = '一线' | '新一线' | '二线' | '三线' | '四线' | '五线';

/** 社保模式 */
export type InsuranceMode = '在职（单位缴）' | '灵活就业（全自缴）' | '不缴社保';

/** 饮食档次（cost_data.LIFESTYLE_FACTOR 的键） */
export type FoodLevel = '节俭' | '普通' | '宽裕';

/** 住房方式（compute_current_situation 的 housing 参数取值） */
export type HousingMode =
  | '合租单间'
  | '一居室整租'
  | '已购房（还月供）'
  | '免租';

/** 子女年龄段（cost_data.CHILD_CARE_MONTHLY_BASE 的键） */
export type ChildSeg =
  | '3岁以下（婴幼儿）'
  | '幼儿园（3-6岁）'
  | '中小学（6-18岁）'
  | '大学在读（18岁+）';

/** 成本明细行（对应 cost_rows，_cat 为内部类别字段，对外可剥离） */
export interface CostRow {
  item: string;
  amount: number;
  note: string;
  _cat?: string | null;
}

/** computeCurrentSituation 输入（Python 14 参数 → options 对象） */
export interface SituationInput {
  age: number;
  wagePretax: number;
  tier: Tier | string;
  housing: HousingMode | string;
  foodLevel: FoodLevel | string;
  hasCar?: boolean;
  insuranceMode?: InsuranceMode | string;
  numChildren?: number;
  /** {段: 人数}；空且 numChildren>0 时兜底归「中小学」 */
  childrenByAge?: Record<string, number> | null;
  supportElderly?: boolean;
  hasHousingDeduction?: boolean;
  hasContinuingEducation?: boolean;
  supportFamilyMonthly?: number;
  /** {类别: 实际月额}；val 为 null 表示清除该类别 */
  overrides?: Record<string, number | null> | null;
}

/** computeCurrentSituation 返回（对应 Python 返回 dict，键名保持蛇形以便对拍） */
export interface SituationResult {
  cost_rows: CostRow[];
  breakdown: Record<string, number>;
  cost_total: number;
  survival_baseline: number;
  social_ins: number;
  tax: number;
  tax_rate: number;
  income_net: number;
  surplus: number;
  surplus_rate: number;
  house_saving_years: number | null;
  special_total: number;
  interpretation: string;
  assumptions: string[];
}
