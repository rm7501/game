// التعريفات والأرقام (التوازن) للعبة
import type {
  BuildingType, FortuneId, GovId, LeaderId, LuckId, MissionId, ResId, TerrainId, UnitType, Units, WheelId, WorldEventId,
} from './types';

export const START_YEAR = 2026;
export const DAYS_PER_MONTH = 30;
export const MS_PER_DAY = 320; // بالسرعة العادية: الشهر ≈ 10 ثواني، السنة ≈ دقيقتين
export const MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];
/** دقائق اللعب الحقيقية لكل سنة بالسرعة العادية */
export const MINUTES_PER_YEAR = (360 * MS_PER_DAY) / 60000;

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
  infra: { name: 'البنية التحتية', icon: '🛣️', desc: '+0.4% نمو سنوي و +12% سرعة الجيوش', k: 0.028, min: 2.5, days: 120 },
  research: { name: 'مراكز الأبحاث', icon: '🔬', desc: '+2.5 نقطة بحث كل شهر', k: 0.03, min: 2.5, days: 140 },
  health: { name: 'الصحة والتعليم', icon: '🏥', desc: '+0.3% نمو سكاني و +4 استقرار', k: 0.022, min: 2, days: 100 },
  fort: { name: 'التحصينات', icon: '🏰', desc: '+10% قوة دفاع لكل مستوى', k: 0.025, min: 2, days: 120 },
  airdef: { name: 'الدفاع الجوي', icon: '📡', desc: 'يعترض 12% من الصواريخ لكل مستوى', k: 0.026, min: 2.5, days: 110 },
  milfac: { name: 'المصانع الحربية', icon: '⚙️', desc: '-6% تكلفة الوحدات و +15% سرعة الإنتاج', k: 0.03, min: 2.5, days: 140 },
  mining: { name: 'استخراج الموارد', icon: '⛏️', desc: '+30% من عائد مواردك الطبيعية', k: 0.025, min: 2, days: 120 },
};
export const BUILD_GROWTH = 1.55;
export const MAX_BUILDING_LEVEL = 10;
export const SLOTS_BY_CLASS = [4, 6, 8, 10, 12, 14];

// ---------------- أنظمة الحكم ----------------
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
  constitutional: gov({ name: 'ملكية دستورية', icon: '📜', desc: '+10 استقرار و +0.5% نمو و +3% دخل', stab: 10, growth: 0.005, income: 1.03 }),
  oligarchy: gov({ name: 'حكم الأثرياء', icon: '🏦', desc: '+15% دخل، بس الشعب أقل رضا (-8 استقرار)', stab: -8, income: 1.15 }),
  transitional: gov({ name: 'حكومة انتقالية', icon: '🌀', desc: 'فوضى مؤقتة (-15 استقرار)، وبعد 4 سنوات تنلف عجلة الحكم من جديد!', stab: -15, income: 0.95 }),
};

// ---------------- الموارد ----------------
export interface ResDef {
  name: string;
  icon: string;
  desc: string;
  gdp: number;
  stab: number;
  popGrowth: number;
  research: number;
  buildCost: number;
}
const res = (o: Partial<ResDef> & Pick<ResDef, 'name' | 'icon' | 'desc'>): ResDef => ({ gdp: 0, stab: 0, popGrowth: 0, research: 1, buildCost: 1, ...o });
export const RESOURCES: Record<ResId, ResDef> = {
  oil: res({ name: 'نفط', icon: '🛢️', desc: '+20% للناتج المحلي', gdp: 0.2 }),
  gas: res({ name: 'غاز', icon: '🔥', desc: '+12% للناتج المحلي', gdp: 0.12 }),
  gold: res({ name: 'ذهب', icon: '🥇', desc: '+8% للناتج ودخل إضافي من الذهب كل شهر', gdp: 0.08 }),
  uranium: res({ name: 'يورانيوم', icon: '☢️', desc: 'برنامج نووي جاهز وقنابل أرخص 40%', gdp: 0.04 }),
  farm: res({ name: 'أراضٍ زراعية', icon: '🌾', desc: '+6% للناتج و +0.6% نمو سكاني و +5 استقرار', gdp: 0.06, stab: 5, popGrowth: 0.006 }),
  rare: res({ name: 'معادن نادرة', icon: '💎', desc: '+6% للناتج و +25% بحث علمي', gdp: 0.06, research: 1.25 }),
  ports: res({ name: 'موانئ استراتيجية', icon: '⚓', desc: '+8% للناتج، سفن أرخص 25%، والتجارة تجيب أكثر', gdp: 0.08 }),
  water: res({ name: 'مياه عذبة وفيرة', icon: '💧', desc: '+0.5% نمو سكاني و +6 استقرار و +3% للناتج', gdp: 0.03, stab: 6, popGrowth: 0.005 }),
  fish: res({ name: 'ثروة سمكية', icon: '🐟', desc: '+7% للناتج و +0.3% نمو سكاني', gdp: 0.07, popGrowth: 0.003 }),
  timber: res({ name: 'غابات وأخشاب', icon: '🪵', desc: '+5% للناتج والمباني أرخص 10%', gdp: 0.05, buildCost: 0.9 }),
  none: res({ name: 'لا موارد', icon: '🏜️', desc: 'ما عندك شي.. بس شعبك صبور (+8 استقرار)', stab: 8 }),
};

// ---------------- المفاجآت (آخر عجلة قبل اللعبة) ----------------
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
  satellite: { name: 'قمر صناعي', icon: '🛰️', desc: 'نص الطريق للتكنولوجيا الجاية و +3 صواريخ', good: true },
  worldcup: { name: 'استضافة كأس العالم', icon: '🏟️', desc: '+60 مليار و +15 استقرار', good: true },
  braindrain: { name: 'هجرة العقول لك', icon: '🎓', desc: '+150 نقطة بحث و +5% سكان', good: true },
  oilfield: { name: 'اكتشاف نفط', icon: '🛢️', desc: 'لو ما عندك موارد يصير عندك نفط، وإلا +10% للناتج', good: true },
  plague: { name: 'وباء', icon: '🦠', desc: 'خسرت ربع سكانك', good: false },
  civilwar: { name: 'حرب أهلية', icon: '🔥', desc: 'خسرت 40% من جيشك و -20 استقرار', good: false },
  crisis: { name: 'أزمة اقتصادية', icon: '📉', desc: 'الناتج -25% والخزينة نصها', good: false },
  traitor: { name: 'جنرال خائن', icon: '🗡️', desc: 'هرب بربع الجيش', good: false },
  volcano: { name: 'بركان', icon: '🌋', desc: 'الناتج -15% والسكان -5%', good: false },
};

// ---------------- القائد ----------------
export interface LeaderDef {
  name: string;
  icon: string;
  desc: string;
}
export const LEADERS: Record<LeaderId, LeaderDef> = {
  warlord: { name: 'القائد المحارب', icon: '🦁', desc: '+15% قوة هجوم والجيش أرخص 10%، وجيشه ما ينهار بسرعة' },
  economist: { name: 'العبقري الاقتصادي', icon: '💼', desc: '+1% نمو سنوي و +8% دخل' },
  diplomat: { name: 'الدبلوماسي', icon: '🕊️', desc: 'الدول تقبل اقتراحاته أكثر، والتجارة تجيب له الضعف' },
  builder: { name: 'البنّاء', icon: '🏗️', desc: 'المباني أرخص 20% وأسرع 20%' },
  scientist: { name: 'العالِم', icon: '🔬', desc: '+30% سرعة البحث العلمي' },
  guardian: { name: 'الحامي', icon: '🛡️', desc: '+20% قوة دفاع، وجيشه يصمد أكثر في الدفاع' },
  populist: { name: 'الشعبوي', icon: '📣', desc: '+12 استقرار، والضرائب العالية ما تزعل الشعب كثير' },
  gambler: { name: 'المقامر', icon: '🎲', desc: 'عجلة الحظ تتوفر له كل سنة بدل سنتين، ونتايجها أكبر (حلوة أو شينة)' },
};

// ---------------- تضاريس الوطن ----------------
export interface TerrainDef {
  name: string;
  icon: string;
  desc: string;
  def: number; // دفاع عن الوطن الأصلي
  gdp: number;
  growth: number;
  popGrowth: number;
  ships: number; // قوة السفن
}
const ter = (o: Partial<TerrainDef> & Pick<TerrainDef, 'name' | 'icon' | 'desc'>): TerrainDef => ({ def: 0, gdp: 0, growth: 0, popGrowth: 0, ships: 0, ...o });
export const TERRAINS: Record<TerrainId, TerrainDef> = {
  mountains: ter({ name: 'جبال وعرة', icon: '⛰️', desc: '+30% دفاع عن وطنك', def: 0.3 }),
  desert: ter({ name: 'صحراء واسعة', icon: '🏜️', desc: '+20% دفاع عن وطنك، بس النمو السكاني أقل', def: 0.2, popGrowth: -0.003 }),
  forest: ter({ name: 'غابات كثيفة', icon: '🌲', desc: '+15% دفاع عن وطنك و +3% للناتج', def: 0.15, gdp: 0.03 }),
  plains: ter({ name: 'سهول خصبة', icon: '🌾', desc: '+1% نمو اقتصادي، بس الدفاع أضعف 10%', def: -0.1, growth: 0.01 }),
  coast: ter({ name: 'سواحل طويلة', icon: '🏖️', desc: '+25% قوة سفنك و +4% للناتج', ships: 0.25, gdp: 0.04 }),
  tundra: ter({ name: 'أراضٍ جليدية', icon: '🧊', desc: '+35% دفاع عن وطنك، بس الناتج أقل 8%', def: 0.35, gdp: -0.08 }),
  rivers: ter({ name: 'أنهار عظيمة', icon: '🏞️', desc: '+0.5% نمو سكاني و +5% للناتج', popGrowth: 0.005, gdp: 0.05 }),
};

// ---------------- المهمات السرية ----------------
export interface MissionDef {
  name: string;
  icon: string;
  desc: (target: number, region?: string) => string;
}
export const MISSIONS: Record<MissionId, MissionDef> = {
  conqueror: { name: 'الفاتح', icon: '⚔️', desc: (t) => `انتصر في ${t} معارك` },
  empire: { name: 'الإمبراطور', icon: '🗺️', desc: (t) => `سيطر على ${t} دول` },
  tycoon: { name: 'إمبراطور المال', icon: '💰', desc: (t) => `وصّل الناتج المحلي إلى ${t >= 1000 ? (t / 1000).toFixed(1) + ' تريليون' : t + ' مليار'}` },
  scholar: { name: 'العقل المدبر', icon: '🧪', desc: (t) => `وصّل للتكنولوجيا مستوى ${t}` },
  allies: { name: 'صانع التحالفات', icon: '🤝', desc: (t) => `كوّن ${t} تحالفات بنفس الوقت` },
  regional: { name: 'سيد القارة', icon: '🌍', desc: (t, r) => `سيطر على ${t} دول في ${r ?? 'قارتك'}` },
  admiral: { name: 'أمير البحار', icon: '⚓', desc: (t) => `امتلك ${t} سفينة حربية` },
  giant: { name: 'أمة عظيمة', icon: '👥', desc: (t) => `وصّل عدد السكان إلى ${t} مليون` },
  fortress: { name: 'الصامد', icon: '🏰', desc: (t) => `صدّ ${t} هجمات على أراضيك` },
};

// ---------------- العجلات قبل اللعبة ----------------
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
  leader: { id: 'leader', title: 'عجلة القائد', icon: '🧭', hint: 'شخصية قائد دولتك تعطيك ميزة خاصة' },
  terrain: { id: 'terrain', title: 'عجلة التضاريس', icon: '🏔️', hint: 'طبيعة أرض وطنك تحدد صعوبة غزوك' },
  mission: { id: 'mission', title: 'عجلة المهمة السرية', icon: '🎯', hint: 'هدف سري محد يعرفه غيرك، لو حققته تاخذ مكافأة كبيرة' },
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
  ['oil', 12], ['gas', 10], ['gold', 9], ['uranium', 6], ['farm', 11], ['rare', 8], ['ports', 9], ['water', 9], ['fish', 9], ['timber', 9], ['none', 9],
] as [ResId, number][]).map(([id, w]) => ({ label: RESOURCES[id].name, icon: RESOURCES[id].icon, w, v: id }));

export const GOV_SLICES: Slice[] = ([
  ['monarchy', 13], ['democracy', 13], ['republic', 14], ['junta', 11], ['planned', 10], ['technocracy', 10], ['constitutional', 11], ['oligarchy', 10], ['transitional', 8],
] as [GovId, number][]).map(([id, w]) => ({ label: GOVS[id].name, icon: GOVS[id].icon, w, v: id }));

export const TECH_NAMES = ['', 'بدائية', 'أساسية', 'متقدمة', 'متطورة', 'مستقبلية', 'خارقة'];
export const TECH_SLICES: Slice[] = [1, 2, 3, 4, 5].map((lv, i) => ({
  label: TECH_NAMES[lv], sub: `مستوى ${lv}`, icon: ['🪨', '🔧', '💻', '🛰️', '🤖'][i], w: [20, 30, 27, 15, 8][i], v: lv,
}));

export const LEADER_SLICES: Slice[] = (Object.keys(LEADERS) as LeaderId[]).map((id) => ({
  label: LEADERS[id].name, icon: LEADERS[id].icon, w: id === 'gambler' ? 9 : 13, v: id,
}));

export const TERRAIN_SLICES: Slice[] = (Object.keys(TERRAINS) as TerrainId[]).map((id) => ({
  label: TERRAINS[id].name, icon: TERRAINS[id].icon, w: 14, v: id,
}));

export const MISSION_SLICES: Slice[] = (Object.keys(MISSIONS) as MissionId[]).map((id) => ({
  label: MISSIONS[id].name, icon: MISSIONS[id].icon, w: 11, v: id,
}));

export const LUCK_SLICES: Slice[] = ([
  ['treasure', 10], ['nuke', 3], ['mercs', 9], ['genius', 7], ['fortress', 7], ['missiles', 7], ['aid', 8], ['respin', 5],
  ['satellite', 6], ['worldcup', 6], ['braindrain', 6], ['oilfield', 6],
  ['plague', 6], ['civilwar', 5], ['crisis', 6], ['traitor', 5], ['volcano', 5],
] as [LuckId, number][]).map(([id, w]) => ({ label: LUCK[id].name, icon: LUCK[id].icon, w, v: id }));

export const STATIC_SLICES: Partial<Record<WheelId, Slice[]>> = {
  area: AREA_SLICES, pop: POP_SLICES, econ: ECON_SLICES, mil: MIL_SLICES, res: RES_SLICES,
  gov: GOV_SLICES, tech: TECH_SLICES, leader: LEADER_SLICES, terrain: TERRAIN_SLICES, mission: MISSION_SLICES, luck: LUCK_SLICES,
};

// ---------------- عجلة الحظ (داخل اللعبة) ----------------
export interface FortuneDef {
  name: string;
  icon: string;
  w: number;
  good: 1 | 0 | -1;
}
export const FORTUNES: Record<FortuneId, FortuneDef> = {
  cash: { name: 'كنز', icon: '💰', w: 12, good: 1 },
  troops: { name: 'متطوعين', icon: '🪖', w: 10, good: 1 },
  tech: { name: 'اختراق علمي', icon: '🧪', w: 9, good: 1 },
  build: { name: 'مشروع مجاني', icon: '🏗️', w: 8, good: 1 },
  festival: { name: 'مهرجان وطني', icon: '🎉', w: 8, good: 1 },
  boom: { name: 'طفرة اقتصادية', icon: '📈', w: 8, good: 1 },
  arms: { name: 'صفقة سلاح', icon: '🚀', w: 7, good: 1 },
  jackpot: { name: 'الجائزة الكبرى', icon: '🎰', w: 3, good: 1 },
  crash: { name: 'انهيار البورصة', icon: '📉', w: 7, good: -1 },
  riots: { name: 'أعمال شغب', icon: '🔥', w: 7, good: -1 },
  outbreak: { name: 'وباء محلي', icon: '🦠', w: 5, good: -1 },
  mutiny: { name: 'تمرد عسكري', icon: '🗡️', w: 5, good: -1 },
  nothing: { name: 'ولا شي', icon: '😐', w: 8, good: 0 },
};
export const FORTUNE_SLICES: Slice[] = (Object.keys(FORTUNES) as FortuneId[]).map((id) => ({
  label: FORTUNES[id].name, icon: FORTUNES[id].icon, w: FORTUNES[id].w, v: id,
}));
export const FORTUNE_EVERY = 24 * DAYS_PER_MONTH; // كل سنتين (المقامر كل سنة)

// ---------------- عجلة الأحداث العالمية ----------------
export interface WorldEventDef {
  name: string;
  icon: string;
  desc: string;
  w: number;
  antiLeader?: boolean; // يزيد احتماله لو فيه دولة مسيطرة
}
export const WORLD_EVENTS: Record<WorldEventId, WorldEventDef> = {
  coalition: { name: 'تحالف دولي', icon: '🤝', desc: 'العالم يتحد ضد أقوى دولة: البوتات تعاديها والدول المحايدة حولها تتسلح', w: 9, antiLeader: true },
  crash: { name: 'أزمة مالية عالمية', icon: '📉', desc: 'كل الخزائن تنقص 20%، وأغنى 3 دول تخسر 40%', w: 8, antiLeader: true },
  pandemic: { name: 'جائحة عالمية', icon: '🦠', desc: 'كل الدول تخسر 5% من سكانها، والإمبراطوريات الكبيرة يتزعزع استقرارها', w: 7, antiLeader: true },
  revolts: { name: 'ربيع الثورات', icon: '✊', desc: 'الأراضي المحتلة في الإمبراطوريات الكبيرة ممكن تعلن استقلالها', w: 8, antiLeader: true },
  bailout: { name: 'خطة الإنقاذ الدولية', icon: '🎁', desc: 'الدول الأضعف تاخذ فلوس وجنود وأبحاث', w: 9 },
  peace: { name: 'مؤتمر السلام', icon: '🕊️', desc: 'كل الحروب توقف وهدنة سنة للجميع', w: 6 },
  energy: { name: 'طفرة الطاقة', icon: '🛢️', desc: 'دول النفط والغاز واليورانيوم تاخذ أرباح ضخمة', w: 6 },
  meteor: { name: 'نيزك', icon: '☄️', desc: 'نيزك يضرب دولة من الدول الكبيرة', w: 5, antiLeader: true },
  techrev: { name: 'ثورة تكنولوجية', icon: '🧪', desc: 'الدول المتأخرة تقفز مستوى تكنولوجيا', w: 7 },
  armsrace: { name: 'سباق تسلح', icon: '⚔️', desc: 'كل الأسلحة أرخص 35% لمدة سنة', w: 6 },
  fortune: { name: 'ليلة الحظ', icon: '🎰', desc: 'كل الدول تقدر تلف عجلة الحظ الحين!', w: 7 },
  goldage: { name: 'عصر ذهبي', icon: '✨', desc: 'الاستقرار +10 والناتج +5% للجميع', w: 6 },
  mercsrebel: { name: 'تمرد المرتزقة', icon: '🗡️', desc: 'أكبر جيش في العالم يخسر 20% من قواته', w: 5, antiLeader: true },
};
export const WORLD_SLICES: Slice[] = (Object.keys(WORLD_EVENTS) as WorldEventId[]).map((id) => ({
  label: WORLD_EVENTS[id].name, icon: WORLD_EVENTS[id].icon, w: WORLD_EVENTS[id].w, v: id,
}));
export const WORLD_EVERY = [40, 56]; // كل 3.5 إلى 4.5 سنة تقريباً (بالأشهر)

// ---------------- التكنولوجيا ----------------
export const TECH_COST = [0, 0, 80, 200, 400, 700, 1100]; // نقاط للوصول للمستوى
export const MAX_TECH = 6;
export const techMult = (t: number) => 1 + 0.2 * (t - 1);
export const missileRange = (t: number) => (t >= 5 ? 40000 : [0, 1500, 2500, 4000, 7000][t] ?? 1500);
export const navalRange = (t: number) => 2000 + 1200 * (t - 1);
export const NUKE_PROJECT = { cost: 80, days: 720, tech: 4 };

// ---------------- المعارك ----------------
export const BATTLE = {
  intensity: 0.08, // نسبة الضرر اليومية
  noise: 0.08, // حظ يومي صغير ±8%
  attBreak: 0.45, // المهاجم ينسحب لو قوته نزلت تحت 45%
  defBreak: 0.3, // المدافع ينهار تحت 30%
  capitalBreak: 0.22,
  maxDays: 40,
};

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
