import type { Day, Readout, StoreRow } from "../types";
import { fmt, period } from "../format";
import { Delta, Prov } from "./bits";

const FLAG: Record<NonNullable<StoreRow["flag"]>, [string, string]> = {
  check: ["crit", "점검"], viral: ["good", "바이럴"], recover: ["new", "회복"], rise: ["", "상승"], drop: ["warn", "하락"],
};

// 모듈 3 · 매장 순위 급등 (Q4). 순위 변화를 매장 주변 SNS 반응으로 판독한다.
export function StorePanel({ data, day }: { data: Readout; day: Day }) {
  const p = data.meta.provenance_raw;
  const st = day.stores;
  return (
    <section className="panel" aria-labelledby="m3">
      <div className="panel-h">
        <div>
          <div className="eyebrow">모듈 3</div>
          <h2 id="m3">매장 순위 급등</h2>
          <div className="q">
            전국 {fmt(data.meta.stores_total)}개 매장 판매 순위 변화를 주변 SNS 언급으로 판독
            {st && ` · 최근 7일 ${period(st.window.start, st.window.end)} vs 그 전 7일`}
          </div>
        </div>
        <div className="tags"><Prov p={p.sales_daily} what="판매" /><Prov p={p.store_reaction_daily} what="매장 언급" /></div>
      </div>
      {!st ? (
        <div className="empty">출시 7일이 지나면 매장별 순위 변화가 쌓입니다.</div>
      ) : (
        <>
          <div className="tablewrap">
            <table>
              <thead><tr><th className="l">매장</th><th>순위</th><th>주변 언급</th><th className="l">판독</th></tr></thead>
              <tbody>
                {st.rows.map((r) => (
                  <tr key={r.store_id}>
                    <td className="l name">{r.name}</td>
                    <td>{fmt(r.rank)}위<div><Delta d={r.delta} /></div></td>
                    <td>{r.sns_prev}→{r.sns}건</td>
                    <td className="l why">
                      {r.flag && <span className={`chip ${FLAG[r.flag][0]}`}>{FLAG[r.flag][1]}</span>}{" "}
                      {r.why ?? <span className="flat">주변 반응 변화 없음 · 확인 필요</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="note">
            점검 {st.counts.check ?? 0} · 바이럴 {st.counts.viral ?? 0}곳. 주변 언급↑ = 7일 15건 이상, 10건 이상 늘고, 전국 언급 흐름보다 60% 이상 더 늘어남. 순위 기준 ±100.
          </p>
        </>
      )}
    </section>
  );
}
