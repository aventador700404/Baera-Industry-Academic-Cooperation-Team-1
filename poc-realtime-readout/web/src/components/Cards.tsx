import type { Card, Readout } from "../types";
import { MODULE_LABEL } from "../format";
import { Prov } from "./bits";

// 그날 판독 → 마케팅이 할 일. 4모듈에 하나씩.
export function Cards({ cards, data }: { cards: Card[]; data: Readout }) {
  const p = data.meta.provenance_raw;
  return (
    <section className="cards" aria-label="오늘의 판독">
      {cards.map((c) => (
        <article className="card" key={c.key}>
          <div className="top">
            <div>
              <div className="eyebrow">{MODULE_LABEL[c.module]}</div>
              <h3>{c.title}</h3>
            </div>
            <span className={`pill ${c.pill.tone}`}>{c.pill.label}</span>
          </div>
          <div className="head">{c.head}</div>
          <ul>{c.items.map((t) => <li key={t}>{t}</li>)}</ul>
          <div className="tags">
            {c.tags.includes("sales") && <Prov p={p.sales_daily} what="판매" />}
            {c.tags.includes("reaction") && <Prov p={p.reaction_daily} what="반응" />}
            {c.tags.includes("cost") && <span className="tag link">비용 가정</span>}
          </div>
        </article>
      ))}
    </section>
  );
}
