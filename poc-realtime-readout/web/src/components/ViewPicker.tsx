import type { View } from "../types";
import { md } from "../format";

export function ViewPicker({ views, cur, onPick }: { views: View[]; cur: number; onPick: (i: number) => void }) {
  const v = views[cur];
  return (
    <section className="control" aria-label="판독 시점">
      <div className="seg">
        {views.map((x, i) => (
          <button key={x.id} type="button" aria-pressed={i === cur} onClick={() => onPick(i)}>
            {x.label}
            <small>{x.id === "pre" ? `${md(x.to)} 기준` : `${md(x.read)} 판독`}</small>
          </button>
        ))}
      </div>
      <div className="timing">
        {"pre" in v.timing ? (
          <>
            <div className="t"><div className="k">주간 판독으로 지금 보는 것</div><div className="v now">티저 이후 반응 (출시 전)</div></div>
            <div className="t"><div className="k">지금 방식 (월 단위 사후 집계)</div><div className="v">출시 전 신호는 보지 못함</div></div>
          </>
        ) : (
          <>
            <div className="t"><div className="k">주간 판독으로 이 결과를 보는 날</div><div className="v now">{md(v.timing.read)}</div></div>
            <div className="t"><div className="k">지금 방식 (월 단위 사후 집계, 가정)</div><div className="v">{md(v.timing.current)} 이후</div></div>
            <div className="t"><div className="k">앞당겨지는 기간</div><div className="v">{v.timing.gain_days > 0 ? `${v.timing.gain_days}일` : "같은 시점"}</div></div>
          </>
        )}
      </div>
    </section>
  );
}
