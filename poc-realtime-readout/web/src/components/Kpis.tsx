import type { Day } from "../types";

export function Kpis({ day }: { day: Day }) {
  return (
    <section className="kpis" aria-label="핵심 지표">
      {day.kpis.map((k) => (
        <div className="kpi" key={k.k}><div className="k">{k.k}</div><div className="v">{k.v}</div><div className="d">{k.d}</div></div>
      ))}
    </section>
  );
}
