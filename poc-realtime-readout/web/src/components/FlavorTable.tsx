import type { Readout, View } from "../types";
import { fmt, period } from "../format";
import { Delta, Prov } from "./bits";

export function FlavorTable({ data, view }: { data: Readout; view: View }) {
  const f = view.flavor;
  return (
    <section className="panel" aria-labelledby="m2">
      <div className="panel-h">
        <div>
          <h2 id="m2">맛별 판매 순위</h2>
          <div className="q">판독 주간 {period(f.window.start, f.window.end)} 일평균 판매, 직전 주간 대비 순위 변화</div>
        </div>
        <div className="tags"><Prov p={data.meta.provenance_raw.sales_daily} what="판매" /></div>
      </div>
      <div className="tablewrap">
        <table>
          <thead><tr><th>순위</th><th className="l">맛</th><th>일평균(개)</th><th>변화</th><th className="l">신호</th></tr></thead>
          <tbody>
            {f.rows.map((r) => (
              <tr key={r.flavor}>
                <td>{r.rank}</td>
                <td className="l name">{r.flavor}</td>
                <td>{fmt(r.avg)}</td>
                <td><Delta d={r.change} /></td>
                <td className="l">{r.signals.map((s) => <span key={s.text} className={`chip ${s.kind}`} style={{ marginRight: 4 }}>{s.text}</span>)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
