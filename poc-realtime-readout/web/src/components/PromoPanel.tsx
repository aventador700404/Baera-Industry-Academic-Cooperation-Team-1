import type { Day, Readout } from "../types";
import { fmt, pct, period } from "../format";
import { Prov } from "./bits";

const STATUS: Record<string, string> = {
  running: "진행 중 · 행사가 끝난 뒤 판독", planned: "예정", pending: "종료 · 기준선을 맞출 행사 없는 날을 쌓는 중", done: "",
};
const STATUS_CHIP: Record<string, string> = { running: "진행 중", planned: "예정", pending: "판독 대기", done: "" };

// 모듈 4 · 판촉 행사 효과
export function PromoPanel({ data, day }: { data: Readout; day: Day }) {
  const fw = day.first_week;
  const r = data.meta.rules;
  return (
    <section className="panel" aria-labelledby="m4">
      <div className="panel-h">
        <div>
          <div className="eyebrow">모듈 4</div>
          <h2 id="m4">판촉 행사 효과</h2>
          <div className="q">행사 기간 판매에서 행사가 없었을 때의 기준선을 빼서 늘어난 판매(증분)만 셉니다</div>
        </div>
        <div className="tags"><Prov p={data.meta.provenance_raw.promo_calendar} what="행사표" /><span className="tag link">비용 가정</span></div>
      </div>
      {fw && (
        <>
          <div className="note">
            출시 첫 주 판매 분해: 맛 수요 {fmt(fw.demand)}개 ({pct(1 - fw.promo_share)}) · 할인 효과 {fmt(fw.promo)}개 ({pct(fw.promo_share)})
          </div>
          <div className="split" role="img" aria-label="출시 첫 주 판매 중 맛 수요와 할인 효과 비중">
            <div style={{ width: `${100 - fw.promo_share * 100}%`, background: "var(--s1)" }} />
            <div style={{ width: `${fw.promo_share * 100}%`, background: "var(--s2)" }} />
          </div>
        </>
      )}
      <div className="tablewrap">
        <table>
          <thead><tr><th className="l">행사</th><th className="l">기간</th><th>판매</th><th>기준선</th><th>증분 (범위)</th><th>할인 비용</th><th>증분 ROI</th><th className="l">판정</th></tr></thead>
          <tbody>
            {day.promos.map((p) => p.status === "done" ? (
              <tr key={p.id}>
                <td className="l name">{p.name}<div className="note">{p.desc}</div></td>
                <td className="l">{period(p.start, p.end)}</td>
                <td>{fmt(p.act!)}</td>
                <td>{fmt(p.base!)}</td>
                <td>+{fmt(p.inc!)} ({pct(p.inc_pct!)})<div className="note">{fmt(p.inc_lo!)}~{fmt(p.inc_hi!)}</div></td>
                <td>{fmt(p.cost_won! / 1e6)}백만 원</td>
                <td>{p.roi!.toFixed(2)}<div className="note">{p.roi_lo!.toFixed(2)}~{p.roi_hi!.toFixed(2)}</div></td>
                <td className="l"><span className={`pill ${p.verdict}`}>{p.verdict_label}{p.firm ? "" : " (잠정)"}</span></td>
              </tr>
            ) : (
              <tr key={p.id}>
                <td className="l name">{p.name}<div className="note">{p.desc}</div></td>
                <td className="l">{period(p.start, p.end)}</td>
                <td colSpan={5} className="l note">{STATUS[p.status]}</td>
                <td className="l"><span className="chip">{STATUS_CHIP[p.status]}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">
        증분 ROI = 증분 매출 ÷ 할인 비용. 할인 비용 = 행사 기간 전체 판매 × 단가 {fmt(r.unit_price)}원 × 할인 환산율(행사표).
        판정: {r.roi_keep} 이상 지속, {r.roi_adjust}~{r.roi_keep} 조정, {r.roi_adjust} 미만 중단 검토.
        범위가 기준을 걸치거나 기준선을 맞춘 날이 10일 미만이면 잠정.
      </p>
    </section>
  );
}
