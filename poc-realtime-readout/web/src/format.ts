export const fmt = (n: number) => Math.round(n).toLocaleString("ko-KR");
export const pct = (n: number, d = 0) => `${(n * 100).toFixed(d)}%`;
export const md = (s: string) => {
  const [, m, d] = s.split("-");
  return `${+m}/${+d}`;
};
export const man = (v: number) => (v >= 10000 ? `${(v / 10000).toFixed(v % 10000 ? 1 : 0)}만` : fmt(v));
export const period = (a: string, b: string) => (a === b ? md(a) : `${md(a)}~${md(b)}`);
