import type { Readout } from "../types";
import { md, mdw } from "../format";

interface Props {
  data: Readout; cur: number; playing: boolean;
  onPick: (i: number) => void; onPlay: () => void;
}

// 상단: 제품명·서비스명 + 기준일(날짜 슬라이더). ▶ 는 기간을 하루씩 재생
export function TopBar({ data, cur, playing, onPick, onPlay }: Props) {
  const day = data.days[cur];
  const idx = (d: string) => data.days.findIndex((x) => x.date === d);
  const w = day.weekly;
  return (
    <header className="topbar">
      <div className="tb-brand">
        <div className="tb-title">
          <span className="logo-dot" aria-hidden />
          <h1>{data.meta.title}</h1>
          <span className="tb-sub">판매 · 광고 · SNS 반응을 같은 날짜 축에서</span>
        </div>
        <div className="tb-product" title="분석 대상 제품">
          <span className="tb-k">신제품</span>
          <b>{data.meta.product.name}</b>
          <span className="tb-k">출시 {md(data.meta.product.launch)}</span>
        </div>
      </div>
      <div className="tb-date">
        <button type="button" className="play" onClick={onPlay} aria-label={playing ? "일시정지" : "기간 재생"}>
          {playing ? "❚❚" : "▶"}
        </button>
        <div className="tb-now">
          <div className="tb-day">{mdw(day.date)} 기준</div>
          <div className="tb-meta">
            {w ? `주간 판독 ${mdw(w.read)}` : "주간 판독 전"}
            {w?.next_read && ` · 다음 판독 ${mdw(w.next_read)}`}
          </div>
        </div>
        <div className="tb-slider">
          <input type="range" min={0} max={data.days.length - 1} value={cur}
                 onChange={(e) => onPick(Number(e.target.value))} aria-label="기준일" />
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
        </div>
      </div>
    </header>
  );
}
