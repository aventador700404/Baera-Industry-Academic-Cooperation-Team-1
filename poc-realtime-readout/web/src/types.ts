// pipeline/build.py 가 만드는 readout.json 의 모양. 파이썬 쪽을 바꾸면 여기도 바꾼다.

export type Tone = "good" | "warn" | "crit" | "info";
export type Prov = "raw" | "api" | "mixed" | "mock";
export type Module = "reaction" | "flavor" | "store" | "promo";

export interface Alert {
  date: string; kind: string; module: Module; tone: Tone;
  title: string; detail: string; action: string; gain_days: number;
}

export interface Card {
  key: "monitor" | "demand" | "store" | "promo"; module: Module; title: string;
  pill: { tone: Tone; label: string };
  head: string; items: string[];
  tags: ("sales" | "reaction" | "cost")[];
}

export interface Kpi { k: string; v: string; d: string }

export interface PromoRow {
  id: string; name: string; start: string; end: string; desc: string; rate: number;
  status: "done" | "running" | "planned" | "pending";
  act?: number; base?: number; inc?: number; inc_lo?: number; inc_hi?: number; inc_pct?: number;
  cost_won?: number; roi?: number; roi_lo?: number; roi_hi?: number; n_fit?: number;
  verdict?: Tone; verdict_label?: string; firm?: boolean; tentative_reason?: "few_days" | "range" | null;
}

export interface FlavorRow {
  rank: number; flavor: string; avg: number; change: number | "new" | null;
  signals: { kind: "new" | "warn" | "good"; text: string }[];
}

export interface StoreRow {
  store_id: string; name: string; rank: number; rank_prev: number; delta: number;
  sns: number; sns_prev: number;
  flag: "check" | "viral" | "recover" | "rise" | "drop" | null; why: string | null;
}

export interface TopicRow {
  topic: string; mentions: number; positive: number; negative: number;
  share: number; share_prev: number | null; pos: number | null; pos_prev: number | null;
  surge: boolean; neg_up: boolean;
}

export interface Day {
  date: string; read: string; gain_days: number;
  kpis: Kpi[];
  monitor: Card;                       // 매일 모니터링
  weekly: {                            // 가장 최근 주간 판독 (월요일 아침, 일요일까지의 데이터)
    asof: string; read: string; next_read: string | null; gain_days: number;
    cards: Card[]; new_alerts: number;
  } | null;
  first_weekly_read: string | null;
  baseline: { base: number[]; lo: number[]; hi: number[]; n_fit: number } | null;
  promos: PromoRow[];
  first_week: { total: number; promo: number; demand: number; promo_share: number } | null;
  flavor: { window: { start: string; end: string }; rows: FlavorRow[] };
  stores: { window: { start: string; end: string }; rows: StoreRow[]; total: number; counts: Record<string, number> } | null;
  topics: { window: { start: string; end: string }; rows: TopicRow[] } | null;
  youtube: { asof: string; videos: { title: string; channel_type: "official" | "consumer"; views: number }[] } | null;
  conversion: { sales_idx: number; search_idx: number; ratio: number } | null;
}

export interface Readout {
  meta: {
    title: string; flavor: string; parent_flavor: string; generated_at: string;
    provenance: Record<string, string>; provenance_raw: Record<string, Prov>;
    stores_total: number; assumptions: string;
    rules: { roi_keep: number; roi_adjust: number; unit_price: number; target_daily: number };
    keyword_labels: Record<string, string>;
    current_read: string;
    milestones: { label: string; date: string; show: string }[];
    weekly_reads: { asof: string; read: string }[];
  };
  dates: string[];
  launch_dates: string[];
  series: { bra: (number | null)[] | null; trend: (number | null)[] | null; mentions: (number | null)[] | null;
            sales: (number | null)[] };
  promos: { id: string; name: string; start: string; end: string; rate: number; desc: string }[];
  markers: { date: string; label: string }[];
  alerts: Alert[];
  days: Day[];
  schema: Record<string, string[]>;
}
