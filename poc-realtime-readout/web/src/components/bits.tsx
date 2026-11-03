import type { Prov } from "../types";

const PROV_TEXT: Record<Prov, string> = { raw: "본사 데이터", api: "공개 API", mixed: "공개 API + 목", mock: "목" };

// 데이터 출처 배지: 테이블이 어디서 왔는지(본사 / 공개 API / 목)를 그대로 보여준다
export function Prov({ p, what }: { p: Prov | undefined; what: string }) {
  if (!p) return null;
  return <span className={`tag ${p}`}>{what} · {PROV_TEXT[p]}</span>;
}

export function Delta({ d }: { d: number | "new" | null }) {
  if (d === null) return <span className="flat">-</span>;
  if (d === "new") return <span className="chip new">신규</span>;
  if (d > 0) return <span className="up">▲{d}</span>;
  if (d < 0) return <span className="down">▼{-d}</span>;
  return <span className="flat">-</span>;
}
