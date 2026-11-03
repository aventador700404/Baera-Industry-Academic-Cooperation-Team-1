export const fmt = (n: number) => Math.round(n).toLocaleString("ko-KR");
export const pct = (n: number, d = 0) => `${(n * 100).toFixed(d)}%`;
export const md = (s: string) => {
  const [, m, d] = s.split("-");
  return `${+m}/${+d}`;
};
export const man = (v: number) => (v >= 10000 ? `${(v / 10000).toFixed(v % 10000 ? 1 : 0)}만` : fmt(v));
export const period = (a: string, b: string) => (a === b ? md(a) : `${md(a)}~${md(b)}`);
const WD = ["일", "월", "화", "수", "목", "금", "토"];
export const mdw = (s: string) => `${md(s)} (${WD[new Date(`${s}T00:00:00`).getDay()]})`;
export const MODULE_LABEL: Record<string, string> = {
  monitor: "매일 모니터링", reaction: "모듈 1 · 신제품 반응", flavor: "모듈 2 · 맛별 판매", store: "모듈 3 · 매장 순위", promo: "모듈 4 · 판촉 효과",
};
