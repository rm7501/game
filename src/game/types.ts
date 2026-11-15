// أنواع البيانات الأساسية للعبة "عجلة الأمم"
export type TerrId = string;
export type NationId = string; // '' = محايدة

export const UNIT_TYPES = ['inf', 'tank', 'jet', 'ship', 'missile', 'nuke'] as const;
export type UnitType = (typeof UNIT_TYPES)[number];
export type Units = Record<UnitType, number>;
export const COMBAT_UNITS: UnitType[] = ['inf', 'tank', 'jet', 'ship'];

export const BUILDING_TYPES = ['industry', 'infra', 'research', 'health', 'fort', 'airdef', 'milfac', 'mining', 'intel'] as const;
export type BuildingType = (typeof BUILDING_TYPES)[number];

export type GovId =
  | 'monarchy' | 'democracy' | 'republic' | 'junta' | 'planned' | 'technocracy' | 'constitutional' | 'oligarchy' | 'transitional';
export type ResId = 'oil' | 'gas' | 'gold' | 'uranium' | 'farm' | 'rare' | 'ports' | 'water' | 'fish' | 'timber' | 'none';
export type LuckId =
  | 'treasure' | 'nuke' | 'mercs' | 'genius' | 'fortress' | 'missiles' | 'aid' | 'respin' | 'satellite' | 'worldcup'
  | 'braindrain' | 'oilfield' | 'plague' | 'civilwar' | 'crisis' | 'traitor' | 'volcano';
export type LeaderId = 'warlord' | 'economist' | 'diplomat' | 'builder' | 'scientist' | 'guardian' | 'populist' | 'gambler';
export type TerrainId = 'mountains' | 'desert' | 'forest' | 'plains' | 'coast' | 'tundra' | 'rivers';
export type MissionId = 'conqueror' | 'empire' | 'tycoon' | 'scholar' | 'allies' | 'regional' | 'admiral' | 'giant' | 'fortress';
export type FortuneId =
  | 'cash' | 'troops' | 'tech' | 'build' | 'festival' | 'boom' | 'arms' | 'jackpot'
  | 'crash' | 'riots' | 'outbreak' | 'mutiny' | 'nothing' | 'card';
export type WorldEventId =
  | 'coalition' | 'crash' | 'pandemic' | 'revolts' | 'bailout' | 'peace' | 'energy' | 'meteor' | 'techrev'
  | 'armsrace' | 'fortune' | 'goldage' | 'mercsrebel';

export type CardId = 'blitz' | 'shield' | 'ceasefire' | 'coup' | 'boom' | 'mobilize' | 'double' | 'supply' | 'defect' | 'reluck';
export type SpyOpId = 'tech' | 'sabotage' | 'revolt' | 'reveal' | 'money';
export type UNResId = 'sanctions' | 'nukeban' | 'peacekeep' | 'devfund' | 'condemn' | 'science' | 'disarm';
export type Vote = 'y' | 'n' | 'a';

export type WheelId = 'area' | 'country' | 'pop' | 'econ' | 'mil' | 'res' | 'gov' | 'tech' | 'leader' | 'terrain' | 'mission' | 'luck';
export const WHEEL_ORDER: WheelId[] = ['area', 'country', 'pop', 'econ', 'mil', 'res', 'gov', 'tech', 'leader', 'terrain', 'mission', 'luck'];

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
  teams: number; // وضع الفرق: 0 = بدون، أو عدد الفرق (2-4)
}

export interface WheelState {
  res: Partial<Record<WheelId, number | string>>;
  respins: number;
  done: boolean;
  ready?: boolean; // ضغط «جاهز» بعد ما شاف بطاقة دولته
  team?: number;
  last?: { wheel: WheelId; nonce: number }; // آخر عجلة انلفّت (عشان الأنيميشن)
}

export interface Player {
  id: string; // معرف الجهاز
  name: string;
  nation: NationId;
  online: boolean;
  joinedAt: number;
  lastSeen: number;
  team?: number; // الفريق (في وضع الفرق)
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
  terrs: number; // عدد الأراضي (دول ومناطق)
  countries: number; // عدد الدول (المناطق من نفس الدولة تنحسب وحدة)
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
  trait: LeaderId; // صفة القائد
  terrain: TerrainId; // تضاريس الوطن
  mission: { id: MissionId; target: number; done: boolean; region?: string };
  fortuneNext: number; // يوم توفر عجلة الحظ
  fortune?: { nonce: number; res: FortuneId; day: number; text: string };
  bonus: number; // نقاط إضافية (من المهمات)
  govUntil?: number; // نهاية الحكومة الانتقالية
  nukeProg: boolean;
  ai?: AIState;
  aiControl?: boolean;
  st: { won: number; lost: number; conq: number; lostT: number; held: number };
  tiers: { area: number; pop: number; econ: number; mil: number };
  d: Derived;
  elimDay?: number;
  joinDay: number;
  lastProp?: number; // آخر يوم وصلها فيه اقتراح (عشان البوتات ما تزعج اللاعب)
  underdog?: boolean; // من الدول الأضعف: تاخذ دعم
  team?: number; // الفريق (في وضع الفرق)
  agents: number; // جواسيس جاهزين
  cards: CardId[]; // بطاقات الخطط اللي بيدك
  fx: { blitz?: number; shield?: number; sanct?: number; supply?: number }; // تأثيرات مؤقتة (يوم نهايتها)
  intel: Record<NationId, number>; // كشف أسرار دولة لين يوم معين
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
  team?: boolean; // تحالف فريق دائم (ما ينفسخ)
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

/** معركة مستمرة لعدة أيام */
export interface Battle {
  id: number;
  terr: TerrId;
  att: NationId;
  def: NationId; // '' = محايدة
  from: TerrId;
  naval: boolean;
  start: number;
  au: Units; // القوات المهاجمة (بالبداية)
  du: Units; // قوات المدافع المشاركة (بالبداية)
  allies: { id: NationId; u: Units }[];
  a0: number; // قوة الهجوم بالبداية
  d0: number; // قوة الدفاع بالبداية (بدون المقاومة الشعبية)
  m: number; // المقاومة الشعبية (ما تموت)
  a: number; // قوة الهجوم الحالية
  d: number; // قوة الدفاع الحالية
  aBreak: number; // ينهار المهاجم تحت هذي النسبة
  dBreak: number;
  days: number;
  mods: string[]; // عوامل أثرت (تفوق جوي، أسلحة مشتركة...)
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
  days?: number;
  mods?: string[];
}

export interface Chat {
  id: number;
  day: number;
  from: NationId;
  name: string;
  to?: NationId;
  team?: number; // رسالة للفريق
  text: string;
}

/** عملية تجسس شغالة */
export interface SpyOp {
  id: number;
  owner: NationId;
  target: NationId;
  op: SpyOpId;
  start: number;
  done: number; // يوم النتيجة
}

/** قرار في الأمم المتحدة قيد التصويت */
export interface UNVote {
  id: number;
  res: UNResId;
  target?: NationId;
  start: number;
  end: number;
  votes: Record<NationId, Vote>;
}

export interface UNResult {
  id: number;
  res: UNResId;
  target?: NationId;
  yes: number;
  no: number;
  abst: number;
  passed: boolean;
  day: number;
  text: string;
}

/** سجل اللعبة (للإعادة والإحصائيات بالنهاية) */
export interface History {
  n: NationId[]; // ترتيب الدول (رقم الدولة في الإطارات = مكانها هنا + 1)
  f: { d: number; o: string; v: number[][] }[]; // إطار: اليوم، أصحاب الأراضي، [نقاط، قوة، ناتج، أراضي] لكل دولة
  ev: { d: number; icon: string; text: string }[]; // أحداث مهمة
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
  battles: Battle[];
  world?: { id: number; ev: WorldEventId; day: number; text: string; target?: NationId; terr?: TerrId };
  nextWorld: number; // يوم عجلة الأحداث العالمية الجاية
  mods: { arms?: number; nukeBan?: number }; // تأثيرات عالمية مؤقتة (يوم نهايتها)
  ops: SpyOp[];
  un?: UNVote;
  unLast?: UNResult;
  nextUN: number;
  nextCards: number; // يوم توزيع البطاقات السنوي
  hist?: History;
  gameId?: string; // معرف اللعبة (لتسجيل النتايج)
  coalition?: NationId; // الدولة اللي العالم متحالف ضدها
  holdUntil?: number; // صاحب الغرفة يوقف اللعبة شوي وقت الأحداث الكبيرة (ms)
}

// الأوامر اللي يرسلها اللاعب
export type Command =
  | { t: 'spin'; wheel: WheelId }
  | { t: 'respin'; wheel: WheelId }
  | { t: 'autospin' }
  | { t: 'ready' }
  | { t: 'fortune' }
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
  | { t: 'chat'; text: string; to?: NationId; team?: boolean }
  | { t: 'team'; team: number }
  | { t: 'agent' }
  | { t: 'spy'; op: SpyOpId; target: NationId }
  | { t: 'vote'; v: Vote }
  | { t: 'card'; card: CardId; target?: NationId; terr?: TerrId }
  | { t: 'speed'; speed: number }
  | { t: 'pause'; paused: boolean };

export interface CmdResult {
  ok: boolean;
  msg?: string;
}
