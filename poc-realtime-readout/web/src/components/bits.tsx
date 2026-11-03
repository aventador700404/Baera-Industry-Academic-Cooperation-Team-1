import type { Card } from "../types";

export function Delta({ d }: { d: number | "new" | null }) {
  if (d === null) return <span className="flat">-</span>;
  if (d === "new") return <span className="chip new">신규</span>;
  if (d > 0) return <span className="up">▲{d}</span>;
  if (d < 0) return <span className="down">▼{-d}</span>;
  return <span className="flat">-</span>;
}

// 패널 머리의 판독: 상태 배지 + 한 줄 결론 + 할 일
export function Verdict({ c, note }: { c: Card; note?: string }) {
  const todo = c.items.find((t) => t.startsWith("할 일"));
  const rest = c.items.filter((t) => t !== todo).slice(0, todo ? 1 : 2);
  return (
    <div className={`verdict ${c.pill.tone}`}>
      <div className="v-top">
        <span className={`pill ${c.pill.tone}`}>{c.pill.label}</span>
        {note && <span className="v-note">{note}</span>}
      </div>
      <div className="v-head">{c.head}</div>
      {rest.map((t) => <div key={t} className="v-item">{t}</div>)}
      {todo && <div className="v-todo"><b>할 일</b>{todo.replace(/^할 일:\s*/, "")}</div>}
    </div>
  );
}
