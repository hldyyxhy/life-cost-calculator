// index.ts —— 公共 API barrel（calc_engine 全部计算逻辑 + 数据模块已翻译完成）
// 小程序/Web UI 统一从此处导入。零第三方依赖，离线端侧计算。
// 注：仅导出页面/组件实际使用的符号，内部工具不导出（配合 sideEffects:false 让 webpack tree-shake）。

// —— 计算函数（页面直接消费）——
export { computeCurrentSituation } from './calc/situation';
export { computeLifeCost } from './calc/lifeCost';
export { computeSurplus, estimateTargetWage } from './calc/family';
export { computeOvertimePay, computeMinWageCheck, assessOvertimeClaim } from './calc/rights';
export {
  computeLoanApr, compareLoanMethods, computeAffordableDebt,
} from './calc/loan';
export { simulateDebtPayoff, simulateLoanSpiral, assessDebtHealth } from './calc/debt';
export { compareBuyRent, housingFundLoan, rateStressTest } from './calc/housing';
export { bonusTaxCompare, specialDeductionHints } from './calc/tax';
export { compareCities } from './calc/compare';
export { checkRelief } from './calc/relief';
export { moneyFmt } from './calc/money';

// —— 提示词生成（22 个 build_*_prompt + profileBrief + 场景库）——
export {
  profileBrief, buildOvertimePrompt, buildLoanAprPrompt, buildCompareMethodsPrompt, buildAffordableDebtPrompt,
  buildDebtPayoffPrompt, buildSpiralPrompt, buildMinWagePrompt, buildUnemploymentPrompt, buildSubsidyPrompt,
  buildHelpPrompt, buildAntifraudPrompt, buildCurrentSituationPrompt, buildMilestonesPrompt, buildComparePrompt,
  buildInjuryPrompt, buildBuyRentPrompt, buildFundPrompt, buildRateStressPrompt, buildTaxPrompt,
  buildAssistancePrompt, buildMedicalPrompt, buildDebtHealthPrompt, HELP_SCENARIOS, FRAUD_TYPES,
} from './calc/prompts';

// —— 数据查询（页面直接消费）——
export {
  estimateUnemploymentPay, unemployDuration,
  calcInjuryOneTime, calcInjuryPension, getProvinceInjuryExtra,
} from './data/rights';
export { estimateInpatient } from './data/medical';
export { getDibaoForCity } from './data/relief';

// —— cost 数据函数（页面直接消费）——
export {
  cityFactor, adjustByTier,
  calcPersonalIncomeTax,
} from './data/cost';

// —— 数据模型（profile/tracking/report）——
export {
  FIELD_DEFS, GROUP_TITLES, WIZARD_STEPS,
  defaultProfile, autoMapTier, validateProfile,
  profileToJson, profileFromJson, saveLastProfile, loadLastProfile,
} from './profile';
export { metricsFrom, safeName, toNum } from './tracking';
export { buildFullReport } from './report';

// —— 类型 ——
export type {
  Tier, InsuranceMode, FoodLevel, HousingMode, ChildSeg,
  CostRow, SituationInput, SituationResult,
} from './types';
