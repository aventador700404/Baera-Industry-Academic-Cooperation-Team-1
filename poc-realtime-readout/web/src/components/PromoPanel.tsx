import type { Day, PromoNews, PromoReaction, Readout } from "../types";
import { fmt, mdw, pct, period } from "../format";
import { Verdict } from "./bits";

const STATUS: Record<string, string> = { running: "진행 중", planned: "예정", pending: "판독 대기", done: "" };

// 행사 일정의 근거: 보도로 확인 / 규칙으로 추정 / 일부 가정
function Evidence({ text, source }: { text?: string | null; source?: string | null }) {
  if (!text) return null;
  const [cls, label] = text.startsWith("확인") ? ["good", "확인"] : text.startsWith("규칙") ? ["blue", "규칙 추정"] : ["warn", "일부 가정"];
  const chip = <span className={`chip ${cls}`} title={text}>{label}</span>;
  return source ? <a href={source} target="_blank" rel="noreferrer" title={`${text} · 근거 기사`}>{chip}</a> : chip;
}

// 공개 데이터로 본 행사 반응: 기사 수, 행사명 검색 배수 (판매 증분과는 별개)
function PublicLine({ news, reaction }: { news?: PromoNews | null; reaction?: PromoReaction | null }) {
  const parts: string[] = [];
  if (news) parts.push(`기사 ${fmt(news.n_articles)}건`);
  if (reaction?.lift) parts.push(`행사명 검색 평소의 ${reaction.lift.toFixed(1)}배`);
  if (reaction?.brand_lift) parts.push(`브랜드 검색 ${reaction.brand_lift.toFixed(2)}배`);
  return parts.length ? <div className="note">{parts.join(" · ")}</div> : null;
}

// 판촉 행사 효과: 행사 기간 판매 − 행사가 없었을 때(기준선) = 증분, 증분 ROI = 증분 매출 ÷ 할인 비용
export function PromoPanel({ data, day }: { data: Readout; day: Day }) {
  const fw = day.first_week;
  const r = data.meta.rules;
  const c = day.weekly?.cards.find((x) => x.key === "promo");
  const before = data.promos.filter((p) => p.before_launch && p.start <= day.date);
  const found = data.meta.public_events ?? [];
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
            {before.map((p) => (
              <tr key={p.id} title={p.desc}>
                <td className="l name">{p.name} <Evidence text={p.evidence} source={p.source} /></td>
                <td className="l">{period(p.start, p.end)}</td>
                <td colSpan={2} className="note">기준선에서 제외</td>
                <td className="l"><span className="chip">출시 전</span></td>
              </tr>
            ))}
            {day.promos.map((p) => p.status === "done" ? (
              <tr key={p.id} title={`${p.desc} · 판매 ${fmt(p.act!)} · 기준선 ${fmt(p.base!)} · 증분 범위 ${fmt(p.inc_lo!)}~${fmt(p.inc_hi!)} · ROI 범위 ${p.roi_lo!.toFixed(2)}~${p.roi_hi!.toFixed(2)} · 할인 비용 ${fmt(p.cost_won! / 1e6)}백만 원`}>
                <td className="l name">{p.name} <Evidence text={p.evidence} source={p.source} />
                  <PublicLine news={p.news} reaction={p.reaction} /></td>
                <td className="l">{period(p.start, p.end)}</td>
                <td>+{fmt(p.inc!)} <span className="note">({pct(p.inc_pct!)})</span></td>
                <td>{p.roi!.toFixed(2)}</td>
                <td className="l"><span className={`pill sm ${p.verdict}`}>{p.verdict_label}{p.firm ? "" : " · 잠정"}</span></td>
              </tr>
            ) : (
              <tr key={p.id} title={p.desc}>
                <td className="l name">{p.name} <Evidence text={p.evidence} source={p.source} />
                  <PublicLine news={p.news} reaction={null} /></td>
                <td className="l">{period(p.start, p.end)}</td>
                <td colSpan={2} className="note">{p.desc}</td>
                <td className="l"><span className="chip">{STATUS[p.status]}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">판정: ROI {r.roi_keep} 이상 지속 · {r.roi_adjust}~{r.roi_keep} 조정 · {r.roi_adjust} 미만 중단 검토 · 단가 {fmt(r.unit_price)}원 기준.
        {" "}잠정 = 기준선 범위가 판정 기준을 걸치거나 행사 없는 날이 적음.
        {found.length > 0 && ` 뉴스에서 찾은 행사 ${found.length}개 (행사표와 맞는 것 ${found.filter((e) => e.in_calendar).length}개).`}</p>
    </section>
  );
}
