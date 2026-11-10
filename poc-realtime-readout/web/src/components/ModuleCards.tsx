import type { Card, Day } from "../types";
import { fmt, mdw } from "../format";

export type Tab = "overview" | "reaction" | "flavor" | "store" | "promo";
export const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "개요" },
  { key: "reaction", label: "신제품 반응" },
  { key: "flavor", label: "맛별 판매 순위" },
  { key: "store", label: "매장 순위 급등" },
  { key: "promo", label: "판촉 행사 효과" },
];

// 판독 4축의 핵심만: 상태 배지 + 한 줄 결론 + 숫자 두 개. 누르면 해당 탭에서 자세한 데이터와 근거를 본다
export function ModuleCards({ day, onOpen }: { day: Day; onOpen: (t: Tab) => void }) {
  const wk = (k: Card["key"]) => day.weekly?.cards.find((c) => c.key === k);
  const kpi = (name: string) => day.kpis.find((k) => k.k === name)?.v ?? "-";
  const me = day.flavor.rows.find((r) => r.signals.some((s) => s.kind === "new"));
  const done = day.promos.filter((p) => p.status === "done");
  const lastPromo = done[done.length - 1];
  const before = day.first_weekly_read ? `첫 주간 판독 ${mdw(day.first_weekly_read)}` : "주간 판독 전";
  const items: { tab: Tab; title: string; freq: string; card?: Card; metric: string[] }[] = [
    { tab: "reaction", title: "신제품 반응", freq: "매일", card: day.reaction_status,
      metric: [`검색 ${kpi("검색지수 (출시 전 한 달 대비)")}`, `긍정률 ${kpi("긍정률 (최근 7일)")}`] },
    { tab: "flavor", title: "맛별 판매 순위", freq: "주간 판독", card: wk("demand"),
      metric: me ? [`이달의 맛 ${me.rank}위`, `일평균 ${fmt(me.avg)}개`] : ["출시 전"] },
    { tab: "store", title: "매장 순위 급등", freq: "주간 판독", card: wk("store"),
      metric: day.stores ? [`점검 ${day.stores.counts.check ?? 0}곳`, `바이럴 ${day.stores.counts.viral ?? 0}곳`] : ["출시 7일 후부터"] },
    { tab: "promo", title: "판촉 행사 효과", freq: "주간 판독", card: wk("promo"),
      metric: lastPromo ? [lastPromo.name, `ROI ${lastPromo.roi!.toFixed(2)}${lastPromo.firm ? "" : " (잠정)"}`]
        : [`행사 ${day.promos.length}개 판독 대기`] },
  ];
  return (
    <section className="mods" aria-label="판독 4축">
      {items.map((it) => {
        const tone = it.card?.pill.tone ?? "info";
        return (
          <button type="button" key={it.tab} className={`mod ${tone}`} onClick={() => onOpen(it.tab)}>
            <span className="mod-h"><span className="mod-title">{it.title}</span><span className="note">{it.freq}</span></span>
            <span className={`pill sm ${tone}`}>{it.card?.pill.label ?? "판독 전"}</span>
            <span className="mod-head">{it.card?.head ?? before}</span>
            <span className="mod-metric">{it.metric.map((m) => <span key={m}>{m}</span>)}</span>
            <span className="mod-more">자세히 보기 →</span>
          </button>
        );
      })}
    </section>
  );
}
