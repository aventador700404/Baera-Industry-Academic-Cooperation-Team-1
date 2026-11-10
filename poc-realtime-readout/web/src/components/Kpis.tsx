import type { Day } from "../types";

// 핵심 지표 숫자들. only 를 주면 그 지표만 (상세 탭에서 해당 축과 관련된 것만 보여 줄 때)
export function Kpis({ day, only }: { day: Day; only?: string[] }) {
  const rows = only ? day.kpis.filter((k) => only.includes(k.k)) : day.kpis;
  return (
    <section className="kpis" aria-label="핵심 지표">
      {rows.map((k) => (
        <div className="kpi" key={k.k}><div className="k">{k.k}</div><div className="v">{k.v}</div><div className="d">{k.d}</div></div>
      ))}
    </section>
  );
}
