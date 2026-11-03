import type { Alert, Day } from "../types";
import { MODULE_LABEL, md } from "../format";

// 그 날까지 감지된 신호. 최신이 위, 오늘 감지된 것은 강조.
export function AlertFeed({ alerts, day }: { alerts: Alert[]; day: Day }) {
  const shown = alerts.filter((a) => a.date <= day.date).slice().reverse();
  return (
    <aside className="feed panel" aria-labelledby="feed-h">
      <div className="panel-h">
        <div>
          <h2 id="feed-h">실시간 알림</h2>
          <div className="q">평소와 다르게 움직인 신호를 그 날 바로 잡아 할 일과 같이 띄웁니다</div>
        </div>
        <span className="chip">{shown.length}건</span>
      </div>
      {shown.length === 0 ? (
        <div className="empty">아직 감지된 신호가 없습니다. ▶ 를 눌러 재생해 보세요.</div>
      ) : (
        <ol className="feed-list">
          {shown.map((a) => (
            <li key={`${a.date}-${a.kind}-${a.title}`} className={`al ${a.tone} ${a.date === day.date ? "today" : ""}`}>
              <div className="al-top">
                <span className={`dot ${a.tone}`} aria-hidden />
                <span className="al-date">{md(a.date)}</span>
                <span className="al-mod">{MODULE_LABEL[a.module]}</span>
                {a.date === day.date && <span className="chip new">오늘</span>}
              </div>
              <div className="al-title">{a.title}</div>
              <div className="al-detail">{a.detail}</div>
              <div className="al-action"><b>할 일</b>{a.action}</div>
              <div className="al-gain">지금 방식보다 {a.gain_days}일 빨리</div>
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}
