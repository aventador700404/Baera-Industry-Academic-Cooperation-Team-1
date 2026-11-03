import type { Day, Readout, StoreRow } from "../types";
import { fmt, mdw, period } from "../format";
import { Delta, Verdict } from "./bits";

const FLAG: Record<NonNullable<StoreRow["flag"]>, [string, string]> = {
  check: ["crit", "점검"], viral: ["good", "바이럴"], recover: ["blue", "회복"], rise: ["", "상승"], drop: ["warn", "하락"],
};

// 매장 순위 급등: 판매 순위 변화를 매장 주변 SNS 언급으로 판독
export function StorePanel({ data, day }: { data: Readout; day: Day }) {
  const st = day.stores;
  const c = day.weekly?.cards.find((x) => x.key === "store");
  return (
    <section className="panel quad" aria-labelledby="q3">
      <div className="panel-h">
        <h2 id="q3">매장 순위 급등</h2>
        <span className="note">전국 {fmt(data.meta.stores_total)}개 매장{st && ` · ${period(st.window.start, st.window.end)} vs 전주`}</span>
      </div>
      {c && <Verdict c={c} note={`주간 판독 ${mdw(day.weekly!.read)}`} />}
      {!st ? (
        <div className="empty">출시 7일 후부터 매장별 순위 변화가 쌓입니다.</div>
      ) : (
        <div className="tablewrap">
          <table className="compact">
            <thead><tr><th className="l">매장</th><th>순위</th><th>주변 언급</th><th className="l">판독</th></tr></thead>
            <tbody>
              {st.rows.map((r) => (
                <tr key={r.store_id}>
                  <td className="l name">{r.name}</td>
                  <td>{fmt(r.rank)}위 <Delta d={r.delta} /></td>
                  <td>{r.sns_prev}→{r.sns}</td>
                  <td className="l why">
                    {r.flag && <span className={`chip ${FLAG[r.flag][0]}`}>{FLAG[r.flag][1]}</span>}{" "}
                    {r.why ?? <span className="flat">반응 변화 없음</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
