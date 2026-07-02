// constants.ts —— 各页共享的常量（从 4 个页面提取去重）

export const TIERS = ['一线', '新一线', '二线', '三线', '四线', '五线'];
export const HOUSINGS = ['合租单间', '一居室整租', '已购房（还月供）', '免租'];
export const FOODS = ['节俭', '普通', '宽裕'];
export const INSURANCES = ['在职（单位缴）', '灵活就业（全自缴）', '不缴社保'];

// breakdown key → 中文 label（处境页 overrides 弹窗用）
export const CAT_CN: Record<string, string> = {
  '住房': '住房', '饮食': '饮食', '交通': '交通',
  '通讯日用': '通讯日用', '社保': '社保', '给老家': '给老家',
};
