import type { Readout } from "../types";
import { md, mdw } from "../format";

interface Props {
  data: Readout; cur: number; playing: boolean;
  onPick: (i: number) => void; onPlay: () => void;
}

// 공통 날짜 슬라이더: 하루 = 그 날 밤까지의 데이터를 다음 날 아침에 본 모니터링. ▶ 로 3월 출시를 날짜 순서대로 재생.
// 칩: 티저·출시는 그 날, 판독은 월요일 판독일을 표시.
export function TimeBar({ data, cur, playing, onPick, onPlay }: Props) {
  const day = data.days[cur];
  const idx = (d: string) => data.days.findIndex((x) => x.date === d);
  const newCount = data.alerts.filter((a) => a.date === day.date).length;
  return (
    <section className="timebar" aria-label="판독 시점">
      <div className="tb-row">
        <button type="button" className="play" onClick={onPlay} aria-label={playing ? "일시정지" : "재생"}>
          {playing ? "❚❚" : "▶"}
        </button>
        <div className="tb-now">
          <div className="tb-date">{mdw(day.read)} 아침</div>
          <div className="note">
            {md(day.date)}까지 쌓인 데이터 · 오늘 새 알림 {newCount}건
            {day.weekly && ` · 주간 판독 기준 ${md(day.weekly.read)}`}
          </div>
        </div>
        <div className="tb-gain">
          <div className="note">지금 방식(월말 정산 후 {md(data.meta.current_read)})보다</div>
          <div className="tb-gain-v">{day.gain_days > 0 ? `${day.gain_days}일 빨리` : "같은 시점"}</div>
        </div>
      </div>
      <input
        type="range" min={0} max={data.days.length - 1} value={cur}
        onChange={(e) => onPick(Number(e.target.value))} aria-label="판독 날짜"
      />
      <div className="tb-marks">
        {data.meta.milestones.map((m) => {
          const i = idx(m.date);
          if (i < 0) return null;
          return (
            <button type="button" key={m.label} className={i === cur ? "on" : ""} onClick={() => onPick(i)}>
              {m.label}<small>{md(m.show)}</small>
            </button>
          );
        })}
      </div>
    </section>
  );
}
