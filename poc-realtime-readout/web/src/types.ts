// pipeline/build.py 가 만드는 readout.json 의 모양. 파이썬 쪽을 바꾸면 여기도 바꾼다.

export type Tone = "good" | "warn" | "crit" | "info";
export type Prov = "raw" | "api" | "mixed" | "mock";

export interface Card {
  key: "demand" | "promo" | "store";
  title: string;
  pill: { tone: Tone; label: string };
  head: string;
  items: string[];
  tags: ("sales" | "reaction" | "cost")[];
}

export interface Kpi { k: string; v: string; d: string }

export interface PromoRow {
  id: string; name: string; start: string; end: string; desc: string; rate: number;
  status: "done" | "running" | "planned";
  act?: number; base?: number; inc?: number; inc_lo?: number; inc_hi?: number; inc_pct?: number;
  cost_won?: number; roi?: number; roi_lo?: number; roi_hi?: number;
  verdict?: Tone; verdict_label?: string; firm?: boolean; tentative_reason?: "few_days" | "range" | null;
}

export interface FlavorRow {
  rank: number; flavor: string; avg: number; change: number | "new" | null;
  signals: { kind: "new" | "warn" | "good"; text: string }[];
}

export interface StoreRow {
  store_id: string; name: string; type: string; rank: number; rank_prev: number; delta: number;
  sns: number; sns_prev: number; sns_pct: number | null;
  flag: "check" | "spread" | "rise" | "drop" | null; why: string | null;
}

export interface Peak { type: string; day: number; date: string; index: number; firm: boolean; lag_from_reaction: number | null }

export interface View {
  id: string; label: string; read: string; to: string; start: string; end: string;
  timing: { pre: true } | { read: string; current: string; gain_days: number };
  kpis: Kpi[];
  cards: Card[];
  baseline: { base: number[]; lo: number[]; hi: number[]; k: number; k_band: [number, number]; n_fit: number } | null;
  promos: PromoRow[];
  first_week: { total: number; promo: number; demand: number; promo_share: number } | null;
  flavor: { window: { start: string; end: string }; rows: FlavorRow[] };
  stores: { rows: StoreRow[]; total: number; counts: Record<string, number>; type_delta: Record<string, number> } | null;
  peaks: Peak[];
  reaction_peak: string | null;
  youtube: { asof: string; videos: { title: string; channel_type: "official" | "consumer"; views: number }[] } | null;
}

export interface Readout {
  meta: {
    title: string; flavor: string; parent_flavor: string; generated_at: string;
    provenance: Record<string, string>; provenance_raw: Record<string, Prov>;
    stores_total: number; assumptions: string;
    rules: { roi_keep: number; roi_adjust: number; unit_price: number; target_daily: number };
    keyword_labels: Record<string, string>;
    anchors: { date: string; cum: number }[];
  };
  dates: string[];
  launch_dates: string[];
  series: { bra: (number | null)[] | null; trend: (number | null)[] | null; mentions: (number | null)[] | null;
            positive: (number | null)[] | null; sales: (number | null)[] };
  promos: { id: string; name: string; start: string; end: string; rate: number; desc: string }[];
  markers: { date: string; label: string }[];
  views: View[];
  schema: Record<string, string[]>;
}
