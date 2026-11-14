// أنواع البيانات الأساسية للعبة "عجلة الأمم"
export type TerrId = string;
export type NationId = string; // '' = محايدة

export const UNIT_TYPES = ['inf', 'tank', 'jet', 'ship', 'missile', 'nuke'] as const;
export type UnitType = (typeof UNIT_TYPES)[number];
export type Units = Record<UnitType, number>;
export const COMBAT_UNITS: UnitType[] = ['inf', 'tank', 'jet', 'ship'];

export const BUILDING_TYPES = ['industry', 'infra', 'research', 'health', 'fort', 'airdef', 'milfac', 'mining'] as const;
export type BuildingType = (typeof BUILDING_TYPES)[number];

export type GovId = 'monarchy' | 'democracy' | 'republic' | 'junta' | 'planned' | 'technocracy';
export type ResId = 'oil' | 'gas' | 'gold' | 'uranium' | 'farm' | 'rare' | 'ports' | 'none';
export type LuckId =
  | 'treasure' | 'nuke' | 'mercs' | 'genius' | 'fortress' | 'missiles' | 'aid' | 'respin'
  | 'plague' | 'civilwar' | 'crisis';

export type WheelId = 'area' | 'country' | 'pop' | 'econ' | 'mil' | 'res' | 'gov' | 'tech' | 'luck';
export const WHEEL_ORDER: WheelId[] = ['area', 'country', 'pop', 'econ', 'mil', 'res', 'gov', 'tech', 'luck'];

export type Difficulty = 'easy' | 'normal' | 'hard';
export type WinMode = 'domination' | 'score' | 'percent';
export type NeutralStrength = 'weak' | 'normal' | 'strong';

export interface Settings {
  bots: number;
  difficulty: Difficulty;
  win: WinMode;
  years: number; // لوضع النقاط: مدة اللعبة بالسنوات
  percent: number; // لوضع النسبة: نسبة مساحة العالم المطلوبة
  neutral: NeutralStrength;
  peaceMonths: number; // فترة السلام في البداية (ما أحد يهاجم لاعب)
  speed: number;
}

export interface WheelState {
  res: Partial<Record<WheelId, number | string>>;
  respins: number;
  done: boolean;
  last?: { wheel: WheelId; nonce: number }; // آخر عجلة انلفّت (عشان الأنيميشن)
}

export interface Player {
  id: string; // معرف الجهاز
  name: string;
  nation: NationId;
  online: boolean;
  joinedAt: number;
  lastSeen: number;
}

export interface Territory {
  id: TerrId;
  owner: NationId; // '' = محايدة
  pop: number; // مليون
  gdp: number; // مليار دولار سنوياً
  unrest: number; // أشهر من عدم الاستقرار بعد الاحتلال
  nuked: number; // أشهر من الإشعاع
  g?: { inf: number; tank: number }; // حامية الدولة المحايدة
  gmax?: number;
  nt?: number; // تكنولوجيا المحايدة
}

export interface QItem {
  id: number;
  kind: 'unit' | 'building' | 'project';
  type: string;
  count: number;
  left: number; // أيام متبقية
  total: number;
  cost?: number;
}

export type Personality = 'aggressive' | 'balanced' | 'economic' | 'defensive';
export interface AIState {
  pers: Personality;
  next: number;
  grudge?: NationId;
  cool?: number; // ما يهاجم قبل هذا اليوم (يرتب أوضاعه بعد الاحتلال)
  asked?: Record<NationId, number>; // آخر مرة طلب تجارة من دولة
}

export interface Derived {
  gdp: number; // الناتج الفعلي
  income: number; // الدخل الشهري
  upkeep: number; // صيانة الجيش الشهرية
  pop: number;
  power: number;
  score: number;
  area: number;
  terrs: number;
  research: number; // نقاط بحث شهرياً
  slots: number;
  used: number;
  manpower: number; // ألف جندي متاح
  atWar: number;
}

export interface Nation {
  id: NationId;
  kind: 'player' | 'bot';
  name: string; // اسم الدولة
  leader: string; // اسم اللاعب أو البوت
  color: string;
  home: TerrId;
  capital: TerrId;
  alive: boolean;
  treasury: number;
  tax: number;
  stability: number;
  tech: number;
  research: number;
  units: Units;
  q: QItem[];
  bq: QItem[];
  b: Record<BuildingType, number>;
  gov: GovId;
  res: ResId;
  luck: LuckId;
  nukeProg: boolean;
  ai?: AIState;
  aiControl?: boolean;
  st: { won: number; lost: number; conq: number; lostT: number };
  tiers: { area: number; pop: number; econ: number; mil: number };
  d: Derived;
  elimDay?: number;
  joinDay: number;
  lastProp?: number; // آخر يوم وصلها فيه اقتراح (عشان البوتات ما تزعج اللاعب)
}

export type MoveKind = 'attack' | 'return' | 'missile' | 'nuke';
export interface Movement {
  id: number;
  owner: NationId;
  from: TerrId;
  to: TerrId;
  units: Units;
  depart: number;
  arrive: number;
  kind: MoveKind;
  naval?: boolean;
}

export interface Relation {
  war?: number; // يوم بداية الحرب
  ally?: number;
  trade?: number;
  truce?: number; // يوم نهاية الهدنة
}

export type ProposalType = 'ally' | 'trade' | 'peace';
export interface Proposal {
  id: number;
  from: NationId;
  to: NationId;
  type: ProposalType;
  day: number;
}

export type NewsKind = 'war' | 'battle' | 'diplo' | 'event' | 'econ' | 'system' | 'nuke' | 'join';
export interface News {
  id: number;
  day: number;
  icon: string;
  text: string;
  kind: NewsKind;
  to?: NationId[]; // خاص بدول معينة
  terr?: TerrId;
  n?: NationId[]; // الدول المعنية
}

export interface Report {
  id: number;
  day: number;
  kind: 'battle' | 'missile' | 'nuke';
  att: NationId;
  def: NationId;
  terr: TerrId;
  from: TerrId;
  A: number;
  D: number;
  la: number;
  ld: number;
  win: boolean;
  aUnits: Partial<Units>;
  dUnits: Partial<Units>;
  aLoss: Partial<Units>;
  dLoss: Partial<Units>;
  allies: NationId[];
  hits?: number;
  intercepted?: number;
}

export interface Chat {
  id: number;
  day: number;
  from: NationId;
  name: string;
  to?: NationId;
  text: string;
}

export type Phase = 'lobby' | 'wheels' | 'playing' | 'ended';

export interface GameState {
  v: number;
  mode: 'single' | 'online';
  phase: Phase;
  settings: Settings;
  day: number;
  paused: boolean;
  speed: number;
  rng: number;
  seq: number;
  hostId: string;
  players: Record<string, Player>;
  nations: Record<NationId, Nation>;
  terr: Record<TerrId, Territory>;
  wheels: Record<NationId, WheelState>;
  taken: Record<TerrId, NationId>;
  moves: Movement[];
  rel: Record<string, Relation>;
  props: Proposal[];
  news: News[];
  reports: Report[];
  chat: Chat[];
  winner?: { nations: NationId[]; reason: string; day: number };
  countdown?: number; // وقت بداية اللعبة بعد العجلات (ms)
  epoch?: number; // يزيد كل ما تغير صاحب الغرفة
}

// الأوامر اللي يرسلها اللاعب
export type Command =
  | { t: 'spin'; wheel: WheelId }
  | { t: 'respin'; wheel: WheelId }
  | { t: 'autospin' }
  | { t: 'tax'; rate: number }
  | { t: 'build'; b: BuildingType }
  | { t: 'cancel'; q: 'q' | 'bq'; id: number }
  | { t: 'recruit'; u: UnitType; n: number }
  | { t: 'disband'; u: UnitType; n: number }
  | { t: 'project'; p: 'nuke' }
  | { t: 'attack'; to: TerrId; units: Partial<Units> }
  | { t: 'strike'; to: TerrId; kind: 'missile' | 'nuke'; n: number }
  | { t: 'propose'; to: NationId; type: ProposalType }
  | { t: 'respond'; id: number; accept: boolean }
  | { t: 'breakAlly'; with: NationId }
  | { t: 'cancelTrade'; with: NationId }
  | { t: 'declare'; on: NationId }
  | { t: 'aid'; to: NationId; money?: number; units?: Partial<Units> }
  | { t: 'chat'; text: string; to?: NationId }
  | { t: 'speed'; speed: number }
  | { t: 'pause'; paused: boolean };

export interface CmdResult {
  ok: boolean;
  msg?: string;
}
