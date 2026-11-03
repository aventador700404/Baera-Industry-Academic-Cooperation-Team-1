import type { Day, Readout } from "../types";
import { fmt, mdw, pct, period } from "../format";
import { Verdict } from "./bits";

const STATUS: Record<string, string> = { running: "진행 중", planned: "예정", pending: "판독 대기", done: "" };

// 판촉 행사 효과: 행사 기간 판매 − 행사가 없었을 때(기준선) = 증분, 증분 ROI = 증분 매출 ÷ 할인 비용
export function PromoPanel({ data, day }: { data: Readout; day: Day }) {
  const fw = day.first_week;
  const r = data.meta.rules;
  const c = day.weekly?.cards.find((x) => x.key === "promo");
  return (
    <section className="panel quad" aria-labelledby="q4">
      <div className="panel-h"><h2 id="q4">판촉 행사 효과</h2><span className="note">기준일 현재 · 증분 = 행사 판매 − 행사 없었을 때</span></div>
      {c && <Verdict c={c} note={`주간 판독 ${mdw(day.weekly!.read)}`} />}
      {fw && (
        <div className="fw">
          <div className="note">출시 첫 주 판매: 맛 수요 {pct(1 - fw.promo_share)} · 할인 효과 {pct(fw.promo_share)}</div>
          <div className="split" role="img" aria-label="출시 첫 주 판매 중 맛 수요와 할인 효과 비중">
            <div style={{ width: `${100 - fw.promo_share * 100}%`, background: "var(--s1)" }} />
            <div style={{ width: `${fw.promo_share * 100}%`, background: "var(--s2)" }} />
          </div>
        </div>
      )}
      <div className="tablewrap">
        <table className="compact">
          <thead><tr><th className="l">행사</th><th className="l">기간</th><th>증분</th><th>증분 ROI</th><th className="l">판정</th></tr></thead>
          <tbody>
            {day.promos.map((p) => p.status === "done" ? (
              <tr key={p.id} title={`${p.desc} · 판매 ${fmt(p.act!)} · 기준선 ${fmt(p.base!)} · 증분 범위 ${fmt(p.inc_lo!)}~${fmt(p.inc_hi!)} · 할인 비용 ${fmt(p.cost_won! / 1e6)}백만 원`}>
                <td className="l name">{p.name}</td>
                <td className="l">{period(p.start, p.end)}</td>
                <td>+{fmt(p.inc!)} <span className="note">({pct(p.inc_pct!)})</span></td>
                <td>{p.roi!.toFixed(2)}</td>
                <td className="l"><span className={`pill sm ${p.verdict}`}>{p.verdict_label}{p.firm ? "" : " · 잠정"}</span></td>
              </tr>
            ) : (
              <tr key={p.id} title={p.desc}>
                <td className="l name">{p.name}</td>
                <td className="l">{period(p.start, p.end)}</td>
                <td colSpan={2} className="note">{p.desc}</td>
                <td className="l"><span className="chip">{STATUS[p.status]}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">판정: ROI {r.roi_keep} 이상 지속 · {r.roi_adjust}~{r.roi_keep} 조정 · {r.roi_adjust} 미만 중단 검토 · 단가 {fmt(r.unit_price)}원 기준</p>
    </section>
  );
}
