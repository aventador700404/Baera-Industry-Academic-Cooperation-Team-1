import type { Day } from "../types";
import { fmt, mdw, period } from "../format";
import { Delta, Verdict } from "./bits";

// 맛별 판매 순위
export function FlavorTable({ day }: { day: Day }) {
  const f = day.flavor;
  const c = day.weekly?.cards.find((x) => x.key === "demand");
  return (
    <section className="panel quad" aria-labelledby="q2">
      <div className="panel-h"><h2 id="q2">맛별 판매 순위</h2><span className="note">최근 7일 {period(f.window.start, f.window.end)}</span></div>
      {c && <Verdict c={c} note={`주간 판독 ${mdw(day.weekly!.read)}`} />}
      <div className="tablewrap">
        <table className="compact">
          <thead><tr><th>순위</th><th className="l">맛</th><th>일평균</th><th>변화</th><th className="l"></th></tr></thead>
          <tbody>
            {f.rows.map((r) => (
              <tr key={r.flavor} className={r.signals.some((s) => s.kind === "new") ? "hl" : ""}>
                <td>{r.rank}</td>
                <td className="l name">{r.flavor}</td>
                <td>{fmt(r.avg)}</td>
                <td><Delta d={r.change} /></td>
                <td className="l">{r.signals.filter((s) => s.kind !== "new").map((s) => <span key={s.text} className={`chip ${s.kind}`}>{s.text}</span>)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
