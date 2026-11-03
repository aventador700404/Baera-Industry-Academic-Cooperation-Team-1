import type { Alert, Day } from "../types";
import { md } from "../format";
import { Verdict } from "./bits";

const MOD: Record<string, string> = { reaction: "신제품 반응", flavor: "맛별 판매", store: "매장 순위", promo: "판촉 효과" };

// 오른쪽: 지금 가장 급한 것 + 알림 피드 (최신이 위)
export function AlertFeed({ alerts, day }: { alerts: Alert[]; day: Day }) {
  const shown = alerts.filter((a) => a.date <= day.date).slice().reverse();
  return (
    <aside className="side" aria-label="모니터링">
      <section className="panel">
        <div className="panel-h"><h2>지금 가장 급한 것</h2><span className="note">최근 3일</span></div>
        <Verdict c={day.monitor} note={MOD[day.monitor.module]} />
      </section>
      <section className="panel feed" aria-labelledby="feed-h">
        <div className="panel-h"><h2 id="feed-h">알림</h2><span className="chip">{shown.length}</span></div>
        {shown.length === 0 ? (
          <div className="empty">아직 알림이 없습니다.</div>
        ) : (
          <ol className="feed-list">
            {shown.map((a) => (
              <li key={`${a.date}-${a.kind}-${a.title}`} className={`al ${a.tone} ${a.date === day.date ? "today" : ""}`}>
                <div className="al-top">
                  <span className={`dot ${a.tone}`} aria-hidden />
                  <span className="al-date">{md(a.date)}</span>
                  <span className="al-mod">{MOD[a.module]}</span>
                  {a.date === day.date && <span className="chip pink">새 알림</span>}
                </div>
                <div className="al-title">{a.title}</div>
                <div className="al-detail">{a.detail}</div>
                <div className="al-action"><b>할 일</b>{a.action}</div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </aside>
  );
}
