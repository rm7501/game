// التعريفات والأرقام (التوازن) للعبة
import type { BuildingType, GovId, LuckId, ResId, UnitType, Units, WheelId } from './types';

export const START_YEAR = 2026;
export const DAYS_PER_MONTH = 30;
export const MS_PER_DAY = 200; // بالسرعة العادية: الشهر = 6 ثواني، السنة ≈ 72 ثانية
export const MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];

export interface UnitDef {
  name: string;
  one: string;
  icon: string;
  atk: number;
  def: number;
  cost: number; // مليار
  man: number; // ألف جندي
  days: number;
  upkeep: number; // مليار شهرياً
  tech: number;
  desc: string;
}

export const UNITS: Record<UnitType, UnitDef> = {
  inf: { name: 'مشاة', one: 'فرقة مشاة', icon: '🪖', atk: 1, def: 2, cost: 0.6, man: 10, days: 20, upkeep: 0.015, tech: 1, desc: 'رخيصة وقوية في الدفاع' },
  tank: { name: 'دبابات', one: 'كتيبة دبابات', icon: 'tank', atk: 5, def: 3.5, cost: 2.5, man: 2, days: 40, upkeep: 0.05, tech: 1, desc: 'قوة الهجوم البري الأساسية' },
  jet: { name: 'طائرات مقاتلة', one: 'سرب طائرات', icon: '✈️', atk: 9, def: 6, cost: 7, man: 0.5, days: 70, upkeep: 0.13, tech: 2, desc: 'تفوق جوي +15% لو عندك ضعف طائرات العدو' },
  ship: { name: 'سفن حربية', one: 'سفينة حربية', icon: '🚢', atk: 6, def: 7, cost: 9, man: 1.5, days: 100, upkeep: 0.16, tech: 1, desc: 'لازمة للغزو البحري (كل سفينة تنقل 8 وحدات)' },
  missile: { name: 'صواريخ باليستية', one: 'صاروخ', icon: '🚀', atk: 0, def: 0, cost: 5, man: 0, days: 40, upkeep: 0.02, tech: 2, desc: 'ضربة من بعيد تدمر جزء من جيش العدو' },
  nuke: { name: 'قنابل نووية', one: 'قنبلة نووية', icon: '☢️', atk: 0, def: 0, cost: 120, man: 0, days: 300, upkeep: 0.6, tech: 4, desc: 'دمار شامل.. والعالم كله بيعاديك' },
};

export const SHIP_CAPACITY = 8;
export const emptyUnits = (): Units => ({ inf: 0, tank: 0, jet: 0, ship: 0, missile: 0, nuke: 0 });

export interface BuildingDef {
  name: string;
  icon: string;
  desc: string;
  k: number; // نسبة التكلفة من الناتج
  min: number; // أقل تكلفة
  days: number;
}

export const BUILDINGS: Record<BuildingType, BuildingDef> = {
  industry: { name: 'المصانع', icon: '🏭', desc: '+8% للناتج المحلي لكل مستوى', k: 0.035, min: 3, days: 150 },
  infra: { name: 'البنية التحتية', icon: '🛣️', desc: '+0.6% نمو سنوي و +12% سرعة الجيوش', k: 0.028, min: 2.5, days: 120 },
  research: { name: 'مراكز الأبحاث', icon: '🔬', desc: '+3 نقاط بحث كل شهر', k: 0.03, min: 2.5, days: 140 },
  health: { name: 'الصحة والتعليم', icon: '🏥', desc: '+0.3% نمو سكاني و +4 استقرار', k: 0.022, min: 2, days: 100 },
  fort: { name: 'التحصينات', icon: '🏰', desc: '+10% قوة دفاع لكل مستوى', k: 0.025, min: 2, days: 120 },
  airdef: { name: 'الدفاع الجوي', icon: '📡', desc: 'يعترض 12% من الصواريخ لكل مستوى', k: 0.026, min: 2.5, days: 110 },
  milfac: { name: 'المصانع الحربية', icon: '⚙️', desc: '-6% تكلفة الوحدات و +15% سرعة الإنتاج', k: 0.03, min: 2.5, days: 140 },
  mining: { name: 'استخراج الموارد', icon: '⛏️', desc: '+30% من عائد مواردك الطبيعية', k: 0.025, min: 2, days: 120 },
};
export const BUILD_GROWTH = 1.55;
export const MAX_BUILDING_LEVEL = 10;
export const SLOTS_BY_CLASS = [4, 6, 8, 10, 12, 14];

export interface GovDef {
  name: string;
  icon: string;
  desc: string;
  stab: number;
  income: number;
  growth: number;
  research: number;
  unitCost: number;
  prod: number;
  atk: number;
  buildCost: number;
  buildSpeed: number;
  weariness: number;
  parallel: number;
}
const gov = (o: Partial<GovDef> & Pick<GovDef, 'name' | 'icon' | 'desc'>): GovDef => ({
  stab: 0, income: 1, growth: 0, research: 1, unitCost: 1, prod: 1, atk: 1, buildCost: 1, buildSpeed: 1, weariness: 1, parallel: 0, ...o,
});
export const GOVS: Record<GovId, GovDef> = {
  monarchy: gov({ name: 'ملكية', icon: '👑', desc: '+15 استقرار و +5% دخل', stab: 15, income: 1.05 }),
  democracy: gov({ name: 'ديمقراطية', icon: '🗳️', desc: '+1.5% نمو و +15% بحث، بس الشعب يتعب من الحروب أسرع', stab: 5, growth: 0.015, research: 1.15, weariness: 1.6 }),
  republic: gov({ name: 'جمهورية', icon: '🏛️', desc: 'متوازنة: +5% دخل و +5% بحث و +5 استقرار', stab: 5, income: 1.05, research: 1.05, growth: 0.005 }),
  junta: gov({ name: 'حكم عسكري', icon: '🎖️', desc: '-15% تكلفة الجيش و +25% سرعة إنتاج و +10% هجوم، بس -10 استقرار', stab: -10, unitCost: 0.85, prod: 1.25, atk: 1.1, growth: -0.005 }),
  planned: gov({ name: 'اقتصاد مخطط', icon: '⚙️', desc: 'المباني أرخص 25% وأسرع، وتقدر تبني 3 مباني مع بعض', buildCost: 0.75, buildSpeed: 1.25, growth: -0.005, parallel: 1 }),
  technocracy: gov({ name: 'تكنوقراط', icon: '🧠', desc: '+35% سرعة البحث العلمي', stab: -5, research: 1.35, growth: 0.005 }),
};

export interface ResDef {
  name: string;
  icon: string;
  desc: string;
  gdp: number;
  stab: number;
  popGrowth: number;
  research: number;
}
export const RESOURCES: Record<ResId, ResDef> = {
  oil: { name: 'نفط', icon: '🛢️', desc: '+20% للناتج المحلي', gdp: 0.2, stab: 0, popGrowth: 0, research: 1 },
  gas: { name: 'غاز', icon: '🔥', desc: '+12% للناتج المحلي', gdp: 0.12, stab: 0, popGrowth: 0, research: 1 },
  gold: { name: 'ذهب', icon: '🥇', desc: '+8% للناتج ودخل إضافي من الذهب كل شهر', gdp: 0.08, stab: 0, popGrowth: 0, research: 1 },
  uranium: { name: 'يورانيوم', icon: '☢️', desc: 'برنامج نووي جاهز وقنابل أرخص 40%', gdp: 0.04, stab: 0, popGrowth: 0, research: 1 },
  farm: { name: 'أراضٍ زراعية', icon: '🌾', desc: '+6% للناتج و +0.6% نمو سكاني و +5 استقرار', gdp: 0.06, stab: 5, popGrowth: 0.006, research: 1 },
  rare: { name: 'معادن نادرة', icon: '💎', desc: '+6% للناتج و +25% بحث علمي', gdp: 0.06, stab: 0, popGrowth: 0, research: 1.25 },
  ports: { name: 'موانئ استراتيجية', icon: '⚓', desc: '+8% للناتج، سفن أرخص 25%، والتجارة تجيب أكثر', gdp: 0.08, stab: 0, popGrowth: 0, research: 1 },
  none: { name: 'لا موارد', icon: '🏜️', desc: 'ما عندك شي.. بس شعبك صبور (+8 استقرار)', gdp: 0, stab: 8, popGrowth: 0, research: 1 },
};

export interface LuckDef {
  name: string;
  icon: string;
  desc: string;
  good: boolean;
}
export const LUCK: Record<LuckId, LuckDef> = {
  treasure: { name: 'كنز مدفون', icon: '💰', desc: 'خزينة إضافية ضخمة', good: true },
  nuke: { name: 'رأس نووي', icon: '☢️', desc: 'تبدأ ومعك قنبلة نووية!', good: true },
  mercs: { name: 'جيش مرتزقة', icon: '🪖', desc: '+20 فرقة مشاة و +8 دبابات', good: true },
  genius: { name: 'عقول عبقرية', icon: '🧠', desc: '+1 مستوى تكنولوجيا', good: true },
  fortress: { name: 'حصون منيعة', icon: '🏰', desc: '+3 مستويات تحصينات مجاناً', good: true },
  missiles: { name: 'ترسانة صواريخ', icon: '🚀', desc: '+8 صواريخ باليستية', good: true },
  aid: { name: 'دعم دولي', icon: '🤝', desc: '+80 مليار و +10 استقرار', good: true },
  respin: { name: 'فرصة ثانية', icon: '🎰', desc: '+2 إعادة لف لأي عجلة', good: true },
  plague: { name: 'وباء', icon: '🦠', desc: 'خسرت ربع سكانك', good: false },
  civilwar: { name: 'حرب أهلية', icon: '🔥', desc: 'خسرت 40% من جيشك و -20 استقرار', good: false },
  crisis: { name: 'أزمة اقتصادية', icon: '📉', desc: 'الناتج -25% والخزينة نصها', good: false },
};

// ---------------- العجلات ----------------
export interface Slice {
  label: string;
  sub?: string;
  icon: string;
  w: number;
  v: number | string;
  color?: string;
}
export interface WheelDef {
  id: WheelId;
  title: string;
  icon: string;
  hint: string;
}

export const WHEELS: Record<WheelId, WheelDef> = {
  area: { id: 'area', title: 'عجلة المساحة', icon: '📐', hint: 'تحدد حجم دولتك، وبعدها نختار دولة حقيقية بنفس الحجم' },
  country: { id: 'country', title: 'عجلة المكان', icon: '📍', hint: 'وين بتكون دولتك على خريطة العالم؟' },
  pop: { id: 'pop', title: 'عجلة السكان', icon: '👥', hint: 'عدد شعبك يحدد قوة التجنيد ونمو الاقتصاد' },
  econ: { id: 'econ', title: 'عجلة الاقتصاد', icon: '📈', hint: 'الناتج المحلي = دخلك اللي تبني فيه وتشتري أسلحة' },
  mil: { id: 'mil', title: 'عجلة العسكر', icon: '⚔️', hint: 'الجيش اللي تبدأ فيه' },
  res: { id: 'res', title: 'عجلة الموارد', icon: '⛏️', hint: 'وش تحت أرضك؟' },
  gov: { id: 'gov', title: 'عجلة نظام الحكم', icon: '🏛️', hint: 'كل نظام له مميزات وعيوب' },
  tech: { id: 'tech', title: 'عجلة التكنولوجيا', icon: '🧪', hint: 'كل مستوى يقوي أسلحتك ويفتح أسلحة جديدة' },
  luck: { id: 'luck', title: 'عجلة المفاجأة', icon: '🎁', hint: 'ممكن تطلع لك نعمة.. وممكن نقمة!' },
};

export const AREA_SLICES: Slice[] = [
  { label: 'صغيرة جداً', sub: 'أقل من 25 ألف كم²', icon: '🏝️', w: 18, v: 0 },
  { label: 'صغيرة', sub: '25 – 110 ألف كم²', icon: '🏞️', w: 20, v: 1 },
  { label: 'متوسطة', sub: '110 – 400 ألف كم²', icon: '⛰️', w: 22, v: 2 },
  { label: 'كبيرة', sub: '400 ألف – مليون كم²', icon: '🏔️', w: 18, v: 3 },
  { label: 'ضخمة', sub: '1 – 2.9 مليون كم²', icon: '🏜️', w: 14, v: 4 },
  { label: 'عملاقة', sub: 'أكبر من 2.9 مليون كم²', icon: '🌍', w: 8, v: 5 },
];
export const AREA_NAMES = AREA_SLICES.map((s) => s.label);

const TIER_W = [8, 14, 20, 22, 17, 12, 7];
export const POP_VALUES = [3, 8, 18, 35, 70, 140, 300];
export const POP_SLICES: Slice[] = POP_VALUES.map((v, i) => ({
  label: `${v} مليون`, icon: ['🧍', '👨‍👩‍👦', '👥', '🏘️', '🏙️', '🌆', '🌏'][i], w: TIER_W[i], v: i,
}));

export const ECON_VALUES = [40, 100, 220, 450, 900, 1800, 3500];
export const ECON_NAMES = ['منهار', 'ضعيف', 'نامٍ', 'متوسط', 'قوي', 'غني', 'عملاق'];
export const ECON_SLICES: Slice[] = ECON_VALUES.map((v, i) => ({
  label: ECON_NAMES[i], sub: v >= 1000 ? `${(v / 1000).toFixed(1)} تريليون $` : `${v} مليار $`,
  icon: ['💸', '🪙', '💵', '💰', '🏦', '💎', '👑'][i], w: TIER_W[i], v: i,
}));

export const MIL_NAMES = ['ضعيف جداً', 'ضعيف', 'متواضع', 'متوسط', 'قوي', 'قوي جداً', 'قوة عظمى'];
export const MIL_TIERS: Partial<Units>[] = [
  { inf: 5, tank: 1 },
  { inf: 10, tank: 3, ship: 1 },
  { inf: 18, tank: 7, jet: 1, ship: 2 },
  { inf: 28, tank: 12, jet: 3, ship: 3, missile: 1 },
  { inf: 40, tank: 20, jet: 7, ship: 5, missile: 3 },
  { inf: 60, tank: 32, jet: 12, ship: 8, missile: 6 },
  { inf: 90, tank: 50, jet: 22, ship: 14, missile: 12 },
];
export const MIL_SLICES: Slice[] = MIL_NAMES.map((n, i) => ({
  label: n, icon: ['🏳️', '🔪', '🪖', '🛡️', '⚔️', '🎖️', '💥'][i], w: TIER_W[i], v: i,
}));

export const RES_SLICES: Slice[] = ([
  ['oil', 14], ['gas', 12], ['gold', 10], ['uranium', 7], ['farm', 14], ['rare', 10], ['ports', 12], ['none', 11],
] as [ResId, number][]).map(([id, w]) => ({ label: RESOURCES[id].name, icon: RESOURCES[id].icon, w, v: id }));

export const GOV_SLICES: Slice[] = ([
  ['monarchy', 18], ['democracy', 18], ['republic', 20], ['junta', 15], ['planned', 14], ['technocracy', 15],
] as [GovId, number][]).map(([id, w]) => ({ label: GOVS[id].name, icon: GOVS[id].icon, w, v: id }));

export const TECH_NAMES = ['', 'بدائية', 'أساسية', 'متقدمة', 'متطورة', 'مستقبلية', 'خارقة'];
export const TECH_SLICES: Slice[] = [1, 2, 3, 4, 5].map((lv, i) => ({
  label: TECH_NAMES[lv], sub: `مستوى ${lv}`, icon: ['🪨', '🔧', '💻', '🛰️', '🤖'][i], w: [20, 30, 27, 15, 8][i], v: lv,
}));

export const LUCK_SLICES: Slice[] = ([
  ['treasure', 13], ['nuke', 4], ['mercs', 12], ['genius', 10], ['fortress', 9], ['missiles', 10], ['aid', 10],
  ['respin', 7], ['plague', 9], ['civilwar', 7], ['crisis', 9],
] as [LuckId, number][]).map(([id, w]) => ({ label: LUCK[id].name, icon: LUCK[id].icon, w, v: id }));

export const STATIC_SLICES: Partial<Record<WheelId, Slice[]>> = {
  area: AREA_SLICES, pop: POP_SLICES, econ: ECON_SLICES, mil: MIL_SLICES, res: RES_SLICES,
  gov: GOV_SLICES, tech: TECH_SLICES, luck: LUCK_SLICES,
};

// ---------------- التكنولوجيا ----------------
export const TECH_COST = [0, 0, 80, 200, 400, 700, 1100]; // نقاط للوصول للمستوى
export const MAX_TECH = 6;
export const techMult = (t: number) => 1 + 0.2 * (t - 1);
export const missileRange = (t: number) => (t >= 5 ? 40000 : [0, 1500, 2500, 4000, 7000][t] ?? 1500);
export const navalRange = (t: number) => 2000 + 1200 * (t - 1);
export const NUKE_PROJECT = { cost: 80, days: 720, tech: 4 };

// ---------------- ألوان الدول ----------------
export const NATION_COLORS = [
  '#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#bfef45',
  '#fabed4', '#469990', '#dcbeff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000',
  '#ffd8b1', '#000075', '#ffe119', '#a9a9a9', '#e6beff', '#ff6f61', '#6b5b95', '#88b04b',
  '#f7cac9', '#92a8d1', '#955251', '#b565a7', '#009b77', '#dd4124', '#d65076', '#45b8ac',
];

export const BOT_NAMES = [
  'الذئب الأحمر', 'القائد صقر', 'الجنرال فهد', 'الإمبراطور نمر', 'السلطان برق', 'المارشال رعد',
  'الأميرال موج', 'الحكيم سهيل', 'الداهية مهند', 'الفارس نايف', 'الثعلب الماكر', 'الملك الأسود',
  'الجنرال عاصفة', 'القيصر حديد', 'الشيخ زاهر', 'الدكتاتور بركان', 'المستشار ذهب', 'الأمير ليث',
  'البارون جليد', 'القائدة لمى', 'الجنرالة ريم', 'الملكة شهد', 'الكابتن ماجد', 'الوزير حاتم',
];
