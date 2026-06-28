// index.ts —— 公共 API barrel（calc_engine 全部计算逻辑 + 数据模块已翻译完成）
// 小程序/Web UI 统一从此处导入。零第三方依赖，离线端侧计算。

// —— 计算函数 ——
export { computeCurrentSituation } from './calc/situation';
export { survivalBaseline } from './calc/survival';
export { normalizeChildrenByAge } from './calc/normalizeChildren';
export { computeLifeCost } from './calc/lifeCost';
export { computeFamilySituation, computeRiskIndicators, computeSurplus, estimateTargetWage } from './calc/family';
export { computeOvertimePay, computeMinWageCheck, assessOvertimeClaim } from './calc/rights';
export {
  computeLoanApr, compareLoanMethods, computeAffordableDebt,
  solveMonthlyIrr, annualIrrFromMonthly, levelFromAnnualIrr, monthlyPayment, remainingPrincipal,
} from './calc/loan';
export { simulateDebtPayoff, simulateLoanSpiral, assessDebtHealth } from './calc/debt';
export { compareBuyRent, housingFundLoan, rateStressTest } from './calc/housing';
export { bonusTaxCompare, specialDeductionHints } from './calc/tax';
export { compareCities } from './calc/compare';
export { checkRelief, estimateMedicalCost } from './calc/relief';
export { moneyFmt } from './calc/money';

// —— 提示词生成（22 个 build_*_prompt + profileBrief + 场景库）——
export {
  profileBrief, buildOvertimePrompt, buildLoanAprPrompt, buildCompareMethodsPrompt, buildAffordableDebtPrompt,
  buildDebtPayoffPrompt, buildSpiralPrompt, buildMinWagePrompt, buildUnemploymentPrompt, buildSubsidyPrompt,
  buildHelpPrompt, buildAntifraudPrompt, buildCurrentSituationPrompt, buildMilestonesPrompt, buildComparePrompt,
  buildInjuryPrompt, buildBuyRentPrompt, buildFundPrompt, buildRateStressPrompt, buildTaxPrompt,
  buildAssistancePrompt, buildMedicalPrompt, buildDebtHealthPrompt, HELP_SCENARIOS, FRAUD_TYPES,
} from './calc/prompts';

// —— 数据查询（rights/medical/relief 各地政策）——
export {
  getMinWageForCity, estimateUnemploymentPay, unemployDuration,
  calcInjuryOneTime, calcInjuryPension, getProvinceInjuryExtra,
} from './data/rights';
export { estimateInpatient, getEmployeeRate } from './data/medical';
export { getDibaoForCity, getTekunForCity } from './data/relief';

// —— cost 数据函数 ——
export {
  cityFactor, raiseFactor, adjustByTier, adjustByTierLevel,
  calcPersonalIncomeTax, calcAnnualIncomeTax, bonusMonthlyRate,
} from './data/cost';

// —— 数据模型（profile/tracking/report）——
export {
  FIELD_DEFS, GROUP_TITLES, WIZARD_STEPS,
  defaultProfile, autoMapTier, validateProfile,
  profileToJson, profileFromJson, saveLastProfile, loadLastProfile,
} from './profile';
export { metricsFrom, renderTxt, safeName, toNum } from './tracking';
export { buildFullReport, fmtNow } from './report';

// —— 类型 ——
export type {
  Tier, InsuranceMode, FoodLevel, HousingMode, ChildSeg,
  CostRow, SituationInput, SituationResult,
} from './types';
