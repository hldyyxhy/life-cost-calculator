// profile.ts —— 用户档案数据模型（翻译自 profile.py）
// 表单配置 + 校验/迁移 + 序列化。文件持久化留 UI 层注入 storage（core 平台无关）。
import costRaw from './data/cost.json';

const C = costRaw as unknown as Record<string, any>;
const CITY_TO_TIER = C.CITY_TO_TIER as Record<string, string>;

/** 控件类型 */
export type CType = 'spin' | 'entry' | 'combo' | 'check';

/** 字段定义（对应 Python FIELD_DEFS 的元组） */
export interface FieldDef {
  key: string;
  default: any;
  label: string;
  ctype: CType;
  meta: any; // spin:[min,max] / combo:选项[] / check:null / entry:说明
}

export type Profile = Record<string, any>;

/** 档案结构定义（6 组）——对应 profile.py:31 FIELD_DEFS */
export const FIELD_DEFS: Record<string, FieldDef[]> = {
  basic: [
    { key: 'name', default: '', label: '姓名（可选）', ctype: 'entry', meta: '用于区分多份长期跟踪档案' },
    { key: 'age', default: 30, label: '年龄', ctype: 'spin', meta: [16, 80] },
    { key: 'gender', default: '男', label: '性别', ctype: 'combo', meta: ['男', '女'] },
    { key: 'city', default: '', label: '所在城市', ctype: 'entry', meta: '如 北京/成都' },
    { key: 'tier', default: '三线', label: '城市等级', ctype: 'combo', meta: ['一线', '新一线', '二线', '三线', '四线', '五线'] },
    { key: 'health', default: '健康（无慢性病）', label: '健康状况', ctype: 'combo', meta: ['健康（无慢性病）', '有慢性病（需长期用药）', '需定期就医'] },
  ],
  income: [
    { key: 'wage', default: '', label: '本人税前月薪（元）', ctype: 'entry', meta: '留空则用本城市典型月薪' },
    { key: 'insurance', default: '在职（单位缴）', label: '社保类型', ctype: 'combo', meta: ['在职（单位缴）', '灵活就业（全自缴）', '不缴社保'] },
    { key: 'has_side_income', default: false, label: '有副业/兼职收入', ctype: 'check', meta: null },
    { key: 'side_income', default: '', label: '副业月收入（元）', ctype: 'entry', meta: '到手估算' },
  ],
  living: [
    { key: 'housing', default: '合租单间', label: '住房方式', ctype: 'combo', meta: ['合租单间', '一居室整租', '已购房（还月供）', '免租'] },
    { key: 'food', default: '普通', label: '饮食档次', ctype: 'combo', meta: ['节俭', '普通', '宽裕'] },
    { key: 'has_car', default: false, label: '养车', ctype: 'check', meta: null },
    { key: 'support_family', default: '', label: '给老家生活费（元/月）', ctype: 'entry', meta: '0 或留空表示不给' },
  ],
  partner: [
    { key: 'has_partner', default: false, label: '有伴侣/配偶', ctype: 'check', meta: null },
    { key: 'partner_wage', default: '', label: '伴侣税前月薪（元）', ctype: 'entry', meta: '留空则用本城市典型月薪' },
    { key: 'partner_insurance', default: '在职（单位缴）', label: '伴侣社保', ctype: 'combo', meta: ['在职（单位缴）', '灵活就业（全自缴）', '不缴社保'] },
  ],
  family: [
    { key: 'num_children', default: 0, label: '子女数量', ctype: 'spin', meta: [0, 6] },
    { key: 'child_baby', default: 0, label: '　3岁以下（婴幼儿）几人', ctype: 'spin', meta: [0, 6] },
    { key: 'child_kg', default: 0, label: '　幼儿园（3-6岁）几人', ctype: 'spin', meta: [0, 6] },
    { key: 'child_school', default: 0, label: '　中小学（6-18岁）几人', ctype: 'spin', meta: [0, 6] },
    { key: 'child_uni', default: 0, label: '　大学在读（18岁+）几人', ctype: 'spin', meta: [0, 6] },
    { key: 'support_elderly', default: false, label: '赡养老人（个税专项扣除）', ctype: 'check', meta: null },
    { key: 'has_housing_deduction', default: false, label: '有住房租金/房贷利息扣除', ctype: 'check', meta: null },
    { key: 'has_continuing_education', default: false, label: '本人继续教育（+400元/月）', ctype: 'check', meta: null },
  ],
  finance: [
    { key: 'mortgage_monthly', default: '', label: '房贷月供（元，另计/非默认）', ctype: 'entry', meta: "留空用默认" },
    { key: 'car_loan_monthly', default: '', label: '车贷月供（元）', ctype: 'entry', meta: '0 或留空' },
    { key: 'savings', default: '', label: '现有存款/应急金（元）', ctype: 'entry', meta: '用于估算失业能撑多久' },
    { key: 'social_expense', default: '', label: '人情/娱乐月支出（元）', ctype: 'entry', meta: '0 或留空' },
  ],
};

/** 组标题 */
export const GROUP_TITLES: Record<string, string> = {
  basic: '一、本人基础',
  income: '二、收入与社保',
  living: '三、居住与生活方式',
  partner: '四、伴侣（双收入）',
  family: '五、家庭负担',
  finance: '六、负债与资产（抗风险）',
};

/** 向导步骤；show_if 为空总显示，否则按已答 dict 决定是否出现（智能跳过） */
export interface WizardField {
  key: string;
  show_if?: (a: Profile) => boolean;
}
export interface WizardStep {
  title: string;
  fields: WizardField[];
}
export const WIZARD_STEPS: WizardStep[] = [
  { title: '先认识一下', fields: [{ key: 'name' }, { key: 'age' }, { key: 'gender' }, { key: 'city' }] },
  {
    title: '你的收入',
    fields: [
      { key: 'wage' }, { key: 'insurance' }, { key: 'has_side_income' },
      { key: 'side_income', show_if: (a) => !!a.has_side_income },
    ],
  },
  { title: '住和吃、出行', fields: [{ key: 'housing' }, { key: 'food' }, { key: 'has_car' }] },
  {
    title: '成家了吗',
    fields: [
      { key: 'has_partner' },
      { key: 'partner_wage', show_if: (a) => !!a.has_partner },
      { key: 'partner_insurance', show_if: (a) => !!a.has_partner },
    ],
  },
  {
    title: '孩子和老人',
    fields: [
      { key: 'num_children' },
      { key: 'child_baby', show_if: (a) => (a.num_children ?? 0) > 0 },
      { key: 'child_kg', show_if: (a) => (a.num_children ?? 0) > 0 },
      { key: 'child_school', show_if: (a) => (a.num_children ?? 0) > 0 },
      { key: 'child_uni', show_if: (a) => (a.num_children ?? 0) > 0 },
      { key: 'support_elderly' },
    ],
  },
  {
    title: '负债和存款',
    fields: [
      { key: 'mortgage_monthly' },
      { key: 'car_loan_monthly', show_if: (a) => !!a.has_car },
      { key: 'savings' }, { key: 'social_expense' },
    ],
  },
  {
    title: '其他（都可留空）',
    fields: [{ key: 'health' }, { key: 'support_family' }, { key: 'has_housing_deduction' }, { key: 'has_continuing_education' }],
  },
];

/** default_profile：生成默认（空）档案。 */
export function defaultProfile(): Profile {
  const profile: Profile = {};
  for (const fields of Object.values(FIELD_DEFS)) {
    for (const f of fields) profile[f.key] = f.default;
  }
  return profile;
}

/** auto_map_tier：按 city 自动匹配城市等级写入 tier；匹配不到则保留。 */
export function autoMapTier(profile: Profile): Profile {
  const city = String(profile.city ?? '').trim();
  if (city) {
    const tier = CITY_TO_TIER[city];
    if (tier) profile.tier = tier;
  }
  return profile;
}

// 旧档案 child_age_group（单值）→ child_* 段字段
const OLD_CHILD_SEG_TO_FIELD: Record<string, string> = {
  '3岁以下（婴幼儿）': 'child_baby',
  '幼儿园（3-6岁）': 'child_kg',
  '中小学（6-18岁）': 'child_school',
  '大学在读（18岁+）': 'child_uni',
};

/** validate_profile：用 FIELD_DEFS 校验补全（丢弃多余、补缺失、空串保留、旧版迁移）。 */
export function validateProfile(raw: any): Profile {
  raw = { ...(raw || {}) };
  if ('child_age_group' in raw) {
    const oldSeg = raw.child_age_group;
    delete raw.child_age_group;
    const n = (raw.num_children ?? 0) || 0;
    const field = OLD_CHILD_SEG_TO_FIELD[oldSeg] ?? 'child_school';
    const childFields = Object.values(OLD_CHILD_SEG_TO_FIELD);
    if (!childFields.some((f) => raw[f])) raw[field] = n;
  }
  const result = defaultProfile();
  const allKeys = new Set<string>();
  for (const fields of Object.values(FIELD_DEFS)) for (const f of fields) allKeys.add(f.key);
  for (const k of allKeys) {
    if (k in raw) result[k] = raw[k];
  }
  return result;
}

/** 档案 → JSON 字符串（中文不转义）。 */
export function profileToJson(profile: Profile, pretty = true): string {
  return JSON.stringify(profile, null, pretty ? 2 : undefined);
}

/** JSON 字符串 → 档案（经 validate 校验补全）。 */
export function profileFromJson(text: string): Profile {
  return validateProfile(JSON.parse(text));
}

/**
 * 持久化抽象：UI 层注入符合该接口的 storage（小程序 wx.getStorageSync/setStorageSync
 * 或浏览器 localStorage）。core 不直接依赖平台 API。
 */
export interface ProfileStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}
const LAST_KEY = 'last_profile.json';

/** save_last_profile：存「上次档案」。失败静默。 */
export function saveLastProfile(storage: ProfileStorage, profile: Profile): void {
  try {
    storage.setItem(LAST_KEY, profileToJson(profile, true));
  } catch (e) {
    // 静默
  }
}

/** load_last_profile：读「上次档案」；不存在/损坏返回 null。 */
export function loadLastProfile(storage: ProfileStorage): Profile | null {
  const text = storage.getItem(LAST_KEY);
  if (text === null) return null;
  try {
    return profileFromJson(text);
  } catch (e) {
    return null;
  }
}
