import type { Card, Day, Readout } from "../types";
import { MODULE_LABEL, md, mdw } from "../format";
import { Prov } from "./bits";

function CardView({ c, data, wide }: { c: Card; data: Readout; wide?: boolean }) {
  const p = data.meta.provenance_raw;
  return (
    <article className={`card ${wide ? "wide" : ""}`}>
      <div className="top">
        <div>
          <div className="eyebrow">{MODULE_LABEL[c.module]}</div>
          <h3>{c.title}</h3>
        </div>
        <span className={`pill ${c.pill.tone}`}>{c.pill.label}</span>
      </div>
      <div className="head">{c.head}</div>
      <ul>{c.items.map((t) => <li key={t}>{t}</li>)}</ul>
      <div className="tags">
        {c.tags.includes("sales") && <Prov p={p.sales_daily} what="판매" />}
        {c.tags.includes("reaction") && <Prov p={p.reaction_daily} what="반응" />}
        {c.tags.includes("cost") && <span className="tag link">비용 가정</span>}
      </div>
    </article>
  );
}

// 두 층: 매일 모니터링(카드 1장, 매일 바뀜) + 주간 판독(결정 3축, 매주 월요일 아침 확정)
export function Cards({ day, data }: { day: Day; data: Readout }) {
  const w = day.weekly;
  const readToday = w && w.asof === day.date;
  return (
    <section className="readout" aria-label="판독">
      <div className="layer-h">
        <h2>매일 모니터링</h2>
        <span className="note">{mdw(day.read)} 아침 · {md(day.date)}까지 데이터 · 급한 신호는 주간 판독을 기다리지 않음</span>
      </div>
      <CardView c={day.monitor} data={data} wide />

      <div className="layer-h">
        <h2>주간 판독</h2>
        {w ? (
          <span className="note">
            {mdw(w.read)} 아침 확정 · {md(w.asof)}까지 데이터 · 지금 방식보다 {w.gain_days}일 빨리
            {w.next_read && ` · 다음 판독 ${mdw(w.next_read)}`}
          </span>
        ) : (
          <span className="note">첫 주간 판독 {day.first_weekly_read ? mdw(day.first_weekly_read) : ""}</span>
        )}
        {readToday && <span className="chip new">오늘 판독</span>}
        {w && w.new_alerts > 0 && !readToday && (
          <span className="chip warn">판독 이후 새 알림 {w.new_alerts}건 → 다음 판독에 반영</span>
        )}
      </div>
      {w ? (
        <div className="cards">{w.cards.map((c) => <CardView key={c.key} c={c} data={data} />)}</div>
      ) : (
        <div className="empty">아직 주간 판독 전입니다.</div>
      )}
    </section>
  );
}
