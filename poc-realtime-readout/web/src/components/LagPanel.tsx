import type { Readout, View } from "../types";
import { md } from "../format";
import { Prov } from "./bits";

// 파트 1 리서치: 숏폼을 본 10~20대는 바로 사지 않고 며칠 뒤 매장에서 산다 → 반응 정점과 판매 몰림의 시차
export function LagPanel({ data, view }: { data: Readout; view: View }) {
  const maxDay = Math.max(1, ...view.peaks.map((x) => x.day));
  const firm = view.peaks.filter((x) => x.firm);
  return (
    <section className="panel" aria-labelledby="m6">
      <div className="panel-h">
        <div>
          <h2 id="m6">반응에서 판매까지 걸린 날</h2>
          <div className="q">
            매장 유형별로 이달의 맛 판매가 다른 유형보다 가장 몰린 날
            {view.reaction_peak && ` · 검색 반응 정점(${md(view.reaction_peak)})에서 며칠 뒤인지`}
          </div>
        </div>
        <div className="tags"><Prov p={data.meta.provenance_raw.sales_daily} what="판매" /><Prov p={data.meta.provenance_raw.reaction_daily} what="반응" /></div>
      </div>
      {view.peaks.length === 0 ? (
        <div className="empty">출시 후 일주일이 지나야 유형별 판매 정점이 보입니다.</div>
      ) : (
        <>
          <div className="peak" style={{ marginTop: 0 }}>
            {view.peaks.map((x) => (
              <div className="row" key={x.type}>
                <span>{x.type}</span>
                <div className={`bar ${x.firm ? "" : "tentative"}`} style={{ width: `${(x.day / maxDay) * 100}%` }} />
                <span>
                  {x.day}일차
                  {x.lag_from_reaction != null && ` (${x.lag_from_reaction >= 0 ? "+" : ""}${x.lag_from_reaction}일)`}
                  {x.firm ? "" : " · 잠정"}
                </span>
              </div>
            ))}
          </div>
          <p className="note" style={{ marginBottom: 0 }}>
            {firm.length >= 2
              ? `${firm[0].type} 매장이 가장 먼저(${firm[0].day}일차), ${firm[firm.length - 1].type} 매장이 가장 늦게(${firm[firm.length - 1].day}일차) 몰림 → 초도 물량과 POP는 ${firm[0].type}부터, 추가 배송은 ${firm[firm.length - 1].type} 쪽으로.`
              : "정점 뒤로 이틀 이상 데이터가 쌓여야 확정합니다."}
            {" "}점선 막대는 아직 정점이 확정되지 않은 유형입니다. 상대지수 = 그 유형 매장당 판매 ÷ 전체 매장당 판매.
          </p>
        </>
      )}
    </section>
  );
}
