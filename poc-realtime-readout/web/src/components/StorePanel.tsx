import type { Readout, StoreRow, View } from "../types";
import { fmt } from "../format";
import { Delta, Prov } from "./bits";

const FLAG: Record<NonNullable<StoreRow["flag"]>, [string, string]> = {
  check: ["crit", "반응↑ 판매↓ 점검"], spread: ["good", "확산"], rise: ["", "상승"], drop: ["warn", "하락"],
};

export function StorePanel({ data, view }: { data: Readout; view: View }) {
  const p = data.meta.provenance_raw;
  const st = view.stores;
  return (
    <section className="panel" aria-labelledby="m3">
      <div className="panel-h">
        <div>
          <h2 id="m3">매장 순위 급변</h2>
          <div className="q">전국 {fmt(data.meta.stores_total)}개 매장 중 판매 순위 변화, 주변 SNS 언급, 그리고 왜 움직였는지</div>
        </div>
        <div className="tags">
          <Prov p={p.sales_daily} what="판매" />
          <Prov p={p.store_reaction_weekly} what="언급" />
          <Prov p={p.store_context_weekly} what="상권" />
        </div>
      </div>
      {!st ? (
        <div className="empty">출시 후 첫 판독부터 매장별 순위 변화가 쌓입니다.</div>
      ) : (
        <>
          <div className="tablewrap">
            <table>
              <thead><tr><th className="l">매장</th><th>순위</th><th>주변 언급</th><th className="l">신호</th><th className="l">왜</th></tr></thead>
              <tbody>
                {st.rows.map((r) => (
                  <tr key={r.store_id}>
                    <td className="l name">{r.name}<div className="note">{r.type}</div></td>
                    <td>{fmt(r.rank)}위<div><Delta d={r.delta} /></div></td>
                    <td>{r.sns_prev}→{r.sns}건</td>
                    <td className="l">{r.flag && <span className={`chip ${FLAG[r.flag][0]}`}>{FLAG[r.flag][1]}</span>}</td>
                    <td className="l why">{r.why ?? <span className="flat">개별 요인 · 확인 필요</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="note">이번 주 점검 신호 {st.counts.check ?? 0}곳 · 확산 {st.counts.spread ?? 0}곳 · 하락 {st.counts.drop ?? 0}곳 (순위 ±100 기준)</p>
        </>
      )}
    </section>
  );
}
